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


import re as _re

def _normalize_branch(name: str) -> str:
    """project_branch 정규화: 핵심 지점명만 추출.
    '유앤아이 창원 - 추가 운영' → '유앤아이 창원'
    '하남미사 막글 작업' → '하남미사'
    '유앤명동 10월' → '유앤명동'
    '유앤수원 리뉴얼' → '유앤수원'
    '컴플란트치과 (x)' → '컴플란트치과'
    '유앤아이 안산ㅓ' → '유앤아이 안산'
    """
    name = name.strip()
    if not name:
        return name
    # (x) 종료 표시 제거
    name = _re.sub(r"\s*\(x\)\s*$", "", name)
    # " - " 이후 제거 (부가 설명)
    name = name.split(" - ")[0].strip()
    # 끝에 붙는 숫자월, 작업 설명 등 제거
    name = _re.sub(r"\s+\d+월$", "", name)
    name = _re.sub(r"\s+(막글\s*작업|리뉴얼|추가\s*운영|작업|마감|연장|재계약|신규)$", "", name)
    # 끝에 붙은 한글 자모 오타 제거 (ㅓ, ㅏ 등 낱자음/낱모음)
    name = _re.sub(r"[ㄱ-ㅎㅏ-ㅣ]+$", "", name)
    # 끝에 "점" 제거 (건대점 → 건대) — 같은 지점의 표기 통일
    name = _re.sub(r"점$", "", name)
    return name.strip()


def _merge_branches(rows) -> list:
    """정규화된 지점명으로 재그룹핑."""
    merged: dict[str, int] = {}
    for r in rows:
        key = _normalize_branch(r["project_branch"])
        if not key:
            continue
        merged[key] = merged.get(key, 0) + r["cnt"]
    result = [{"branch_name": k, "cnt": v} for k, v in merged.items()]
    result.sort(key=lambda x: x["cnt"], reverse=True)
    return result


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
    branch_filter: Optional[str] = None,
):
    conn = _conn()
    conditions = []
    params = []

    # 지점 필터 (uandi = 유앤아이 관련 게시글만)
    if branch_filter == "uandi":
        conditions.append("branch_name LIKE '%유앤%'")

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
        conditions.append("(branch_name = ? OR project_branch = ? OR project_branch LIKE ?)")
        params.extend([branch_name, branch_name, f"{branch_name}%"])
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
def filter_options(branch_filter: Optional[str] = None):
    conn = _conn()

    bf_where = " AND branch_name LIKE '%유앤%'" if branch_filter == "uandi" else ""
    bf_where_only = " WHERE branch_name LIKE '%유앤%'" if branch_filter == "uandi" else ""
    bf_pb = " AND project_branch LIKE '%유앤%'" if branch_filter == "uandi" else ""

    channels = conn.execute(
        f"SELECT blog_channel, COUNT(*) as cnt FROM blog_posts{bf_where_only} GROUP BY blog_channel ORDER BY cnt DESC"
    ).fetchall()

    types_main = conn.execute(
        f"SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != ''{bf_where} GROUP BY post_type_main ORDER BY cnt DESC"
    ).fetchall()

    authors = conn.execute(
        f"SELECT author_main as author, COUNT(*) as cnt FROM blog_posts WHERE author_main != ''{bf_where} GROUP BY author_main ORDER BY cnt DESC"
    ).fetchall()

    accounts = conn.execute(
        f"SELECT blog_id, blog_channel, COUNT(*) as cnt FROM blog_posts WHERE blog_id != ''{bf_where} GROUP BY blog_id ORDER BY cnt DESC LIMIT 30"
    ).fetchall()

    raw_branches = conn.execute(
        f"SELECT project_branch, COUNT(*) as cnt FROM blog_posts WHERE project_branch != ''{bf_pb} GROUP BY project_branch ORDER BY cnt DESC"
    ).fetchall()
    branches = _merge_branches(raw_branches)

    project_months = conn.execute(
        f"SELECT project_month, COUNT(*) as cnt FROM blog_posts WHERE project_month != ''{bf_where} GROUP BY project_month ORDER BY project_month DESC"
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
def blog_dashboard(
    branch_filter: Optional[str] = None,
    month: Optional[str] = None,
):
    conn = _conn()

    bf = " WHERE branch_name LIKE '%유앤%'" if branch_filter == "uandi" else ""
    bf_and = " AND branch_name LIKE '%유앤%'" if branch_filter == "uandi" else ""
    bf_pb = " AND project_branch LIKE '%유앤%'" if branch_filter == "uandi" else ""

    total = conn.execute(f"SELECT COUNT(*) FROM blog_posts{bf}").fetchone()[0]
    by_channel = conn.execute(
        f"SELECT blog_channel, COUNT(*) as cnt FROM blog_posts{bf} GROUP BY blog_channel"
    ).fetchall()
    review_count = conn.execute(
        f"SELECT COUNT(*) FROM blog_posts WHERE needs_review = 1{bf_and}"
    ).fetchone()[0]

    by_type = conn.execute(
        f"SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != ''{bf_and} GROUP BY post_type_main ORDER BY cnt DESC"
    ).fetchall()

    if month:
        raw_branch = conn.execute(
            f"SELECT project_branch, COUNT(*) as cnt FROM blog_posts WHERE project_branch != ''{bf_pb} AND project_month = ? GROUP BY project_branch ORDER BY cnt DESC",
            (month,)
        ).fetchall()
    else:
        raw_branch = conn.execute(
            f"SELECT project_branch, COUNT(*) as cnt FROM blog_posts WHERE project_branch != ''{bf_pb} GROUP BY project_branch ORDER BY cnt DESC"
        ).fetchall()
    # project_branch 정규화: "유앤아이 창원 - 추가 운영" → "유앤아이 창원" 등
    by_branch = _merge_branches(raw_branch)

    monthly = conn.execute(f"""
        SELECT project_month as month, COUNT(*) as cnt
        FROM blog_posts
        WHERE project_month != ''{bf_and}
        GROUP BY project_month ORDER BY project_month DESC LIMIT 6
    """).fetchall()

    # 주간 발행 추이 (최근 12주)
    weekly = conn.execute(f"""
        SELECT strftime('%Y-W%W', published_at) as week,
               MIN(published_at) as week_start,
               COUNT(*) as cnt
        FROM blog_posts
        WHERE published_at != '' AND published_at >= date('now', '-42 days'){bf_and}
        GROUP BY week ORDER BY week DESC
    """).fetchall()

    # 담당자별 게시글 수 (전체 또는 월간)
    if month:
        by_author = conn.execute(
            f"SELECT author_main, COUNT(*) as cnt FROM blog_posts WHERE author_main != ''{bf_and} AND project_month = ? GROUP BY author_main ORDER BY cnt DESC",
            (month,)
        ).fetchall()
    else:
        by_author = conn.execute(
            f"SELECT author_main, COUNT(*) as cnt FROM blog_posts WHERE author_main != ''{bf_and} GROUP BY author_main ORDER BY cnt DESC"
        ).fetchall()

    # 종류별 분포 (전체 또는 월간)
    by_type_monthly = None
    if month:
        by_type_monthly = [dict(r) for r in conn.execute(
            f"SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != ''{bf_and} AND project_month = ? GROUP BY post_type_main ORDER BY cnt DESC",
            (month,)
        ).fetchall()]

    # 이번주 발행글 (최근 7일)
    this_week = conn.execute(f"""
        SELECT id, clean_title, keyword, blog_channel, post_type_main, author_main, published_at, branch_name
        FROM blog_posts
        WHERE published_at >= date('now', '-7 days'){bf_and}
        ORDER BY published_at DESC
    """).fetchall()

    # 지난주 발행글 (7~14일 전)
    last_week = conn.execute(f"""
        SELECT id, clean_title, keyword, blog_channel, post_type_main, author_main, published_at, branch_name
        FROM blog_posts
        WHERE published_at >= date('now', '-14 days')
          AND published_at < date('now', '-7 days'){bf_and}
        ORDER BY published_at DESC
    """).fetchall()

    conn.close()
    result = {
        "total": total,
        "by_channel": {r["blog_channel"]: r["cnt"] for r in by_channel},
        "review_count": review_count,
        "by_type": [dict(r) for r in by_type],
        "by_branch": [dict(r) for r in by_branch],
        "monthly": [dict(m) for m in monthly],
        "weekly": [dict(w) for w in weekly],
        "by_author": [dict(a) for a in by_author],
        "this_week": [dict(r) for r in this_week],
        "last_week": [dict(r) for r in last_week],
    }
    if by_type_monthly is not None:
        result["by_type_monthly"] = by_type_monthly
    return result


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
        conditions.append("(ba.blog_id LIKE ? OR ba.account_name LIKE ? OR ba.blog_nickname LIKE ? OR ba.blog_title LIKE ?)")
        params.extend([f"%{search}%"] * 4)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    rows = conn.execute(f"""
        SELECT ba.*,
               COUNT(bp.id) as post_count,
               SUM(CASE WHEN bp.published_at >= date('now', '-30 days') THEN 1 ELSE 0 END) as recent_count,
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
    token: Optional[str] = None
    full: bool = False


@router.post("/sync-notion")
def sync_notion(body: NotionSyncRequest, user: dict = Depends(require_role("admin"))):
    """Notion API 증분 동기화. 토큰 미입력 시 저장된 토큰 사용."""
    from blog.sync_notion import incremental_sync, NOTION_BLOG_DB_ID
    token = body.token.strip() if body.token else None
    if not token:
        conn = _conn()
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'notion_token'").fetchone()
        conn.close()
        token = row["value"] if row else None
    if not token:
        raise HTTPException(400, "Notion 토큰이 없습니다. 토큰을 입력하거나 먼저 저장해주세요.")
    try:
        result = incremental_sync(token, NOTION_BLOG_DB_ID, dry_run=False)
        return result
    except Exception as e:
        raise HTTPException(500, f"동기화 실패: {str(e)}")


@router.get("/notion-token/status")
def notion_token_status(user: dict = Depends(require_role("admin"))):
    """저장된 Notion 토큰 존재 여부 확인 (토큰 값 자체는 반환하지 않음)."""
    conn = _conn()
    row = conn.execute("SELECT value, updated_at FROM app_settings WHERE key = 'notion_token'").fetchone()
    conn.close()
    if row and row["value"]:
        masked = row["value"][:8] + "..." + row["value"][-4:]
        return {"saved": True, "masked": masked, "updated_at": row["updated_at"]}
    return {"saved": False}


class NotionTokenRequest(BaseModel):
    token: str


@router.post("/notion-token")
def save_notion_token(body: NotionTokenRequest, user: dict = Depends(require_role("admin"))):
    """Notion 토큰을 서버에 저장."""
    token = body.token.strip()
    if not token.startswith("ntn_"):
        raise HTTPException(400, "올바른 Notion 토큰 형식이 아닙니다 (ntn_...)")
    conn = _conn()
    conn.execute(
        "INSERT INTO app_settings (key, value, updated_at) VALUES ('notion_token', ?, datetime('now','localtime')) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (token,),
    )
    conn.commit()
    conn.close()
    masked = token[:8] + "..." + token[-4:]
    return {"message": f"토큰 저장 완료 ({masked})", "masked": masked}


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


# ── 제목 스크래핑 ──
@router.get("/scrape-titles/status")
def scrape_titles_status():
    """스크래핑 대상 건수 조회."""
    from blog.scrape_titles import get_scrape_status
    return get_scrape_status()


class ScrapeTitlesRequest(BaseModel):
    limit: int = 0
    delay: float = 0.3
    include_cafe: bool = False


@router.post("/scrape-titles")
def scrape_titles(body: ScrapeTitlesRequest, user: dict = Depends(require_role("admin"))):
    """제목 없는 게시글의 URL에서 제목 스크래핑."""
    from blog.scrape_titles import scrape_missing_titles
    try:
        result = scrape_missing_titles(limit=body.limit, delay=body.delay, include_cafe=body.include_cafe)
        return {"message": f"수집 {result['scraped']}건 완료", **result}
    except Exception as e:
        raise HTTPException(500, f"스크래핑 실패: {str(e)}")


# ── 계정 닉네임 수집 ──
@router.post("/scrape-nicknames")
def scrape_nicknames(user: dict = Depends(require_role("admin"))):
    """닉네임이 없는 blog_accounts의 닉네임/타이틀을 스크래핑."""
    from blog.scrape_titles import scrape_account_nicknames
    try:
        result = scrape_account_nicknames(delay=0.5)
        return {"message": f"닉네임 수집 {result['updated']}건 완료", **result}
    except Exception as e:
        raise HTTPException(500, f"닉네임 수집 실패: {str(e)}")


# ── URL 제목 수정 (needs_review + URL 포함 제목) ──
@router.post("/fix-url-titles")
def fix_url_titles_api(user: dict = Depends(require_role("admin"))):
    """needs_review=1이면서 제목에 URL이 포함된 글의 실제 제목을 스크래핑."""
    from blog.scrape_titles import fix_url_titles
    try:
        result = fix_url_titles(delay=0.3)
        return {"message": f"URL 제목 수정 {result['fixed']}건 완료", **result}
    except Exception as e:
        raise HTTPException(500, f"URL 제목 수정 실패: {str(e)}")


# ── 블로그 데이터 임포트 (서버 DB에 로컬 덤프 반영) ──
@router.post("/import-data")
def import_blog_data(user: dict = Depends(require_role("admin"))):
    """blog_data.json.gz를 서버 DB에 임포트."""
    from blog.export_blog_data import import_data, DUMP_PATH
    if not os.path.exists(DUMP_PATH):
        raise HTTPException(404, "blog_data.json.gz 파일이 없습니다")
    try:
        import_data()
        return {"message": "블로그 데이터 임포트 완료"}
    except Exception as e:
        raise HTTPException(500, f"임포트 실패: {str(e)}")

