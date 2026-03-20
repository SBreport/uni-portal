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
    return os.environ.get("AUTH_SALT", "uandi_equipment_2026")


def hash_password(plain: str) -> str:
    """기존 auth.py와 동일한 해싱 — SHA256(salt + plain)."""
    salt = _get_salt()
    return hashlib.sha256((salt + plain).encode()).hexdigest()


def verify_password(plain: str, stored_hash: str) -> bool:
    return hash_password(plain) == stored_hash


def create_access_token(username: str, role: str, branch_id: int | None) -> str:
    """JWT 액세스 토큰 생성."""
    payload = {
        "sub": username,
        "role": role,
        "branch_id": branch_id,
        "exp": int(time.time()) + SESSION_TTL,
    }
    return jwt.encode(payload, _get_salt(), algorithm="HS256")


def verify_access_token(token: str) -> dict | None:
    """JWT 검증 → payload dict 또는 None."""
    try:
        payload = jwt.decode(token, _get_salt(), algorithms=["HS256"])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
