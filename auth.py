import hashlib
import hmac
import json
import os
import time
import base64
import streamlit as st
import streamlit.components.v1 as components

from config import ROLES, BRANDING
from users import get_user

# 세션 유효 시간 (초) — 6시간
SESSION_TTL = 6 * 60 * 60


def _get_secret(key, default=None):
    """secrets.toml → 환경변수 순으로 값을 조회한다."""
    try:
        return st.secrets["auth"][key]
    except (KeyError, FileNotFoundError):
        env_key = f"AUTH_{key.upper()}"
        return os.environ.get(env_key, default)


def _get_signing_key():
    return _get_secret("salt", "uandi_default_salt")


def hash_password(plain):
    salt = _get_secret("salt", "uandi_default_salt")
    return hashlib.sha256((salt + plain).encode()).hexdigest()


def verify_password(plain, stored_hash):
    return hash_password(plain) == stored_hash


# ============================================================
# 세션 토큰 (URL query param으로 유지)
# ============================================================
def _create_token(username, role, branch_id):
    """HMAC 서명 토큰 생성 (URL-safe base64)."""
    payload = {"u": username, "r": role, "b": branch_id,
               "exp": int(time.time()) + SESSION_TTL}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    sig = hmac.new(_get_signing_key().encode(), raw.encode(), hashlib.sha256).hexdigest()[:12]
    token = base64.urlsafe_b64encode((raw + "|" + sig).encode()).decode()
    return token


def _verify_token(token):
    """토큰 검증 → payload dict 또는 None."""
    if not token:
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        raw, sig = decoded.rsplit("|", 1)
        expected = hmac.new(_get_signing_key().encode(), raw.encode(), hashlib.sha256).hexdigest()[:12]
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(raw)
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


# ============================================================
# 로그인 페이지
# ============================================================
def show_login_page():
    st.markdown("""<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>""", unsafe_allow_html=True)

    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown("")
        st.markdown("")
        st.title("유앤아이의원")
        st.caption("통합 관리 시스템")
        st.markdown("")

        with st.form("login_form"):
            username = st.text_input("사용자 ID")
            password = st.text_input("비밀번호", type="password")
            submitted = st.form_submit_button("로그인", type="primary", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.error("ID와 비밀번호를 입력해주세요.")
                else:
                    user = get_user(username)
                    if user is None:
                        st.error("사용자를 찾을 수 없습니다.")
                    elif not verify_password(password, user["password_hash"]):
                        st.error("비밀번호가 올바르지 않습니다.")
                    else:
                        # 세션 설정
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = user["username"]
                        st.session_state["role"] = user["role"]
                        st.session_state["branch_id"] = user.get("branch_id")
                        # 토큰을 URL query param에 설정 (새로고침 시 유지됨)
                        token = _create_token(user["username"], user["role"], user.get("branch_id"))
                        st.query_params["t"] = token
                        st.rerun()

        st.markdown("")
        st.caption(BRANDING)

    return False


# ============================================================
# 인증 게이트
# ============================================================
def require_auth():
    """인증 확인. query param 't'에 유효한 토큰이 있으면 자동 로그인."""
    # 이미 인증됨
    if st.session_state.get("authenticated", False):
        return True

    # URL의 토큰으로 세션 복원
    token = st.query_params.get("t", None)
    if token:
        payload = _verify_token(token)
        if payload:
            st.session_state["authenticated"] = True
            st.session_state["username"] = payload["u"]
            st.session_state["role"] = payload["r"]
            st.session_state["branch_id"] = payload.get("b")
            return True
        else:
            # 토큰 만료/무효 → 제거
            del st.query_params["t"]

    show_login_page()
    return False


def get_current_role():
    return st.session_state.get("role", "viewer")


def get_user_branch_id():
    return st.session_state.get("branch_id")


def get_permissions():
    return ROLES.get(get_current_role(), ROLES["viewer"])


def show_user_info_sidebar():
    username = st.session_state.get("username", "")
    role = get_current_role()
    role_label = ROLES.get(role, {}).get("label", role)

    st.markdown(f"**{username}** · `{role_label}`")

    if st.button("로그아웃", use_container_width=True):
        # URL에서 토큰 제거
        if "t" in st.query_params:
            del st.query_params["t"]
        for key in ["authenticated", "username", "role", "branch_id",
                     "_users_cache", "pending_photo_changes"]:
            st.session_state.pop(key, None)
        st.rerun()
