"""
지점명 통일 마이그레이션: 홍대신촌점 → 홍대점

사용법: docker exec -it <컨테이너명> python migrate_branch_name.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "equipment.db")

OLD_NAME = "홍대신촌점"
NEW_NAME = "홍대점"

OLD_SHORT = "홍대신촌"
NEW_SHORT = "홍대"


def migrate():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    changes = []

    # 1. 장비 branches 테이블
    c.execute("SELECT id FROM branches WHERE name = ?", (OLD_NAME,))
    old_row = c.fetchone()
    c.execute("SELECT id FROM branches WHERE name = ?", (NEW_NAME,))
    new_row = c.fetchone()

    if old_row and new_row:
        # 둘 다 존재 → 기존 장비를 새 지점으로 이동 후 옛 지점 삭제
        old_id, new_id = old_row[0], new_row[0]
        c.execute("UPDATE equipment SET branch_id = ? WHERE branch_id = ?", (new_id, old_id))
        cnt = c.rowcount
        c.execute("DELETE FROM branches WHERE id = ?", (old_id,))
        changes.append(f"[장비] branches: {OLD_NAME}(id={old_id}) 장비 {cnt}건 → {NEW_NAME}(id={new_id}) 이동, 옛 지점 삭제")
    elif old_row and not new_row:
        # 옛 이름만 존재 → 이름 변경
        c.execute("UPDATE branches SET name = ? WHERE id = ?", (NEW_NAME, old_row[0]))
        changes.append(f"[장비] branches: {OLD_NAME} → {NEW_NAME} 이름 변경")
    else:
        changes.append(f"[장비] branches: {OLD_NAME} 없음 (변경 불필요)")

    # 2. 이벤트 evt_branches 테이블
    c.execute("SELECT id FROM evt_branches WHERE name = ?", (OLD_NAME,))
    old_evt = c.fetchone()
    c.execute("SELECT id FROM evt_branches WHERE name = ?", (NEW_NAME,))
    new_evt = c.fetchone()

    if old_evt and new_evt:
        old_id, new_id = old_evt[0], new_evt[0]
        c.execute("UPDATE evt_items SET branch_id = ? WHERE branch_id = ?", (new_id, old_id))
        cnt = c.rowcount
        c.execute("DELETE FROM evt_branches WHERE id = ?", (old_id,))
        changes.append(f"[이벤트] evt_branches: {OLD_NAME}(id={old_id}) 이벤트 {cnt}건 → {NEW_NAME}(id={new_id}) 이동, 옛 지점 삭제")
    elif old_evt and not new_evt:
        c.execute("UPDATE evt_branches SET name = ?, short_name = ? WHERE id = ?",
                  (NEW_NAME, NEW_SHORT, old_evt[0]))
        changes.append(f"[이벤트] evt_branches: {OLD_NAME} → {NEW_NAME} 이름 변경")
    else:
        changes.append(f"[이벤트] evt_branches: {OLD_NAME} 없음 (변경 불필요)")

    conn.commit()
    conn.close()

    print("=" * 50)
    print("지점명 마이그레이션 완료")
    print("=" * 50)
    for c in changes:
        print(f"  {c}")
    print()


if __name__ == "__main__":
    migrate()
