"""앱 설정 라우터 — GET/POST /config/agency-map."""

import json
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user, require_role
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/agency-map")
async def get_agency_map(
    user: Annotated[dict, Depends(get_current_user)],
    type: Literal["place", "webpage"] = Query(..., description="매핑 유형: place 또는 webpage"),
):
    """실행사 매핑 조회.

    Returns: {branch_name: agency_name, ...}
    """
    key = f"agency_map_{type}"
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"agency_map_{type} 설정이 없습니다.")
        return json.loads(row["value"])
    finally:
        conn.close()


@router.post("/agency-map")
def update_agency_map(
    body: dict,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    """실행사 매핑 저장 (admin 전용).

    Body: {"type": "place"|"webpage", "data": {branch: agency, ...}}
    """
    map_type = body.get("type")
    if map_type not in ("place", "webpage"):
        raise HTTPException(status_code=400, detail="type은 'place' 또는 'webpage'여야 합니다.")
    data = body.get("data", {})
    key = f"agency_map_{map_type}"
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings(key, value, updated_at) VALUES(?, ?, datetime('now'))",
            (key, json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/agency-sheets")
async def get_agency_sheets(
    user: Annotated[dict, Depends(get_current_user)],
):
    """실행사별 구글시트 설정 조회.

    Returns: {"애드드림즈": "sheet_id_or_url", ...}
    """
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'agency_sheets_place'"
        ).fetchone()
        if row is None:
            return {}
        return json.loads(row["value"])
    finally:
        conn.close()


@router.post("/agency-sheets")
def update_agency_sheets(
    body: dict,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    """실행사별 구글시트 설정 저장 (admin 전용).

    Body: {"data": {"애드드림즈": "sheet_id_or_url", ...}}
    """
    import re
    data = body.get("data", {})
    # URL에서 시트 ID 추출
    cleaned = {}
    for name, val in data.items():
        name = name.strip()
        val = val.strip()
        if not name or not val:
            continue
        # Google Sheets URL → ID 추출
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", val)
        if m:
            cleaned[name] = m.group(1)
        else:
            cleaned[name] = val  # Already an ID

    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings(key, value, updated_at) VALUES(?, ?, datetime('now'))",
            ("agency_sheets_place", json.dumps(cleaned, ensure_ascii=False)),
        )
        conn.commit()
        return {"ok": True, "saved": cleaned}
    finally:
        conn.close()
