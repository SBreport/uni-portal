"""Equipment 정리 도구 라우터 (admin only).

- GET  /admin/equipment-cleanup/duplicates  : 중복 그룹 목록
- GET  /admin/equipment-cleanup/summary     : 요약 통계
- POST /admin/equipment-cleanup/merge       : 중복 row 통합
- POST /admin/equipment-cleanup/remap       : device_info_id 재매핑
"""

import sqlite3
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import require_role
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter(prefix="/admin/equipment-cleanup", tags=["EquipmentCleanup"])
_admin = require_role("admin")


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    return get_conn(EQUIPMENT_DB)


# ── GET /summary ─────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_cleanup_summary(user: Annotated[dict, Depends(_admin)]):
    """요약 통계: 중복 그룹 수, NULL 매핑 수."""
    conn = _conn()
    try:
        dup_groups = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT branch_id, device_info_id
                FROM equipment
                WHERE device_info_id IS NOT NULL
                GROUP BY branch_id, device_info_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        null_count = conn.execute(
            "SELECT COUNT(*) FROM equipment WHERE device_info_id IS NULL"
        ).fetchone()[0]

        dup_rows = conn.execute("""
            SELECT COALESCE(SUM(cnt - 1), 0) FROM (
                SELECT COUNT(*) as cnt
                FROM equipment
                WHERE device_info_id IS NOT NULL
                GROUP BY branch_id, device_info_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        return {
            "duplicate_groups": dup_groups,
            "duplicate_excess_rows": dup_rows,
            "null_mapping": null_count,
        }
    finally:
        conn.close()


# ── GET /duplicates ──────────────────────────────────────────────────────────

@router.get("/duplicates")
async def get_duplicates(
    user: Annotated[dict, Depends(_admin)],
    branch_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    """중복 그룹 목록 (페이지네이션).

    같은 (branch_id, device_info_id)를 가진 equipment row가 2개 이상인 그룹.
    """
    conn = _conn()
    try:
        offset = (page - 1) * page_size

        branch_filter = "AND e.branch_id = :branch_id" if branch_id else ""

        # 중복 그룹 키 목록 (페이지네이션)
        group_rows = conn.execute(f"""
            SELECT e.branch_id, b.name AS branch_name,
                   e.device_info_id,
                   di.name AS device_info_name,
                   di.category AS category_name,
                   COUNT(*) AS row_count,
                   SUM(e.quantity) AS total_qty
            FROM equipment e
            JOIN branches b ON e.branch_id = b.id
            LEFT JOIN device_info di ON e.device_info_id = di.id
            WHERE e.device_info_id IS NOT NULL
            {branch_filter}
            GROUP BY e.branch_id, e.device_info_id
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, b.name, di.name
            LIMIT :limit OFFSET :offset
        """, {"branch_id": branch_id, "limit": page_size, "offset": offset}).fetchall()

        # 전체 건수
        total_row = conn.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT branch_id, device_info_id
                FROM equipment e
                WHERE device_info_id IS NOT NULL
                {branch_filter}
                GROUP BY branch_id, device_info_id
                HAVING COUNT(*) > 1
            )
        """, {"branch_id": branch_id} if branch_id else {}).fetchone()
        total = total_row[0] if total_row else 0

        # 각 그룹의 세부 row 조회
        result = []
        for g in group_rows:
            rows = conn.execute("""
                SELECT e.id, e.name, e.quantity, e.source, e.note,
                       e.device_info_id, e.created_at, e.updated_at
                FROM equipment e
                WHERE e.branch_id = ? AND e.device_info_id = ?
                ORDER BY e.id
            """, (g["branch_id"], g["device_info_id"])).fetchall()

            result.append({
                "branch_id": g["branch_id"],
                "branch_name": g["branch_name"],
                "device_info_id": g["device_info_id"],
                "device_info_name": g["device_info_name"],
                "category_name": g["category_name"],
                "row_count": g["row_count"],
                "total_qty": g["total_qty"],
                "rows": [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "qty": r["quantity"],
                        "source": r["source"] or "sheets",
                        "note": r["note"] or "",
                        "created_at": r["created_at"],
                    }
                    for r in rows
                ],
            })

        return {
            "groups": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }
    finally:
        conn.close()


# ── POST /merge ──────────────────────────────────────────────────────────────

class MergeRequest(BaseModel):
    branch_id: int
    device_info_id: int
    target_row_id: int
    source_row_ids: list[int]
    new_name: Optional[str] = None


@router.post("/merge")
async def merge_equipment(
    body: MergeRequest,
    user: Annotated[dict, Depends(_admin)],
):
    """중복 row 통합.

    1. source_row들의 qty 합산 → target_row.quantity에 반영
    2. new_name 있으면 target_row.name 변경
    3. source_row들 DELETE
    4. 트랜잭션 보장
    """
    if not body.source_row_ids:
        raise HTTPException(400, "source_row_ids가 비어 있습니다.")
    if body.target_row_id in body.source_row_ids:
        raise HTTPException(400, "target_row_id는 source_row_ids에 포함될 수 없습니다.")

    conn = _conn()
    try:
        # target row 존재 확인
        target = conn.execute(
            "SELECT id, name, quantity, branch_id, device_info_id FROM equipment WHERE id = ?",
            (body.target_row_id,),
        ).fetchone()
        if not target:
            raise HTTPException(404, f"target_row_id={body.target_row_id} 를 찾을 수 없습니다.")

        if target["branch_id"] != body.branch_id or target["device_info_id"] != body.device_info_id:
            raise HTTPException(
                400,
                "target row의 branch_id / device_info_id가 요청값과 다릅니다."
            )

        # source row들 qty 합산
        placeholders = ",".join("?" * len(body.source_row_ids))
        sources = conn.execute(
            f"SELECT id, quantity, branch_id, device_info_id FROM equipment WHERE id IN ({placeholders})",
            body.source_row_ids,
        ).fetchall()

        if len(sources) != len(body.source_row_ids):
            found_ids = {r["id"] for r in sources}
            missing = [i for i in body.source_row_ids if i not in found_ids]
            raise HTTPException(404, f"source_row_ids 중 찾을 수 없는 id: {missing}")

        for s in sources:
            if s["branch_id"] != body.branch_id or s["device_info_id"] != body.device_info_id:
                raise HTTPException(
                    400,
                    f"source row id={s['id']}의 branch_id / device_info_id가 요청값과 다릅니다."
                )

        source_qty_total = sum(s["quantity"] for s in sources)
        new_qty = target["quantity"] + source_qty_total
        new_name = (body.new_name or "").strip() or target["name"]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 트랜잭션 시작
        conn.execute("BEGIN")

        # target 업데이트
        conn.execute(
            "UPDATE equipment SET quantity = ?, name = ?, updated_at = ? WHERE id = ?",
            (new_qty, new_name, now, body.target_row_id),
        )

        # source 삭제
        conn.execute(
            f"DELETE FROM equipment WHERE id IN ({placeholders})",
            body.source_row_ids,
        )

        conn.execute("COMMIT")

        return {
            "success": True,
            "target_id": body.target_row_id,
            "merged_count": len(body.source_row_ids),
            "new_qty": new_qty,
            "new_name": new_name,
        }

    except HTTPException:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise HTTPException(500, f"통합 실패: {str(e)}")
    finally:
        conn.close()


# ── POST /remap ──────────────────────────────────────────────────────────────

class RemapRequest(BaseModel):
    branch_id: Optional[int] = None
    force: bool = False


@router.post("/remap")
async def remap_equipment(
    body: RemapRequest,
    user: Annotated[dict, Depends(_admin)],
):
    """device_info_id 재매핑.

    - force=False (기본): device_info_id IS NULL인 row만 재매핑
    - force=True: 전체 re-run (현재 매핑 덮어씌움)
    """
    from equipment.matcher import match_single

    conn = _conn()
    try:
        # 대상 row 조회
        if body.force:
            where = "WHERE 1=1"
        else:
            where = "WHERE e.device_info_id IS NULL"

        branch_clause = "AND e.branch_id = ?" if body.branch_id else ""
        params: list = []
        if body.branch_id:
            params.append(body.branch_id)

        rows = conn.execute(
            f"SELECT id, name FROM equipment {where} {branch_clause}",
            params,
        ).fetchall()

        if not rows:
            return {"remapped_count": 0, "unmatched_count": 0}

        # device_info 전체 로드 (매번 DB 쿼리 대신 캐시)
        device_list = [
            dict(r) for r in conn.execute(
                "SELECT * FROM device_info ORDER BY usage_count DESC, name"
            ).fetchall()
        ]

        remapped = 0
        unmatched = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("BEGIN")
        for row in rows:
            dev_id, _ = match_single(row["name"], device_list)
            if dev_id is not None:
                conn.execute(
                    "UPDATE equipment SET device_info_id = ?, updated_at = ? WHERE id = ?",
                    (dev_id, now, row["id"]),
                )
                remapped += 1
            else:
                unmatched += 1
        conn.execute("COMMIT")

        return {
            "remapped_count": remapped,
            "unmatched_count": unmatched,
            "total_processed": len(rows),
        }

    except HTTPException:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise HTTPException(500, f"재매핑 실패: {str(e)}")
    finally:
        conn.close()
