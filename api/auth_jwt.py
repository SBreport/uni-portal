"""JWT 토큰 생성/검증 모듈.

기존 auth.py의 HMAC 토큰 대신 표준 JWT(HS256) 사용.
비밀번호 해싱은 기존 auth.py의 로직을 그대로 재사용.
"""

import hashlib
import os
import time
import json
import hmac as _hmac
import base64

# JWT 라이브러리 (PyJWT)
import jwt

SESSION_TTL = 6 * 60 * 60  # 6시간


def _get_salt():
    salt = os.environ.get("AUTH_SALT")
    if not salt:
        # 하드코딩 폴백 금지: 비밀번호 해싱 salt는 반드시 환경변수로 주입.
        raise RuntimeError("AUTH_SALT 환경변수가 설정되지 않았습니다. 배포 환경에 반드시 설정하세요.")
    return salt


def _get_jwt_secret():
    # JWT 서명키를 비밀번호 salt와 분리한다(과거엔 salt 하나를 공유 → 노출 시 토큰 위조 가능).
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET 환경변수가 설정되지 않았습니다. 배포 환경에 반드시 설정하세요.")
    return secret


def hash_password(plain: str) -> str:
    """기존 auth.py와 동일한 해싱 — SHA256(salt + plain)."""
    salt = _get_salt()
    return hashlib.sha256((salt + plain).encode()).hexdigest()


def verify_password(plain: str, stored_hash: str) -> bool:
    if hash_password(plain) == stored_hash:
        return True
    # 전환기 호환: 옛 salt로 저장된 해시도 인정(AUTH_SALT_LEGACY 설정 시).
    # 사용자 락아웃 없이 salt를 갈아타기 위한 임시 경로. 마이그레이션 완료 후 이 환경변수를 제거할 것.
    legacy = os.environ.get("AUTH_SALT_LEGACY")
    if legacy:
        return hashlib.sha256((legacy + plain).encode()).hexdigest() == stored_hash
    return False


def create_access_token(username: str, role: str, branch_id: int | None, permissions: list[str] | None = None) -> str:
    """JWT 액세스 토큰 생성."""
    payload = {
        "sub": username,
        "role": role,
        "branch_id": branch_id,
        "permissions": permissions or [],
        "exp": int(time.time()) + SESSION_TTL,
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")


def verify_access_token(token: str) -> dict | None:
    """JWT 검증 → payload dict 또는 None."""
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
