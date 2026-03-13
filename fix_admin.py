"""관리자 계정 복구 스크립트.

서버(Docker 컨테이너)에서 실행:
  docker exec -it <컨테이너명> python fix_admin.py

또는 로컬에서:
  python fix_admin.py
"""

import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "equipment.db")
SALT = os.environ.get("AUTH_SALT", "uandi_default_salt")


def hash_password(plain):
    return hashlib.sha256((SALT + plain).encode()).hexdigest()


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 현재 사용자 목록 출력
    print("=== 현재 등록된 사용자 ===")
    c.execute("SELECT username, role, branch_id FROM users ORDER BY username")
    rows = c.fetchall()
    if not rows:
        print("(사용자 없음)")
    for r in rows:
        print(f"  {r['username']:15s}  역할: {r['role']:10s}  지점: {r['branch_id'] or '-'}")

    print()

    # admin 계정 확인
    c.execute("SELECT username, role FROM users WHERE username = 'admin'")
    admin_row = c.fetchone()

    if admin_row:
        if admin_row["role"] != "admin":
            print(f"[!] 'admin' 계정이 있지만 역할이 '{admin_row['role']}'입니다.")
            c.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")
            print("[O] 역할을 'admin'으로 복구했습니다.")
        else:
            print("[O] 'admin' 계정 역할 정상 (admin)")

        # 비밀번호 리셋
        new_pw = input("새 비밀번호 입력 (Enter 시 'admin1234'): ").strip()
        if not new_pw:
            new_pw = "admin1234"
        pw_hash = hash_password(new_pw)
        c.execute("UPDATE users SET password_hash = ? WHERE username = 'admin'", (pw_hash,))
        print(f"[O] 'admin' 비밀번호 변경 완료 → '{new_pw}'")
    else:
        print("[!] 'admin' 계정이 없습니다. 새로 생성합니다.")
        new_pw = input("비밀번호 입력 (Enter 시 'admin1234'): ").strip()
        if not new_pw:
            new_pw = "admin1234"
        pw_hash = hash_password(new_pw)
        c.execute(
            "INSERT INTO users (username, password_hash, role, branch_id, memo) VALUES (?, ?, 'admin', NULL, '관리자 복구')",
            ("admin", pw_hash),
        )
        print(f"[O] 'admin' 계정 생성 완료 (비밀번호: '{new_pw}')")

    conn.commit()
    conn.close()
    print("\n완료. 앱에서 로그인하세요.")


if __name__ == "__main__":
    main()
