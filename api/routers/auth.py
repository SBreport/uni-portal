"""Auth 라우터 — 로그인, 현재 사용자 조회."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from api.auth_jwt import verify_password, create_access_token
from api.deps import get_current_user
from api.models import LoginRequest, TokenResponse, UserInfo

from users import get_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = get_user(req.username)
    if user is None or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID 또는 비밀번호가 올바르지 않습니다.",
        )
    token = create_access_token(user["username"], user["role"], user.get("branch_id"))
    return TokenResponse(
        access_token=token,
        username=user["username"],
        role=user["role"],
        branch_id=user.get("branch_id"),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: Annotated[dict, Depends(get_current_user)]):
    return UserInfo(**user)
