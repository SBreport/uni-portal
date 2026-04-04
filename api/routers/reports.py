"""보고서 라우터."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from api.deps import get_current_user, require_role

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary")
async def get_summary(user: Annotated[dict, Depends(get_current_user)]):
    """전 지점 요약."""
    from reports.generator import get_all_branches_summary
    return get_all_branches_summary()


@router.get("/branch/{branch_id}")
async def get_branch_report(
    branch_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """지점별 상세 보고서 (월별 필터 지원)."""
    if user["role"] == "branch" and user["branch_id"] != branch_id:
        raise HTTPException(403, "자기 지점만 조회 가능합니다.")

    from reports.generator import get_branch_report
    report = get_branch_report(branch_id, year, month)
    if not report:
        raise HTTPException(404, "지점을 찾을 수 없습니다.")
    return report


@router.get("/branch/{branch_id}/export", response_class=HTMLResponse)
async def export_branch_report(
    branch_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """지점별 보고서 HTML 내보내기 (월별 필터 지원)."""
    if user["role"] == "branch" and user["branch_id"] != branch_id:
        raise HTTPException(403, "자기 지점만 조회 가능합니다.")

    from reports.export import render_html_report
    html = render_html_report(branch_id, year, month)
    return HTMLResponse(content=html)
