"""Equipment 라우터 — 보유장비 + 장비사전 (10개 엔드포인트)."""

from typing import Annotated, Optional
import math
from fastapi import APIRouter, Depends, HTTPException, Query


def _clean_df(df):
    if df is None:
        return []
    return [{k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
             for k, v in row.items()} for row in df.to_dict(orient="records")]

from api.deps import get_current_user, require_role
from api.models import EquipmentUpdate, PhotoChangeItem, DeviceInfoUpsert

from equipment.db import (
    load_data, get_branches, get_categories,
    update_equipment, save_photo_changes,
    get_all_device_info, search_device_info, find_matching_devices,
    upsert_device_info, delete_device_info,
)

router = APIRouter()
_branch = require_role("branch")
_editor = require_role("editor")


# ── 장비 목록 ──
@router.get("")
async def get_equipment(
    user: Annotated[dict, Depends(get_current_user)],
    branch: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    df = load_data()
    if df.empty:
        return []

    # 컬럼명 정규화 (DB 쿼리가 '지점명', '순번'을 반환하므로)
    rename_map = {}
    if "지점명" in df.columns and "지점" not in df.columns:
        rename_map["지점명"] = "지점"
    if "순번" in df.columns and "id" not in df.columns:
        rename_map["순번"] = "id"
    if rename_map:
        df = df.rename(columns=rename_map)

    # 사진 값 정규화 ('O' → '있음')
    if "사진" in df.columns:
        df["사진"] = df["사진"].apply(lambda x: "있음" if str(x).strip() in ("O", "o", "있음") else "")

    # 필터 적용
    if branch:
        df = df[df["지점"] == branch]
    if category:
        df = df[df["카테고리"] == category]
    if search:
        mask = df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
        df = df[mask]
    return _clean_df(df)


@router.get("/branches")
async def get_branch_list(user: Annotated[dict, Depends(get_current_user)]):
    return get_branches()


@router.get("/categories")
async def get_category_list(user: Annotated[dict, Depends(get_current_user)]):
    return get_categories()


@router.patch("/{eq_id}")
async def patch_equipment(
    eq_id: int,
    req: EquipmentUpdate,
    user: Annotated[dict, Depends(_branch)],
):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        update_equipment(eq_id, **updates)
    return {"ok": True}


@router.post("/photo-changes")
async def post_photo_changes(
    changes: list[PhotoChangeItem],
    user: Annotated[dict, Depends(_branch)],
):
    change_list = [(c.equipment_id, c.photo_status) for c in changes]
    ok, errors = save_photo_changes(change_list)
    return {"ok": ok, "errors": errors}


# ── 장비 사전 ──
@router.get("/device-info")
async def get_device_info_list(user: Annotated[dict, Depends(get_current_user)]):
    return get_all_device_info()


@router.get("/device-info/search")
async def search_devices(
    q: str = Query(...),
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    return search_device_info(q)


@router.get("/device-info/match")
async def match_devices(
    name: str = Query(...),
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    return find_matching_devices(name)


@router.post("/device-info")
async def create_device_info(
    req: DeviceInfoUpsert,
    user: Annotated[dict, Depends(_editor)],
):
    upsert_device_info(
        name=req.name, category=req.category, summary=req.summary,
        target=req.target, mechanism=req.mechanism, note=req.note,
        aliases=req.aliases, is_verified=req.is_verified,
    )
    return {"ok": True}


@router.delete("/device-info/{name}")
async def remove_device_info(
    name: str,
    user: Annotated[dict, Depends(_editor)],
):
    delete_device_info(name)
    return {"ok": True}


# ── 동기화 (admin) ──
@router.post("/sync")
async def post_sync(
    user: Annotated[dict, Depends(require_role("admin"))],
):
    from equipment.sync import sync_from_sheets
    result = sync_from_sheets()
    return result


@router.post("/device-info/update-counts")
async def post_update_counts(
    user: Annotated[dict, Depends(_editor)],
):
    from equipment.db import update_device_usage_counts
    update_device_usage_counts()
    return {"ok": True}


@router.post("/device-info/sync-json")
async def post_sync_json(
    user: Annotated[dict, Depends(_editor)],
):
    from equipment.db import seed_device_info_from_json
    seed_device_info_from_json()
    return {"ok": True}
