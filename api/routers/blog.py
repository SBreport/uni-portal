"""블로그 게시글 API 라우터."""

import os
import sys
import sqlite3
import subprocess
import shutil
from typing import Optional
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from pydantic import BaseModel

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
    post_type_main: Optional[str] = None,
    blog_id: Optional[str] = None,
    keyword: Optional[str] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    author: Optional[str] = None,
    branch_name: Optional[str] = None,
    project_month: Optional[str] = None,
    needs_review: Optional[int] = None,
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
    if post_type_main:
        conditions.append("post_type_main = ?")
        params.append(post_type_main)
    if blog_id:
        conditions.append("blog_id = ?")
        params.append(blog_id)
    if keyword:
        conditions.append("keyword LIKE ?")
        params.append(f"%{keyword}%")
    if search:
        conditions.append("(title LIKE ? OR keyword LIKE ? OR tags LIKE ? OR clean_title LIKE ?)")
        params.extend([f"%{search}%"] * 4)
    if date_from:
        conditions.append("published_at >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("published_at <= ?")
        params.append(date_to)
    if author:
        conditions.append("(author_main = ? OR author LIKE ?)")
        params.extend([author, f"%{author}%"])
    if branch_name:
        conditions.append("branch_name = ?")
        params.append(branch_name)
    if project_month:
        conditions.append("project_month = ?")
        params.append(project_month)
    if needs_review is not None:
        conditions.append("needs_review = ?")
        params.append(needs_review)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    total = conn.execute(f"SELECT COUNT(*) FROM blog_posts {where}", params).fetchone()[0]

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"""SELECT id, content_number, title, keyword, tags, post_type,
                   blog_channel, blog_id, post_number, platform,
                   published_url, author, published_at, status, project, exposure_rank,
                   branch_name, slot_number, post_type_main, post_type_sub,
                   project_month, project_branch, status_clean, clean_title,
                   author_main, author_sub, needs_review
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

    channels = conn.execute(
        "SELECT blog_channel, COUNT(*) as cnt FROM blog_posts GROUP BY blog_channel ORDER BY cnt DESC"
    ).fetchall()

    types_main = conn.execute(
        "SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != '' GROUP BY post_type_main ORDER BY cnt DESC"
    ).fetchall()

    authors = conn.execute(
        "SELECT author_main as author, COUNT(*) as cnt FROM blog_posts WHERE author_main != '' GROUP BY author_main ORDER BY cnt DESC"
    ).fetchall()

    accounts = conn.execute(
        "SELECT blog_id, blog_channel, COUNT(*) as cnt FROM blog_posts WHERE blog_id != '' GROUP BY blog_id ORDER BY cnt DESC LIMIT 30"
    ).fetchall()

    branches = conn.execute(
        "SELECT branch_name, COUNT(*) as cnt FROM blog_posts WHERE branch_name != '' GROUP BY branch_name ORDER BY cnt DESC"
    ).fetchall()

    project_months = conn.execute(
        "SELECT project_month, COUNT(*) as cnt FROM blog_posts WHERE project_month != '' GROUP BY project_month ORDER BY project_month DESC"
    ).fetchall()

    sync = conn.execute(
        "SELECT csv_modified_at, imported_at, imported_rows, skipped_rows FROM blog_sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    conn.close()
    return {
        "channels": [dict(c) for c in channels],
        "post_types_main": [dict(t) for t in types_main],
        "authors": [dict(a) for a in authors],
        "accounts": [dict(a) for a in accounts],
        "branches": [dict(b) for b in branches],
        "project_months": [dict(m) for m in project_months],
        "last_sync": dict(sync) if sync else None,
    }


# ── 대시보드 ──
@router.get("/dashboard")
def blog_dashboard():
    conn = _conn()

    total = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]
    by_channel = conn.execute(
        "SELECT blog_channel, COUNT(*) as cnt FROM blog_posts GROUP BY blog_channel"
    ).fetchall()
    review_count = conn.execute(
        "SELECT COUNT(*) FROM blog_posts WHERE needs_review = 1"
    ).fetchone()[0]

    by_type = conn.execute(
        "SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != '' GROUP BY post_type_main ORDER BY cnt DESC"
    ).fetchall()

    by_branch = conn.execute(
        "SELECT branch_name, COUNT(*) as cnt FROM blog_posts WHERE branch_name != '' GROUP BY branch_name ORDER BY cnt DESC LIMIT 15"
    ).fetchall()

    monthly = conn.execute("""
        SELECT project_month as month, COUNT(*) as cnt
        FROM blog_posts
        WHERE project_month != ''
        GROUP BY project_month ORDER BY project_month DESC LIMIT 12
    """).fetchall()

    recent = conn.execute("""
        SELECT id, clean_title, keyword, blog_channel, post_type_main, author_main, published_at, status_clean
        FROM blog_posts
        WHERE published_at != ''
        ORDER BY published_at DESC LIMIT 10
    """).fetchall()

    conn.close()
    return {
        "total": total,
        "by_channel": {r["blog_channel"]: r["cnt"] for r in by_channel},
        "review_count": review_count,
        "by_type": [dict(r) for r in by_type],
        "by_branch": [dict(r) for r in by_branch],
        "monthly": [dict(m) for m in monthly],
        "recent": [dict(r) for r in recent],
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
        "SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != '' GROUP BY post_type_main ORDER BY cnt DESC LIMIT 10"
    ).fetchall()
    paper_posts = conn.execute(
        "SELECT COUNT(*) FROM blog_posts WHERE post_type_main = '논문글'"
    ).fetchone()[0]

    monthly = conn.execute("""
        SELECT project_month as month, COUNT(*) as cnt
        FROM blog_posts
        WHERE project_month != ''
        GROUP BY project_month ORDER BY project_month DESC LIMIT 6
    """).fetchall()

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


# ── 계정 관리 ──
@router.get("/accounts")
def list_accounts(
    channel: Optional[str] = None,
    search: Optional[str] = None,
):
    conn = _conn()
    conditions = []
    params = []

    if channel:
        conditions.append("ba.channel = ?")
        params.append(channel)
    if search:
        conditions.append("(ba.blog_id LIKE ? OR ba.account_name LIKE ? OR ba.account_group LIKE ?)")
        params.extend([f"%{search}%"] * 3)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    rows = conn.execute(f"""
        SELECT ba.*,
               COUNT(bp.id) as post_count,
               MAX(bp.published_at) as last_published
        FROM blog_accounts ba
        LEFT JOIN blog_posts bp ON bp.blog_id = ba.blog_id
        {where}
        GROUP BY ba.id
        ORDER BY post_count DESC
    """, params).fetchall()

    conn.close()
    return {"items": [dict(r) for r in rows]}


class AccountUpdate(BaseModel):
    account_name: Optional[str] = None
    account_group: Optional[str] = None
    channel: Optional[str] = None
    note: Optional[str] = None


@router.patch("/accounts/{blog_id}")
def update_account(blog_id: str, body: AccountUpdate, user: dict = Depends(require_role("editor"))):
    conn = _conn()
    existing = conn.execute("SELECT id FROM blog_accounts WHERE blog_id = ?", (blog_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404, "계정을 찾을 수 없습니다")

    updates = []
    params = []
    for field in ["account_name", "account_group", "channel", "note"]:
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val)

    if not updates:
        conn.close()
        return {"message": "변경 없음"}

    params.append(blog_id)
    conn.execute(f"UPDATE blog_accounts SET {', '.join(updates)} WHERE blog_id = ?", params)
    conn.commit()
    conn.close()
    return {"message": "수정 완료"}


# ── CSV 업로드 (관리자 전용) ──
@router.post("/upload-csv")
def upload_csv(file: UploadFile = File(...), user: dict = Depends(require_role("admin"))):
    """관리자가 노션 CSV를 업로드하여 blog_posts를 갱신."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "CSV 파일만 업로드 가능합니다")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

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


# ── Notion 동기화 (관리자 전용) ──
class NotionSyncRequest(BaseModel):
    token: str
    full: bool = False


@router.post("/sync-notion")
def sync_notion(body: NotionSyncRequest, user: dict = Depends(require_role("admin"))):
    """Notion API 증분 동기화. 마지막 동기화 이후 수정된 페이지만 처리."""
    from blog.sync_notion import incremental_sync, NOTION_BLOG_DB_ID
    try:
        result = incremental_sync(body.token, NOTION_BLOG_DB_ID, dry_run=False)
        return result
    except Exception as e:
        raise HTTPException(500, f"동기화 실패: {str(e)}")


@router.get("/sync-notion/status")
def sync_notion_status():
    """마지막 Notion 동기화 상태 조회."""
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM notion_sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return {"last_sync": None}
    return {"last_sync": dict(row)}
