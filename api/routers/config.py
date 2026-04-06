"""앱 설정 라우터 — GET /config/agency-map."""

import json
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user
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
