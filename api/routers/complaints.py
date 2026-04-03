"""민원 관리 라우터."""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from api.deps import require_role, get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/complaints", tags=["Complaints"])


class ComplaintCreate(BaseModel):
    branch_id: int
    title: str
    content: str = ""
    category: str = ""
    severity: str = "normal"
    assigned_to: str = ""


class ComplaintUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None


class StatusChange(BaseModel):
    new_status: str
    note: str = ""


@router.get("/summary/counts")
async def summary_counts(user: Annotated[dict, Depends(get_current_user)]):
    from complaints.db import count_complaints
    branch_id = user["branch_id"] if user["role"] == "branch" else None
    return count_complaints(branch_id)


@router.get("")
async def list_complaints(
    user: Annotated[dict, Depends(get_current_user)],
    branch_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = 1,
):
    from complaints.db import list_complaints
    # branch role: only own branch
    if user["role"] == "branch":
        branch_id = user["branch_id"]
    return list_complaints(branch_id, status, page)


@router.get("/{complaint_id}")
async def get_complaint(complaint_id: int, user: Annotated[dict, Depends(get_current_user)]):
    from complaints.db import get_complaint
    item = get_complaint(complaint_id)
    if not item:
        raise HTTPException(404, "not found")
    if user["role"] == "branch" and item["branch_id"] != user["branch_id"]:
        raise HTTPException(403, "forbidden")
    return item


@router.post("")
async def create_complaint(req: ComplaintCreate, user: Annotated[dict, Depends(get_current_user)]):
    from complaints.db import create_complaint
    data = req.model_dump()
    data["reported_by"] = user["username"]
    if user["role"] == "branch":
        data["branch_id"] = user["branch_id"]
    cid = create_complaint(data)
    return {"ok": True, "id": cid}


@router.patch("/{complaint_id}")
async def update_complaint(complaint_id: int, req: ComplaintUpdate, user: Annotated[dict, Depends(require_role("editor"))]):
    from complaints.db import update_complaint
    update_complaint(complaint_id, req.model_dump(exclude_none=True))
    return {"ok": True}


@router.post("/{complaint_id}/status")
async def change_status(complaint_id: int, req: StatusChange, user: Annotated[dict, Depends(get_current_user)]):
    from complaints.db import change_status
    ok, msg = change_status(complaint_id, req.new_status, user["username"], req.note)
    if not ok:
        raise HTTPException(400, msg)
    return {"ok": True}


@router.get("/{complaint_id}/logs")
async def get_logs(complaint_id: int, user: Annotated[dict, Depends(get_current_user)]):
    from complaints.db import get_complaint_logs
    return get_complaint_logs(complaint_id)
