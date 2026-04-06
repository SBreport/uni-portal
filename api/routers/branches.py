"""통합 지점 목록 라우터 — GET /branches."""

from typing import Annotated
from fastapi import APIRouter, Depends, Query

from api.deps import get_current_user
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("")
async def get_branches(
    user: Annotated[dict, Depends(get_current_user)],
    active_only: bool = Query(True, description="활성 지점만 반환 (기본값: true)"),
):
    """통합 지점 목록.

    Returns: [{id, name, short_name, region_name, is_active}]
    """
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = """
            SELECT
                eb.id,
                eb.name,
                eb.short_name,
                er.name AS region_name,
                eb.is_active
            FROM evt_branches eb
            LEFT JOIN evt_regions er ON eb.region_id = er.id
        """
        if active_only:
            sql += " WHERE eb.is_active = 1"
        sql += " ORDER BY eb.name"

        rows = conn.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
