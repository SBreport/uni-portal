"""DB 마이그레이션 관리 라우터 (admin only).

migrations/ 디렉토리의 SQL 파일을 안전하게 적용.
- 적용 전 자동 백업
- 트랜잭션 실행 (실패 시 rollback)
- migration_history 테이블에 이력 기록
- SHA256 해시로 중복 적용 방지
"""

import os
import shutil
import hashlib
import sqlite3
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.deps import get_current_user, require_role, ROLE_HIERARCHY
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter(prefix="/admin/migrations", tags=["Migrations"])
_admin = require_role("admin")

# SQL 파일 디렉토리 — path traversal 방지를 위해 절대경로로 고정
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MIGRATIONS_DIR = os.path.join(_PROJECT_ROOT, "docs", "_temp", "treatment_norm", "migrations")
BACKUP_DIR = os.path.join(_PROJECT_ROOT, "data", "_백업")


def _safe_filename(filename: str) -> str:
    """파일명 검증 — 디렉토리 구분자, 상위 경로 탐색 금지."""
    # 경로 구분자 포함 또는 상위 참조 금지
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="잘못된 파일명입니다.")
    if not filename.endswith(".sql"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=".sql 파일만 허용됩니다.")
    return filename


def _get_applied_hashes(conn: sqlite3.Connection) -> dict[str, str]:
    """적용된 마이그레이션 파일명 → 해시 매핑 반환."""
    try:
        rows = conn.execute(
            "SELECT filename, sql_hash FROM migration_history WHERE success = 1"
        ).fetchall()
        return {r["filename"]: r["sql_hash"] for r in rows}
    except sqlite3.OperationalError:
        # migration_history 테이블 없음 (첫 실행)
        return {}


def _sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _make_backup(filename: str) -> str:
    """DB 파일을 백업하고 경로를 반환."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.splitext(filename)[0]
    backup_name = f"equipment_{ts}_pre_{base}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    shutil.copy2(EQUIPMENT_DB, backup_path)
    return backup_path


def _record_history(
    filename: str,
    sql_hash: str,
    applied_by: str,
    backup_path: str,
    success: int,
    error_log: str,
    summary: str,
) -> None:
    """migration_history에 결과 기록 (별도 연결 사용)."""
    try:
        conn = get_conn(EQUIPMENT_DB)
        conn.execute(
            """INSERT INTO migration_history
               (filename, sql_hash, applied_at, applied_by, backup_path, success, error_log, summary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                filename,
                sql_hash,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                applied_by,
                backup_path,
                success,
                error_log,
                summary,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # 이력 기록 실패는 무시 (로그만)
        import logging
        logging.getLogger("migrations").error(f"이력 기록 실패: {e}")


# ── GET /pending ────────────────────────────────────────────────────────────
@router.get("/pending")
async def get_pending_migrations(
    user: Annotated[dict, Depends(_admin)],
):
    """아직 적용되지 않은 SQL 파일 목록 반환."""
    if not os.path.isdir(MIGRATIONS_DIR):
        return []

    conn = get_conn(EQUIPMENT_DB)
    applied = _get_applied_hashes(conn)
    conn.close()

    result = []
    for fname in sorted(os.listdir(MIGRATIONS_DIR)):
        if not fname.endswith(".sql"):
            continue
        fpath = os.path.join(MIGRATIONS_DIR, fname)
        stat = os.stat(fpath)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        sql_hash = _sha256(content)

        if fname in applied:
            continue  # 이미 적용됨

        lines = content.splitlines()
        # 상위 8줄에서 주석·요약 추출
        comment_lines = [
            l.lstrip("-").strip()
            for l in lines[:8]
            if l.strip().startswith("--")
        ]
        summary_top = "\n".join(comment_lines)[:200]

        result.append(
            {
                "filename": fname,
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M"
                ),
                "lines": len(lines),
                "summary_top": summary_top,
            }
        )
    return result


# ── GET /preview/{filename} ─────────────────────────────────────────────────
@router.get("/preview/{filename}")
async def preview_migration(
    filename: str,
    user: Annotated[dict, Depends(_admin)],
):
    """SQL 파일 내용 반환 (최대 100KB)."""
    _safe_filename(filename)
    fpath = os.path.join(MIGRATIONS_DIR, filename)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read(102400)  # 100KB 제한

    return {
        "filename": filename,
        "content": content,
        "line_count": len(content.splitlines()),
    }


# ── POST /apply ─────────────────────────────────────────────────────────────
class ApplyRequest(BaseModel):
    filename: str


@router.post("/apply")
async def apply_migration(
    body: ApplyRequest,
    user: Annotated[dict, Depends(_admin)],
):
    """SQL 마이그레이션 적용.

    1. 권한 검증 (admin)
    2. SHA256 중복 방지
    3. 자동 백업
    4. 트랜잭션 실행
    5. 이력 기록
    """
    filename = _safe_filename(body.filename)
    fpath = os.path.join(MIGRATIONS_DIR, filename)
    if not os.path.isfile(fpath):
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    with open(fpath, "r", encoding="utf-8") as f:
        sql_content = f.read()

    sql_hash = _sha256(sql_content)

    # 중복 적용 방지
    conn = get_conn(EQUIPMENT_DB)
    applied = _get_applied_hashes(conn)
    conn.close()

    if filename in applied:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"이미 적용된 마이그레이션입니다. (hash: {sql_hash[:8]}...)",
        )

    # 자동 백업
    try:
        backup_path = _make_backup(filename)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"백업 생성 실패: {e}"
        )

    # SQL 실행 (트랜잭션)
    conn = get_conn(EQUIPMENT_DB)
    applied_by = user.get("username", "unknown")
    error_log = ""
    summary = ""
    total_affected = 0

    try:
        # 여러 구문을 분리해서 실행, 각 결과 집계
        statements = [s.strip() for s in sql_content.split(";") if s.strip()]
        for stmt in statements:
            cur = conn.execute(stmt)
            if cur.rowcount and cur.rowcount > 0:
                total_affected += cur.rowcount
        conn.commit()
        summary = f"{len(statements)}개 구문 실행, {total_affected}건 영향"
    except Exception as e:
        conn.rollback()
        error_log = str(e)
        conn.close()

        # 이력에 실패 기록
        _record_history(
            filename, sql_hash, applied_by, backup_path,
            success=0, error_log=error_log, summary="실패"
        )

        # 백업에서 복원
        try:
            shutil.copy2(backup_path, EQUIPMENT_DB)
            restore_msg = "백업에서 복원되었습니다."
        except Exception as restore_err:
            restore_msg = f"복원 실패 — 수동 복원 필요: {backup_path}"
            import logging
            logging.getLogger("migrations").error(f"복원 실패: {restore_err}")

        raise HTTPException(
            status_code=500,
            detail=f"마이그레이션 실패: {error_log}\n{restore_msg}",
        )

    conn.close()

    # 이력에 성공 기록
    _record_history(
        filename, sql_hash, applied_by, backup_path,
        success=1, error_log="", summary=summary
    )

    return {
        "success": True,
        "summary": summary,
        "backup_path": backup_path,
        "error": None,
    }


# ── GET /history ─────────────────────────────────────────────────────────────
@router.get("/history")
async def get_migration_history(
    user: Annotated[dict, Depends(_admin)],
):
    """마이그레이션 이력 전체 (최신순)."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute(
            """SELECT id, filename, applied_at, applied_by,
                      success, summary, backup_path, error_log, sql_hash
               FROM migration_history
               ORDER BY applied_at DESC"""
        ).fetchall()
    except sqlite3.OperationalError:
        conn.close()
        return []
    conn.close()
    return [dict(r) for r in rows]
