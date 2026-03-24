"""블로그 게시글 API 라우터."""

import os
import sqlite3
import subprocess
import shutil
from typing import Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, UploadFile, File

from api.deps import require_role, get_current_user
from fastapi import Depends

router = APIRouter(prefix="/blog", tags=["Blog"])

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")
UPLOAD_DIR = os.path.join(DB_DIR, "blog")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 게시글 목록 (페이지네이션 + 필터) ──
@router.get("/posts")
def list_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    channel: Optional[str] = None,
    platform: Optional[str] = None,
    post_type: Optional[str] = None,
    blog_id: Optional[str] = None,
    keyword: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    author: Optional[str] = None,
):
    conn = _conn()
    conditions = []
    params = []

    if channel:
        conditions.append("blog_channel = ?")
        params.append(channel)
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    if post_type:
        conditions.append("post_type LIKE ?")
        params.append(f"%{post_type}%")
    if blog_id:
        conditions.append("blog_id = ?")
        params.append(blog_id)
    if keyword:
        conditions.append("keyword LIKE ?")
        params.append(f"%{keyword}%")
    if search:
        conditions.append("(title LIKE ? OR keyword LIKE ? OR tags LIKE ?)")
        params.extend([f"%{search}%"] * 3)
    if date_from:
        conditions.append("published_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("published_at <= ?")
        params.append(date_to)
    if author:
        conditions.append("author = ?")
        params.append(author)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # 총 건수
    total = conn.execute(f"SELECT COUNT(*) FROM blog_posts {where}", params).fetchone()[0]

    # 페이지네이션
    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""SELECT id, content_number, title, keyword, tags, post_type,
                   blog_channel, blog_id, post_number, platform,
                   published_url, author, published_at, status, project, exposure_rank
            FROM blog_posts {where}
            ORDER BY published_at DESC, id DESC
            LIMIT ? OFFSET ?""",
        params + [per_page, offset]
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "items": [dict(r) for r in rows],
    }


# ── 게시글 상세 ──
@router.get("/posts/{post_id}")
def get_post(post_id: int):
    conn = _conn()
    row = conn.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "게시글을 찾을 수 없습니다")

    result = dict(row)

    # 연결된 논문 정보
    links = conn.execute("""
        SELECT pbl.*, p.title_ko, p.evidence_level, p.study_type
        FROM paper_blog_links pbl
        JOIN papers p ON p.id = pbl.paper_id
        WHERE pbl.blog_post_id = ?
    """, (post_id,)).fetchall()
    result["linked_papers"] = [dict(l) for l in links]

    conn.close()
    return result


# ── 필터 옵션 (드롭다운용) ──
@router.get("/filter-options")
def filter_options():
    conn = _conn()

    # 채널별 건수
    channels = conn.execute(
        "SELECT blog_channel, COUNT(*) as cnt FROM blog_posts GROUP BY blog_channel ORDER BY cnt DESC"
    ).fetchall()

    # 종류별 건수 (상위 20)
    types = conn.execute(
        "SELECT post_type, COUNT(*) as cnt FROM blog_posts WHERE post_type != '' GROUP BY post_type ORDER BY cnt DESC LIMIT 20"
    ).fetchall()

    # 작성자별 건수
    authors = conn.execute(
        "SELECT author, COUNT(*) as cnt FROM blog_posts WHERE author != '' GROUP BY author ORDER BY cnt DESC"
    ).fetchall()

    # 블로그 계정별 건수 (상위 30)
    accounts = conn.execute(
        "SELECT blog_id, blog_channel, COUNT(*) as cnt FROM blog_posts WHERE blog_id != '' GROUP BY blog_id ORDER BY cnt DESC LIMIT 30"
    ).fetchall()

    # 동기화 정보
    sync = conn.execute(
        "SELECT csv_modified_at, imported_at, imported_rows, skipped_rows FROM blog_sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    conn.close()
    return {
        "channels": [dict(c) for c in channels],
        "post_types": [dict(t) for t in types],
        "authors": [dict(a) for a in authors],
        "accounts": [dict(a) for a in accounts],
        "last_sync": dict(sync) if sync else None,
    }


# ── 통계 ──
@router.get("/stats")
def blog_stats():
    conn = _conn()

    total = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]
    by_channel = conn.execute(
        "SELECT blog_channel, COUNT(*) as cnt FROM blog_posts GROUP BY blog_channel"
    ).fetchall()
    by_type = conn.execute(
        "SELECT post_type, COUNT(*) as cnt FROM blog_posts WHERE post_type != '' GROUP BY post_type ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    paper_posts = conn.execute(
        "SELECT COUNT(*) FROM blog_posts WHERE post_type LIKE '%논문글%'"
    ).fetchone()[0]

    # 월별 발행 추이 (최근 6개월)
    monthly = conn.execute("""
        SELECT substr(published_at, 1, 7) as month, COUNT(*) as cnt
        FROM blog_posts
        WHERE published_at != '' AND published_at >= date('now', '-6 months')
        GROUP BY month ORDER BY month DESC
    """).fetchall()

    # 동기화 로그
    sync_log = conn.execute(
        "SELECT * FROM blog_sync_log ORDER BY id DESC LIMIT 5"
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "by_channel": {r["blog_channel"]: r["cnt"] for r in by_channel},
        "by_type": [dict(r) for r in by_type],
        "paper_posts": paper_posts,
        "monthly": [dict(m) for m in monthly],
        "sync_log": [dict(s) for s in sync_log],
    }


# ── CSV 업로드 (관리자 전용) ──
@router.post("/upload-csv")
def upload_csv(file: UploadFile = File(...), user: dict = Depends(require_role("admin"))):
    """관리자가 노션 CSV를 업로드하여 blog_posts를 갱신."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "CSV 파일만 업로드 가능합니다")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 파일 저장
    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # import_csv.py 실행
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    script = os.path.join(project_root, "blog", "import_csv.py")

    if not os.path.exists(script):
        raise HTTPException(500, "blog/import_csv.py를 찾을 수 없습니다")

    result = subprocess.run(
        [sys.executable, script, save_path],
        capture_output=True, text=True, timeout=300
    )

    if result.returncode != 0:
        raise HTTPException(500, f"임포트 실패: {result.stderr}")

    return {"message": "임포트 완료", "output": result.stdout}


import sys
