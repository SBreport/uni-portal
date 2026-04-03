"""상위노출 (Place Ranking) API 라우터."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user

router = APIRouter(prefix="/place", tags=["Place"])


@router.get("/daily")
async def get_daily(
    branch_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT * FROM place_daily WHERE 1=1"
        params = []
        if branch_id:
            sql += " AND branch_id = ?"
            params.append(branch_id)
        if date_from:
            sql += " AND date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND date <= ?"
            params.append(date_to)
        sql += " ORDER BY date DESC, branch_name"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@router.get("/trends")
async def get_trends(branch_id: int, keyword: Optional[str] = None):
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT date, is_exposed, rank FROM place_daily WHERE branch_id = ?"
        params = [branch_id]
        if keyword:
            sql += " AND keyword = ?"
            params.append(keyword)
        sql += " ORDER BY date"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@router.get("/months")
def get_months(user: dict = Depends(get_current_user)):
    """사용 가능한 월별 시트 목록 반환."""
    try:
        from place.sheets import list_months
        return list_months()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"구글 시트 연결 실패: {e}")


@router.get("/ranking")
def get_ranking(
    month: str = Query(..., description="시트 이름 (예: '3월(2026년)')"),
    user: dict = Depends(get_current_user),
):
    """특정 월의 상위노출 데이터 반환."""
    try:
        from place.sheets import get_ranking
        return get_ranking(month)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"구글 시트 연결 실패: {e}")
