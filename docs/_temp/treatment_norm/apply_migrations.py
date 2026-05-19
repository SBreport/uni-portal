"""
마이그레이션 적용 스크립트
1. 백업 생성
2. 001 SQL 적용 (이미 적용됐으면 스킵)
3. 002 SQL 적용
4. 검증
"""
import sqlite3
import sys
import io
import shutil
import os
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = "C:/LocalGD/7_CODE/uni-portal/data/equipment.db"
BACKUP_DIR = "C:/LocalGD/7_CODE/uni-portal/_백업"
NOW = datetime.now().strftime("%Y-%m-%dT%H%M%S")
BACKUP_PATH = f"{BACKUP_DIR}/equipment_2026-05-19_T{NOW}_pre_2-6.db"

# 백업 생성
os.makedirs(BACKUP_DIR, exist_ok=True)
shutil.copy2(DB, BACKUP_PATH)
backup_size = os.path.getsize(BACKUP_PATH) / (1024*1024)
print(f"백업 완료: {BACKUP_PATH} ({backup_size:.1f} MB)")

conn = sqlite3.connect(DB)
conn.text_factory = str
cur = conn.cursor()

# 현재 상태 확인
cur.execute("SELECT COUNT(*) FROM device_info")
di_before = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM equipment")
eq_before = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM equipment WHERE device_info_id IS NULL")
unlinked_before = cur.fetchone()[0]
cur.execute("SELECT name FROM pragma_table_info('device_info') WHERE name='primary_category_id'")
has_col = bool(cur.fetchone())

print(f"\n적용 전 상태:")
print(f"  device_info: {di_before}")
print(f"  equipment: {eq_before}")
print(f"  unlinked: {unlinked_before}")
print(f"  has primary_category_id: {has_col}")

# 001 이미 적용 여부 확인
# - B 작업: id=12, id=24 삭제됐는지 확인
cur.execute("SELECT COUNT(*) FROM device_info WHERE id IN (12, 24)")
deleted_check = cur.fetchone()[0]
print(f"\n001 적용 여부 체크 (id=12,24 존재): {deleted_check}")

if deleted_check == 0:
    print("001 이미 적용됨 — 스킵")
    apply_001 = False
else:
    print("001 미적용 — 적용 진행")
    apply_001 = True

conn.close()

# 001 적용
if apply_001:
    print("\n=== 001 SQL 적용 ===")
    with open("C:/LocalGD/7_CODE/uni-portal/docs/_temp/treatment_norm/migrations/001_treatment_norm_stage_2-1to4.sql", "r", encoding="utf-8") as f:
        sql_001 = f.read()

    conn = sqlite3.connect(DB)
    conn.text_factory = str
    try:
        conn.executescript(sql_001)
        conn.commit()
        print("001 적용 완료")
    except Exception as e:
        conn.rollback()
        print(f"001 적용 실패: {e}")
        raise
    finally:
        conn.close()
else:
    print("\n=== 001 스킵 (이미 적용됨) ===")

# 001 적용 후 상태
conn = sqlite3.connect(DB)
conn.text_factory = str
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM device_info")
di_after_001 = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM equipment WHERE device_info_id IS NULL")
unlinked_after_001 = cur.fetchone()[0]
print(f"\n001 적용 후: device_info={di_after_001}, unlinked={unlinked_after_001}")

# 002 적용 여부 확인
cur.execute("SELECT name FROM pragma_table_info('device_info') WHERE name='primary_category_id'")
has_col_002 = bool(cur.fetchone())
print(f"\n002 적용 여부 체크 (primary_category_id 존재): {has_col_002}")

conn.close()

if has_col_002:
    print("002 이미 적용됨 — 스킵")
else:
    print("\n=== 002 SQL 적용 ===")
    with open("C:/LocalGD/7_CODE/uni-portal/docs/_temp/treatment_norm/migrations/002_treatment_norm_stage_2-6_and_manual4.sql", "r", encoding="utf-8") as f:
        sql_002 = f.read()

    conn = sqlite3.connect(DB)
    conn.text_factory = str
    try:
        conn.executescript(sql_002)
        conn.commit()
        print("002 적용 완료")
    except Exception as e:
        conn.rollback()
        print(f"002 적용 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()

# ===========================
# 최종 검증
# ===========================
print("\n=== 최종 검증 ===")
conn = sqlite3.connect(DB)
conn.text_factory = str
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM device_info")
di_final = cur.fetchone()[0]
print(f"device_info count: {di_final} (기대: 233)")

cur.execute("SELECT COUNT(*) FROM equipment")
eq_final = cur.fetchone()[0]
print(f"equipment count: {eq_final}")

cur.execute("SELECT COUNT(*) FROM equipment WHERE device_info_id IS NULL")
unlinked_final = cur.fetchone()[0]
print(f"equipment unlinked: {unlinked_final} (기대: ~1-3)")

cur.execute("SELECT COUNT(*) FROM device_info WHERE primary_category_id IS NOT NULL")
filled = cur.fetchone()[0]
print(f"primary_category_id filled: {filled} (기대: 228)")

cur.execute("SELECT COUNT(*) FROM device_info WHERE primary_category_id IS NULL")
nulls = cur.fetchone()[0]
print(f"primary_category_id NULL: {nulls} (기대: 4-5)")

# NULL이 있는 device_info
cur.execute("""
    SELECT id, name FROM device_info WHERE primary_category_id IS NULL ORDER BY id
""")
null_rows = cur.fetchall()
print(f"\nprimary_category_id가 NULL인 device_info ({len(null_rows)}건):")
for r in null_rows:
    print(f"  id={r[0]}: {r[1]}")

# eq.id=80 삭제 확인
cur.execute("SELECT COUNT(*) FROM equipment WHERE id=80")
print(f"\neq.id=80 존재: {cur.fetchone()[0]} (기대: 0)")

# 광교 비타민/크라이오 삽입 확인
cur.execute("SELECT id, name, device_info_id FROM equipment WHERE branch_id=2 AND name IN ('비타민','크라이오')")
new_rows = cur.fetchall()
print(f"광교 비타민/크라이오 신규: {new_rows} (기대: 2건)")

# eq.id=614 정정 확인
cur.execute("SELECT id, name, device_info_id FROM equipment WHERE id=614")
print(f"eq.id=614: {cur.fetchone()} (기대: '올리지오 키스', di=31)")

# eq.id=685 삭제 확인
cur.execute("SELECT COUNT(*) FROM equipment WHERE id=685")
print(f"eq.id=685 존재: {cur.fetchone()[0]} (기대: 0)")

# 목포 실리프팅 6종 확인
cur.execute("SELECT id, name, device_info_id FROM equipment WHERE branch_id=17 AND name IN ('실루엣소프트','민트실','실루엣픽스실','옥토실','엠보스몰드실','모노실')")
silk_rows = cur.fetchall()
print(f"목포 실리프팅 6종: {len(silk_rows)}건")
for r in silk_rows:
    print(f"  {r}")

# eq.id=690 LPL 확인
cur.execute("SELECT id, name, device_info_id, note FROM equipment WHERE id=690")
print(f"eq.id=690: {cur.fetchone()} (기대: 'LPL', di=LPL_id)")

# LPL device_info 확인
cur.execute("SELECT id, name, category, aliases FROM device_info WHERE name='LPL'")
print(f"LPL device_info: {cur.fetchone()}")

# 실리프팅 aliases 확인
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=72")
print(f"실리프팅 aliases: {cur.fetchone()}")

# 올리지오X aliases 확인
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=31")
print(f"올리지오X aliases: {cur.fetchone()}")

conn.close()

print("\n=== 검증 완료 ===")
print(f"백업 경로: {BACKUP_PATH}")
