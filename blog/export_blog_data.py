"""
블로그 데이터 SQL 덤프 내보내기/가져오기

로컬에서 Notion API로 수집한 블로그 데이터를 서버에 반영할 때 사용.
equipment.db와 별개로 블로그 관련 테이블만 처리.

사용:
  내보내기: python blog/export_blog_data.py export
  가져오기: python blog/export_blog_data.py import
"""

import sqlite3
import os
import sys
import json
import gzip

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "equipment.db")
DUMP_PATH = os.path.join(os.path.dirname(__file__), "blog_data.json.gz")

TABLES = ["blog_posts", "blog_accounts", "notion_sync_log", "blog_sync_log", "app_settings"]


def export_data():
    """블로그 관련 테이블을 JSON으로 내보내기."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    dump = {}
    for table in TABLES:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            dump[table] = [dict(r) for r in rows]
            print(f"  {table}: {len(rows)}건")
        except Exception as e:
            print(f"  {table}: 스킵 ({e})")

    conn.close()

    with gzip.open(DUMP_PATH, "wt", encoding="utf-8") as f:
        json.dump(dump, f, ensure_ascii=False, indent=None)

    size_mb = os.path.getsize(DUMP_PATH) / 1024 / 1024
    print(f"\n내보내기 완료: {DUMP_PATH} ({size_mb:.1f}MB)")


def import_data():
    """JSON 덤프를 DB에 가져오기 (기존 데이터 교체)."""
    if not os.path.exists(DUMP_PATH):
        print(f"덤프 파일 없음: {DUMP_PATH}")
        sys.exit(1)

    with gzip.open(DUMP_PATH, "rt", encoding="utf-8") as f:
        dump = json.load(f)

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")

    for table, rows in dump.items():
        if not rows:
            print(f"  {table}: 0건 (스킵)")
            continue

        # 기존 데이터 삭제 후 삽입
        conn.execute(f"DELETE FROM {table}")

        cols = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)

        for row in rows:
            vals = [row.get(c) for c in cols]
            try:
                conn.execute(f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})", vals)
            except Exception:
                pass  # 스키마 차이 무시

        print(f"  {table}: {len(rows)}건 반영")

    conn.commit()
    conn.close()
    print("\n가져오기 완료")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("export", "import"):
        print("사용: python blog/export_blog_data.py [export|import]")
        sys.exit(1)

    if sys.argv[1] == "export":
        print("블로그 데이터 내보내기...")
        export_data()
    else:
        print("블로그 데이터 가져오기...")
        import_data()
