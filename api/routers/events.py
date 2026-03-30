"""Events 라우터 — 이벤트 조회 + 시술사전 (12개 엔드포인트)."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from api.deps import get_current_user, require_role
from api.models import TreatmentUpdate, TreatmentCreate, EventSyncRequest

from events.db import (
    load_current_events, load_evt_branches, load_evt_categories, load_evt_periods,
    load_price_history, search_by_treatment, load_event_summary,
    load_treatment_dictionary, update_treatment_info, add_treatment_entry,
)

router = APIRouter()
_editor = require_role("editor")


@router.get("")
async def get_events(user: Annotated[dict, Depends(get_current_user)]):
    rows, is_fallback = load_current_events()
    return {"data": rows or [], "is_fallback": is_fallback}


@router.get("/branches")
async def get_branches(user: Annotated[dict, Depends(get_current_user)]):
    return load_evt_branches()


@router.get("/categories")
async def get_categories(user: Annotated[dict, Depends(get_current_user)]):
    return load_evt_categories()


@router.get("/periods")
async def get_periods(user: Annotated[dict, Depends(get_current_user)]):
    return load_evt_periods()


@router.get("/price-history")
async def get_price_history(
    branch_name: str = Query(...),
    event_name: str = Query(...),
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    rows = load_price_history(branch_name, event_name)
    return rows or []


@router.get("/search")
async def search_events(
    q: str = Query(...),
    period_id: Optional[int] = None,
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    rows = search_by_treatment(q, period_id)
    return rows or []


@router.get("/summary")
async def get_summary(user: Annotated[dict, Depends(get_current_user)]):
    rows = load_event_summary()
    return rows or []


# ── 시술 사전 ──
@router.get("/treatments")
async def get_treatments(user: Annotated[dict, Depends(get_current_user)]):
    rows = load_treatment_dictionary()
    return rows or []


@router.patch("/treatments/{treatment_id}")
async def patch_treatment(
    treatment_id: int,
    req: TreatmentUpdate,
    user: Annotated[dict, Depends(_editor)],
):
    ok = update_treatment_info(
        treatment_id,
        description=req.description,
        is_verified=req.is_verified,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="시술 정보를 찾을 수 없습니다.")
    return {"ok": True}


@router.post("/treatments")
async def create_treatment(
    req: TreatmentCreate,
    user: Annotated[dict, Depends(_editor)],
):
    ok = add_treatment_entry(req.name, req.brand, req.category_id, req.description)
    if not ok:
        raise HTTPException(status_code=409, detail="이미 존재하는 시술입니다.")
    return {"ok": True}


# ── 동기화 (admin) ──
@router.post("/sync")
async def post_sync(
    req: EventSyncRequest,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    from events.sync import run_event_sync_from_url
    if not req.source_url:
        raise HTTPException(status_code=400, detail="source_url이 필요합니다.")
    result = run_event_sync_from_url(req.source_url, req.year, req.start_month, req.end_month)
    return result


@router.post("/sync-file")
async def post_sync_file(
    year: int = Query(...),
    start_month: int = Query(...),
    end_month: int = Query(...),
    file: UploadFile = File(...),
    user: Annotated[dict, Depends(require_role("admin"))] = None,
):
    from events.sync import run_event_sync_from_file
    content = await file.read()
    result = run_event_sync_from_file(content, year, start_month, end_month)
    return result
