"""Cafe 라우터 — 카페 마케팅 원고 관리 (17개 엔드포인트)."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user, require_role
from api.models import (
    BranchPeriodCreate, ArticleUpdate, StatusChange,
    PublishInfo, CommentUpsert, FeedbackCreate, CafeSyncRequest,
)

from cafe.db import (
    load_cafe_periods, get_or_create_period, get_or_create_branch_period,
    update_branch_metadata, load_branch_period_meta,
    load_cafe_articles, load_cafe_article_detail, update_article,
    change_status, set_published_info,
    upsert_comment, add_feedback, load_status_history,
    load_cafe_summary, get_equipment_context,
)

router = APIRouter()
_branch = require_role("branch")


# ── 기간 ──
@router.get("/periods")
async def get_periods(user: Annotated[dict, Depends(get_current_user)]):
    return load_cafe_periods()


# ── 지점 목록 (evt_branches 재사용) ──
@router.get("/branches")
async def get_branches(user: Annotated[dict, Depends(get_current_user)]):
    from events.db import load_evt_branches
    return load_evt_branches()


# ── 지점-기간 ──
@router.post("/branch-periods")
async def create_branch_period(
    req: BranchPeriodCreate,
    user: Annotated[dict, Depends(_branch)],
):
    period_id = get_or_create_period(req.year, req.month)
    bp_id = get_or_create_branch_period(period_id, req.branch_id)
    return {"branch_period_id": bp_id, "period_id": period_id}


@router.get("/branch-periods/{bp_id}/meta")
async def get_branch_period_meta(
    bp_id: int,
    user: Annotated[dict, Depends(get_current_user)],
):
    meta = load_branch_period_meta(bp_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Not found")
    return dict(meta)


@router.patch("/branch-periods/{bp_id}/meta")
async def update_bp_meta(
    bp_id: int,
    updates: dict,
    user: Annotated[dict, Depends(_branch)],
):
    update_branch_metadata(bp_id, **updates)
    return {"ok": True}


# ── 원고 목록 ──
@router.get("/branch-periods/{bp_id}/articles")
async def get_articles(
    bp_id: int,
    user: Annotated[dict, Depends(get_current_user)],
):
    df = load_cafe_articles(bp_id)
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


# ── 원고 상세 ──
@router.get("/articles/{article_id}")
async def get_article_detail(
    article_id: int,
    user: Annotated[dict, Depends(get_current_user)],
):
    detail = load_cafe_article_detail(article_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="원고를 찾을 수 없습니다.")
    return detail


@router.patch("/articles/{article_id}")
async def patch_article(
    article_id: int,
    req: ArticleUpdate,
    user: Annotated[dict, Depends(_branch)],
):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        update_article(article_id, **updates)
    return {"ok": True}


# ── 상태 변경 ──
@router.post("/articles/{article_id}/status")
async def post_status(
    article_id: int,
    req: StatusChange,
    user: Annotated[dict, Depends(_branch)],
):
    changed_by = req.changed_by or user["username"]
    change_status(article_id, req.new_status, changed_by, req.note)
    return {"ok": True}


# ── 발행 정보 ──
@router.post("/articles/{article_id}/publish")
async def post_publish(
    article_id: int,
    req: PublishInfo,
    user: Annotated[dict, Depends(_branch)],
):
    published_by = req.published_by or user["username"]
    set_published_info(article_id, req.url, published_by)
    return {"ok": True}


# ── 댓글 ──
@router.put("/articles/{article_id}/comments/{slot}")
async def put_comment(
    article_id: int,
    slot: int,
    req: CommentUpsert,
    user: Annotated[dict, Depends(_branch)],
):
    upsert_comment(article_id, slot, req.comment_text, req.reply_text)
    return {"ok": True}


# ── 피드백 ──
@router.post("/articles/{article_id}/feedbacks")
async def post_feedback(
    article_id: int,
    req: FeedbackCreate,
    user: Annotated[dict, Depends(_branch)],
):
    add_feedback(article_id, req.author, req.content)
    return {"ok": True}


# ── 상태 이력 ──
@router.get("/articles/{article_id}/history")
async def get_history(
    article_id: int,
    user: Annotated[dict, Depends(get_current_user)],
):
    return load_status_history(article_id)


# ── 대시보드 요약 ──
@router.get("/summary/{period_id}")
async def get_summary(
    period_id: int,
    user: Annotated[dict, Depends(get_current_user)],
):
    rows = load_cafe_summary(period_id)
    # DB 컬럼명 → 프론트엔드 필드명 매핑
    rename = {
        "total_articles": "total",
        "cnt_waiting": "작성대기",
        "cnt_written": "작성완료",
        "cnt_revision": "수정요청",
        "cnt_reviewed": "검수완료",
        "cnt_published": "발행완료",
        "cnt_hold": "보류",
    }
    for r in rows:
        for old_key, new_key in rename.items():
            if old_key in r:
                r[new_key] = r.pop(old_key)
    return rows


# ── 장비 컨텍스트 ──
@router.get("/equipment-context")
async def get_equip_context(
    branch_name: str = Query(...),
    equipment_name: str = Query(...),
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    return get_equipment_context(branch_name, equipment_name)


# ── 시트 동기화 (admin) ──
@router.post("/sync")
async def post_sync(
    req: CafeSyncRequest,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    import re, os, traceback

    # URL에서 시트 ID 추출
    sheet_id = ""
    if req.sheet_url:
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", req.sheet_url)
        if m:
            sheet_id = m.group(1)
        else:
            sheet_id = req.sheet_url.strip()  # ID 직접 입력 대비

    # 시트 ID가 있으면 환경변수 임시 오버라이드
    if sheet_id:
        os.environ["CAFE_SHEET_ID"] = sheet_id

    try:
        from cafe.sync import run_cafe_import
        result = run_cafe_import(req.year, req.month, req.branch_filter)
        return result
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[CAFE SYNC ERROR] {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"동기화 오류: {str(e)}")
