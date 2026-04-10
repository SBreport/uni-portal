"""블로그 게시글 API 라우터.

SQL 로직은 blog/post_queries.py에 위임. 라우터는 요청/응답만 담당.
"""

import os
import sys
import shutil
import subprocess
from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from pydantic import BaseModel

from api.deps import require_role, get_current_user
from blog.post_queries import (
    list_posts, get_post, get_filter_options, get_dashboard, get_stats,
    list_accounts, update_account as _update_account,
    get_notion_token, get_notion_token_status, save_notion_token,
    get_last_sync_status,
)

router = APIRouter(prefix="/blog", tags=["Blog"])
_admin = require_role("admin")

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
UPLOAD_DIR = os.path.join(DB_DIR, "blog")


# ── 게시글 목록 (페이지네이션 + 필터) ──
@router.get("/posts")
def list_posts_api(
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
    return list_posts(
        page=page, per_page=per_page, channel=channel, platform=platform,
        post_type=post_type, post_type_main=post_type_main, blog_id=blog_id,
        keyword=keyword, search=search, date_from=date_from, date_to=date_to,
        author=author, branch_name=branch_name, project_month=project_month,
        needs_review=needs_review, branch_filter=branch_filter,
    )


# ── 게시글 상세 ──
@router.get("/posts/{post_id}")
def get_post_api(post_id: int):
    result = get_post(post_id)
    if not result:
        raise HTTPException(404, "게시글을 찾을 수 없습니다")
    return result


# ── 필터 옵션 (드롭다운용) ──
@router.get("/filter-options")
def filter_options_api(branch_filter: Optional[str] = None):
    return get_filter_options(branch_filter)


# ── 대시보드 ──
@router.get("/dashboard")
def blog_dashboard_api(
    branch_filter: Optional[str] = None,
    month: Optional[str] = None,
):
    return get_dashboard(branch_filter, month)


# ── 통계 ──
@router.get("/stats")
def blog_stats_api():
    return get_stats()


# ── 계정 관리 ──
@router.get("/accounts")
def list_accounts_api(
    channel: Optional[str] = None,
    search: Optional[str] = None,
    branch_filter: Optional[str] = None,
):
    return {"items": list_accounts(channel, search, branch_filter)}


class AccountUpdate(BaseModel):
    account_name: Optional[str] = None
    account_group: Optional[str] = None
    channel: Optional[str] = None
    note: Optional[str] = None


@router.patch("/accounts/{blog_id}")
def update_account_api(blog_id: str, body: AccountUpdate, user: dict = Depends(require_role("editor"))):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"message": "변경 없음"}
    if not _update_account(blog_id, updates):
        raise HTTPException(404, "계정을 찾을 수 없습니다")
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
    """Notion API 증분 동기화."""
    from blog.sync_notion import incremental_sync, NOTION_BLOG_DB_ID
    token = body.token.strip() if body.token else None
    if not token:
        token = get_notion_token()
    if not token:
        raise HTTPException(400, "Notion 토큰이 없습니다. 토큰을 입력하거나 먼저 저장해주세요.")
    try:
        return incremental_sync(token, NOTION_BLOG_DB_ID, dry_run=False)
    except Exception as e:
        raise HTTPException(500, f"동기화 실패: {str(e)}")


@router.get("/notion-token/status")
def notion_token_status_api(user: dict = Depends(require_role("admin"))):
    return get_notion_token_status()


class NotionTokenRequest(BaseModel):
    token: str


@router.post("/notion-token")
def save_notion_token_api(body: NotionTokenRequest, user: dict = Depends(require_role("admin"))):
    token = body.token.strip()
    if not token.startswith("ntn_"):
        raise HTTPException(400, "올바른 Notion 토큰 형식이 아닙니다 (ntn_...)")
    masked = save_notion_token(token)
    return {"message": f"토큰 저장 완료 ({masked})", "masked": masked}


@router.get("/sync-notion/status")
def sync_notion_status_api():
    last = get_last_sync_status()
    return {"last_sync": last}


# ── 제목 스크래핑 ──
@router.get("/scrape-titles/status")
def scrape_titles_status():
    from blog.scrape_titles import get_scrape_status
    return get_scrape_status()


class ScrapeTitlesRequest(BaseModel):
    limit: int = 0
    delay: float = 0.3
    include_cafe: bool = False


@router.post("/scrape-titles")
def scrape_titles(body: ScrapeTitlesRequest, user: dict = Depends(require_role("admin"))):
    from blog.scrape_titles import scrape_missing_titles
    try:
        result = scrape_missing_titles(limit=body.limit, delay=body.delay, include_cafe=body.include_cafe)
        return {"message": f"수집 {result['scraped']}건 완료", **result}
    except Exception as e:
        raise HTTPException(500, f"스크래핑 실패: {str(e)}")


# ── 계정 닉네임 수집 ──
@router.post("/scrape-nicknames")
def scrape_nicknames(user: dict = Depends(require_role("admin"))):
    from blog.scrape_titles import scrape_account_nicknames
    try:
        result = scrape_account_nicknames(delay=0.5)
        return {"message": f"닉네임 수집 {result['updated']}건 완료", **result}
    except Exception as e:
        raise HTTPException(500, f"닉네임 수집 실패: {str(e)}")


# ── URL 제목 수정 ──
@router.post("/fix-url-titles")
def fix_url_titles_api(user: dict = Depends(require_role("admin"))):
    from blog.scrape_titles import fix_url_titles
    try:
        result = fix_url_titles(delay=0.3)
        return {"message": f"URL 제목 수정 {result['fixed']}건 완료", **result}
    except Exception as e:
        raise HTTPException(500, f"URL 제목 수정 실패: {str(e)}")


# ── 데이터 품질 현황 ──
@router.get("/data-quality")
def data_quality_summary(user: dict = Depends(require_role("admin"))):
    """블로그 데이터 품질 현황 — 삭제/미수집/검토필요 건수."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        total = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]
        deleted = conn.execute(
            "SELECT COUNT(*) FROM blog_posts WHERE scraped_title = '(삭제됨)'"
        ).fetchone()[0]
        cafe_fail = conn.execute(
            "SELECT COUNT(*) FROM blog_posts WHERE scraped_title = '(카페-수집불가)'"
        ).fetchone()[0]
        needs_review = conn.execute(
            "SELECT COUNT(*) FROM blog_posts WHERE needs_review = 1"
        ).fetchone()[0]
        no_title = conn.execute(
            "SELECT COUNT(*) FROM blog_posts WHERE (title IS NULL OR title = '') "
            "AND (scraped_title IS NULL OR scraped_title = '') "
            "AND published_url IS NOT NULL AND published_url != ''"
        ).fetchone()[0]
        no_branch = conn.execute(
            "SELECT COUNT(*) FROM blog_posts WHERE evt_branch_id IS NULL "
            "AND branch_name LIKE '유앤%'"
        ).fetchone()[0]
        return {
            "total": total,
            "deleted": deleted,
            "cafe_fail": cafe_fail,
            "needs_review": needs_review,
            "no_title": no_title,
            "no_branch": no_branch,
        }
    finally:
        conn.close()


@router.get("/data-quality/details")
def data_quality_details(
    category: str = Query(..., description="deleted|cafe_fail|needs_review|no_title|no_branch"),
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(require_role("admin")),
):
    """데이터 품질 문제 건 상세 목록."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        conditions = {
            "deleted": "scraped_title = '(삭제됨)'",
            "cafe_fail": "scraped_title = '(카페-수집불가)'",
            "needs_review": "needs_review = 1",
            "no_title": "(title IS NULL OR title = '') AND (scraped_title IS NULL OR scraped_title = '') "
                        "AND published_url IS NOT NULL AND published_url != ''",
            "no_branch": "evt_branch_id IS NULL AND branch_name LIKE '유앤%'",
        }
        where = conditions.get(category)
        if not where:
            return {"items": [], "total": 0}

        total = conn.execute(f"SELECT COUNT(*) FROM blog_posts WHERE {where}").fetchone()[0]
        rows = conn.execute(f"""
            SELECT id, COALESCE(clean_title, scraped_title, title) AS title,
                   keyword, blog_channel, branch_name, published_url,
                   published_at, author, scraped_title, needs_review
            FROM blog_posts WHERE {where}
            ORDER BY published_at DESC LIMIT ?
        """, (limit,)).fetchall()
        return {"items": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


# ── 블로그 데이터 임포트 ──
@router.post("/import-data")
def import_blog_data(user: dict = Depends(require_role("admin"))):
    from blog.export_blog_data import import_data, DUMP_PATH
    if not os.path.exists(DUMP_PATH):
        raise HTTPException(404, "blog_data.json.gz 파일이 없습니다")
    try:
        import_data()
        return {"message": "블로그 데이터 임포트 완료"}
    except Exception as e:
        raise HTTPException(500, f"임포트 실패: {str(e)}")


# ── 활성 블로그 계정 (지점별, 3개월 내 브랜드블로그 발행) ──
@router.get("/active-accounts")
def get_active_accounts(
    branch_filter: str = Query("uandi"),
    user: dict = Depends(get_current_user),
):
    """지점별 활성 블로그 계정 (3개월 내 브랜드블로그 발행 계정)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT bp.blog_id, COUNT(*) as post_count,
                   ba.blog_nickname, eb.name as branch_name
            FROM blog_posts bp
            LEFT JOIN blog_accounts ba ON bp.blog_id = ba.blog_id
            LEFT JOIN evt_branches eb ON bp.evt_branch_id = eb.id
            WHERE bp.blog_channel = 'br'
            AND bp.published_at >= date('now', '-3 months')
            AND bp.blog_id IS NOT NULL AND bp.blog_id != ''
            AND bp.evt_branch_id IS NOT NULL
            GROUP BY bp.evt_branch_id, bp.blog_id
            ORDER BY eb.name, post_count DESC
        """).fetchall()

        branch_map: dict[str, list] = {}
        for r in rows:
            bn = r["branch_name"] or "미지정"
            branch_map.setdefault(bn, []).append({
                "blog_id": r["blog_id"],
                "nickname": r["blog_nickname"] or r["blog_id"],
                "post_count": r["post_count"],
            })

        branches = [
            {"branch_name": k, "accounts": v}
            for k, v in sorted(branch_map.items())
        ]
        return {"branches": branches}
    finally:
        conn.close()


# ── 스케줄러 상태/트리거 ──
@router.get("/scheduler/status")
async def scheduler_status(user: Annotated[dict, Depends(_admin)]):
    from api.scheduler import get_scheduler_status
    return get_scheduler_status()


@router.post("/scheduler/trigger")
async def scheduler_trigger(user: Annotated[dict, Depends(_admin)]):
    from api.scheduler import _run_blog_sync
    import asyncio
    asyncio.create_task(_run_blog_sync())
    return {"ok": True, "message": "sync triggered"}
