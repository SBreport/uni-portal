"""
사용자 관리 모듈 (SQLite 기반)
- publish/users.py 의 Google Sheets 버전을 SQLite로 대체
"""

import sqlite3
import os
import json

from shared.db import get_conn as _shared_get_conn, SYSTEM_DB

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = SYSTEM_DB

# 마이그레이션: equipment.db에서 users 테이블을 system.db로 복사
def _migrate_users_if_needed():
    """system.db가 없거나 비어있으면 equipment.db에서 users를 복사."""
    old_db = os.path.join(DB_DIR, "equipment.db")
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        # system.db 생성 + users 테이블
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username      TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role          TEXT DEFAULT 'viewer',
                branch_id     INTEGER,
                memo          TEXT DEFAULT '',
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # equipment.db에서 복사
        if os.path.exists(old_db):
            try:
                old_conn = sqlite3.connect(old_db)
                old_conn.row_factory = sqlite3.Row
                rows = old_conn.execute("SELECT username, password_hash, role, branch_id, memo FROM users").fetchall()
                for r in rows:
                    conn.execute(
                        "INSERT OR IGNORE INTO users (username, password_hash, role, branch_id, memo) VALUES (?,?,?,?,?)",
                        (r["username"], r["password_hash"], r["role"], r["branch_id"], r["memo"] if "memo" in r.keys() else "")
                    )
                old_conn.close()
            except Exception as e:
                print(f"[WARN] users 마이그레이션 실패: {e}")
        conn.commit()
        conn.close()

_migrate_users_if_needed()


def _get_conn():
    return _shared_get_conn(SYSTEM_DB)


def load_users():
    """사용자 목록을 로드한다."""
    users = []

    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("SELECT username, password_hash, role, branch_id, memo, permissions FROM users ORDER BY username")
            for row in c.fetchall():
                users.append({
                    "username": row["username"],
                    "password_hash": row["password_hash"],
                    "role": row["role"],
                    "branch_id": row["branch_id"],
                    "memo": row["memo"] if "memo" in row.keys() else "",
                    "permissions": row["permissions"] if "permissions" in row.keys() else "[]",
                })
        finally:
            conn.close()
    except Exception:
        pass

    # DB에 사용자가 없으면 bootstrap admin 사용 (환경변수)
    if not users:
        try:
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

    return users


def get_user(username):
    """사용자명으로 사용자 정보를 반환한다."""
    for user in load_users():
        if user["username"] == username:
            return user
    return None


def add_user(username, password_hash, role, branch_id=None, memo="", permissions="[]"):
    """사용자를 추가한다."""
    if get_user(username):
        return False, f"'{username}' 은(는) 이미 존재합니다."

    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (username, password_hash, role, branch_id, memo, permissions) VALUES (?, ?, ?, ?, ?, ?)",
                (username, password_hash, role, branch_id, memo, permissions),
            )
            conn.commit()
            return True, f"'{username}' 사용자가 추가되었습니다."
        finally:
            conn.close()
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
        try:
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            if c.rowcount == 0:
                return False, f"'{username}' 을(를) 찾을 수 없습니다."
            conn.commit()
            return True, f"'{username}' 사용자가 삭제되었습니다."
        finally:
            conn.close()
    except Exception as e:
        return False, f"삭제 실패: {e}"


def update_user_role(username, new_role):
    """사용자 역할을 변경한다."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username))
            if c.rowcount == 0:
                return False, f"'{username}' 을(를) 찾을 수 없습니다."
            conn.commit()
            return True, f"'{username}' 역할이 변경되었습니다."
        finally:
            conn.close()
    except Exception as e:
        return False, f"역할 변경 실패: {e}"


def update_user_password(username, new_password_hash):
    """사용자 비밀번호를 변경한다."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_password_hash, username))
            if c.rowcount == 0:
                return False, f"'{username}' 을(를) 찾을 수 없습니다."
            conn.commit()
            return True, f"'{username}' 비밀번호가 변경되었습니다."
        finally:
            conn.close()
    except Exception as e:
        return False, f"비밀번호 변경 실패: {e}"


def update_user_memo(username, memo):
    """사용자 비고를 변경한다."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("UPDATE users SET memo = ? WHERE username = ?", (memo, username))
            if c.rowcount == 0:
                return False, f"'{username}' 을(를) 찾을 수 없습니다."
            conn.commit()
            return True, f"'{username}' 비고가 변경되었습니다."
        finally:
            conn.close()
    except Exception as e:
        return False, f"비고 변경 실패: {e}"


def ensure_memo_column():
    """기존 DB에 memo 컬럼이 없으면 추가한다."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("PRAGMA table_info(users)")
            cols = [row["name"] for row in c.fetchall()]
            if "memo" not in cols:
                c.execute("ALTER TABLE users ADD COLUMN memo TEXT DEFAULT ''")
                conn.commit()
        finally:
            conn.close()
    except Exception:
        pass


def ensure_permissions_column():
    """기존 DB에 permissions 컬럼이 없으면 추가한다."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("PRAGMA table_info(users)")
            cols = [row["name"] for row in c.fetchall()]
            if "permissions" not in cols:
                c.execute("ALTER TABLE users ADD COLUMN permissions TEXT DEFAULT '[]'")
                conn.commit()
        finally:
            conn.close()
    except Exception:
        pass

ensure_permissions_column()


def update_user_permissions(username, permissions_json):
    """사용자 권한 태그를 변경한다."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("UPDATE users SET permissions = ? WHERE username = ?", (permissions_json, username))
            if c.rowcount == 0:
                return False, f"'{username}' 을(를) 찾을 수 없습니다."
            conn.commit()
            return True, f"'{username}' 권한이 변경되었습니다."
        finally:
            conn.close()
    except Exception as e:
        return False, f"권한 변경 실패: {e}"


def get_user_permissions(username):
    """사용자 권한 태그 목록을 반환한다."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute("SELECT permissions FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            if row and row["permissions"]:
                return json.loads(row["permissions"])
            return []
        finally:
            conn.close()
    except Exception:
        return []
