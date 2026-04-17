"""place_daily UNIQUE 제약을 (date,branch_id,keyword) → (date,branch_name,keyword)로 마이그레이션.

로컬엔 이미 적용됐는데 웹 DB엔 미반영 상태.
branch_id가 전부 0인 상태라 옛 UNIQUE가 서로 다른 지점끼리 충돌시킴.
"""
import sqlite3
import shutil
from datetime import datetime

DB = "/app/data/equipment.db"
BACKUP = f"/app/data/equipment.db.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

print(f"1) 백업: {BACKUP}")
shutil.copy(DB, BACKUP)

c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

cur = c.execute("SELECT sql FROM sqlite_master WHERE name='place_daily'").fetchone()
print(f"2) 현재 스키마:\n{cur[0]}\n")

if "UNIQUE(date, branch_name, keyword)" in cur[0]:
    print("이미 마이그레이션됨. 종료.")
else:
    # 중복 체크
    dup = c.execute("""
        SELECT date, branch_name, keyword, COUNT(*) AS cnt
        FROM place_daily
        GROUP BY date, branch_name, keyword
        HAVING cnt > 1
        LIMIT 10
    """).fetchall()
    if dup:
        print("경고: 새 UNIQUE에 걸릴 중복 row 존재. 수동 정리 필요.")
        for r in dup:
            print(dict(r))
        raise SystemExit(1)

    print("3) 새 테이블 생성 + 데이터 복사 + 교체")
    c.executescript("""
        BEGIN;
        CREATE TABLE place_daily_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            branch_id INTEGER NOT NULL DEFAULT 0,
            branch_name TEXT NOT NULL,
            keyword TEXT NOT NULL,
            is_exposed INTEGER DEFAULT 0,
            rank INTEGER,
            source TEXT DEFAULT 'sheets',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            evt_branch_id INTEGER,
            UNIQUE(date, branch_name, keyword)
        );
        INSERT INTO place_daily_new (id, date, branch_id, branch_name, keyword, is_exposed, rank, source, created_at, evt_branch_id)
        SELECT id, date, branch_id, branch_name, keyword, is_exposed, rank, source, created_at, evt_branch_id FROM place_daily;
        DROP TABLE place_daily;
        ALTER TABLE place_daily_new RENAME TO place_daily;
        COMMIT;
    """)
    total = c.execute("SELECT COUNT(*) FROM place_daily").fetchone()[0]
    print(f"4) 완료. 총 row: {total}")

c.close()
