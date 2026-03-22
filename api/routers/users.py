"""Users 라우터 — 사용자 CRUD (admin 전용)."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from api.auth_jwt import hash_password
from api.deps import require_role
from api.models import UserCreate, UserUpdate

from users import (
    load_users, add_user, remove_user,
    update_user_role, update_user_password, update_user_memo,
)

router = APIRouter()
_admin = require_role("admin")


@router.get("")
async def list_users(user: Annotated[dict, Depends(_admin)]):
    users = load_users()
    return [
        {"username": u["username"], "role": u["role"],
         "branch_id": u["branch_id"], "memo": u.get("memo", "")}
        for u in users
    ]


@router.post("")
async def create_user(req: UserCreate, user: Annotated[dict, Depends(_admin)]):
    pw_hash = hash_password(req.password)
    ok = add_user(req.username, pw_hash, req.role, req.branch_id, req.memo)
    if not ok:
        raise HTTPException(status_code=409, detail="이미 존재하는 사용자입니다.")

    return {"ok": True, "username": req.username}


@router.delete("/{username}")
async def delete_user(username: str, user: Annotated[dict, Depends(_admin)]):
    ok = remove_user(username)
    if not ok:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    return {"ok": True}


@router.patch("/{username}")
async def update_user(username: str, req: UserUpdate, user: Annotated[dict, Depends(_admin)]):
    if req.role is not None:
        update_user_role(username, req.role)
    if req.password is not None:
        pw_hash = hash_password(req.password)
        update_user_password(username, pw_hash)
    if req.memo is not None:
        update_user_memo(username, req.memo)

    return {"ok": True}
