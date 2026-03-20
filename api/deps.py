"""FastAPI 의존성 주입 모듈.

- get_current_user: Authorization 헤더에서 JWT 검증
- require_role: 역할 기반 접근 제어
"""

import sys
import os
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 프로젝트 루트를 sys.path에 추가 (기존 모듈 import용)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.auth_jwt import verify_access_token

security = HTTPBearer()

# 역할 계층 (높을수록 권한 많음)
ROLE_HIERARCHY = {"viewer": 0, "branch": 1, "editor": 2, "admin": 3}


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> dict:
    """JWT 토큰에서 사용자 정보 추출."""
    payload = verify_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "username": payload["sub"],
        "role": payload["role"],
        "branch_id": payload.get("branch_id"),
    }


def require_role(min_role: str):
    """최소 역할 요구 의존성 팩토리."""
    min_level = ROLE_HIERARCHY.get(min_role, 0)

    async def _check(user: Annotated[dict, Depends(get_current_user)]) -> dict:
        user_level = ROLE_HIERARCHY.get(user["role"], 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"'{min_role}' 이상의 권한이 필요합니다.",
            )
        return user

    return _check
