"""
사용자 관리 모듈 (SQLite 기반)
- publish/users.py 의 Google Sheets 버전을 SQLite로 대체
"""

import sqlite3
import os
import streamlit as st

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_users():
    """사용자 목록을 로드한다. 캐시는 session_state에 저장."""
    if "_users_cache" in st.session_state:
        return st.session_state["_users_cache"]

    users = []

    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("SELECT username, password_hash, role, branch_id FROM users ORDER BY username")
        for row in c.fetchall():
            users.append({
                "username": row["username"],
                "password_hash": row["password_hash"],
                "role": row["role"],
                "branch_id": row["branch_id"],
            })
        conn.close()
    except Exception:
        pass

    # DB에 사용자가 없으면 bootstrap admin 사용
    # secrets.toml → 환경변수 순으로 조회
    if not users:
        try:
            admin_id = None
            admin_pw_hash = None
            admin_role = "admin"
            try:
                auth_secrets = st.secrets["auth"]
                admin_id = auth_secrets["bootstrap_admin_id"]
                admin_pw_hash = auth_secrets["bootstrap_admin_pw_hash"]
                admin_role = auth_secrets.get("bootstrap_admin_role", "admin")
            except (KeyError, FileNotFoundError):
                admin_id = os.environ.get("AUTH_BOOTSTRAP_ADMIN_ID")
                admin_pw_hash = os.environ.get("AUTH_BOOTSTRAP_ADMIN_PW_HASH")
                admin_role = os.environ.get("AUTH_BOOTSTRAP_ADMIN_ROLE", "admin")

            if admin_id and admin_pw_hash:
                users.append({
                    "username": admin_id,
                    "password_hash": admin_pw_hash,
                    "role": admin_role,
                    "branch_id": None,
                })
        except Exception:
            pass

    st.session_state["_users_cache"] = users
    return users


def get_user(username):
    """사용자명으로 사용자 정보를 반환한다."""
    for user in load_users():
        if user["username"] == username:
            return user
    return None


def add_user(username, password_hash, role, branch_id=None):
    """사용자를 추가한다."""
    if get_user(username):
        return False, f"'{username}' 은(는) 이미 존재합니다."

    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password_hash, role, branch_id) VALUES (?, ?, ?, ?)",
            (username, password_hash, role, branch_id),
        )
        conn.commit()
        conn.close()
        invalidate_users_cache()
        return True, f"'{username}' 사용자가 추가되었습니다."
    except Exception as e:
        return False, f"추가 실패: {e}"


def remove_user(username):
    """사용자를 삭제한다."""
    users = load_users()
    admins = [u for u in users if u["role"] == "admin"]
    target = get_user(username)
    if target and target["role"] == "admin" and len(admins) <= 1:
        return False, "마지막 관리자는 삭제할 수 없습니다."

    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username = ?", (username,))
        if c.rowcount == 0:
            conn.close()
            return False, f"'{username}' 을(를) 찾을 수 없습니다."
        conn.commit()
        conn.close()
        invalidate_users_cache()
        return True, f"'{username}' 사용자가 삭제되었습니다."
    except Exception as e:
        return False, f"삭제 실패: {e}"


def update_user_role(username, new_role):
    """사용자 역할을 변경한다."""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
        if c.rowcount == 0:
            conn.close()
            return False, f"'{username}' 을(를) 찾을 수 없습니다."
        conn.commit()
        conn.close()
        invalidate_users_cache()
        return True, f"'{username}' 역할이 변경되었습니다."
    except Exception as e:
        return False, f"역할 변경 실패: {e}"


def update_user_password(username, new_password_hash):
    """사용자 비밀번호를 변경한다."""
    try:
        conn = _get_conn()
        c = conn.cursor()
        c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_password_hash, username))
        if c.rowcount == 0:
            conn.close()
            return False, f"'{username}' 을(를) 찾을 수 없습니다."
        conn.commit()
        conn.close()
        invalidate_users_cache()
        return True, f"'{username}' 비밀번호가 변경되었습니다."
    except Exception as e:
        return False, f"비밀번호 변경 실패: {e}"


def invalidate_users_cache():
    st.session_state.pop("_users_cache", None)
