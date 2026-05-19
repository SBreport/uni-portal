"""
2-6 마이그레이션 SQL 생성 스크립트
- 001: 2-1~2-4 SQL 추출 (변경계획서에서)
- 002: primary_category_id + 수동 4건 + 다수결
"""
import sqlite3
import sys
import io
import os
import json
from collections import defaultdict
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB = "C:/LocalGD/7_CODE/uni-portal/data/equipment.db"
conn = sqlite3.connect(DB)
conn.text_factory = str
cur = conn.cursor()

# =========================================================
# 001 파일 생성 (2-1~2-4 SQL 추출)
# =========================================================

sql_001 = """\
-- ============================================================
-- 001_treatment_norm_stage_2-1to4.sql
-- 시술 정규화 2단계 (2-1~2-4) 마이그레이션
-- 생성일: 2026-05-19
-- 영향 row 수: device_info 8건 변경/삭제, equipment ~575건, evt_treatments 12건
-- 적용 전 백업 권장: _백업/equipment_2026-05-19_T100155.db
-- ============================================================

BEGIN TRANSACTION;

-- ============================================================
-- A. device_info alias 정리 (6건)
-- ============================================================

-- id=27 울쎄라피 프라임: "울쎄라" 단독 제거
UPDATE device_info
SET aliases = '["울쎄라피프라임","울쎄라피 프라임/","아이울쎄라피프라임"]',
    updated_at = datetime('now','+9 hours')
WHERE id = 27;

-- id=22 HPL: APL 계열 3개 제거
UPDATE device_info
SET aliases = '["hpl","HPL","hpl,apl"]',
    updated_at = datetime('now','+9 hours')
WHERE id = 22;

-- id=73 아쎄라: 바디 alias 2개 제거 (얼굴/페이스 유지)
UPDATE device_info
SET aliases = '["아쎄라 윤곽","얼굴아쎄라","페이스 아쎄라"]',
    updated_at = datetime('now','+9 hours')
WHERE id = 73;

-- id=86 하이드라페이셜: "아쿠아필" 제거 (aliases 비움)
UPDATE device_info
SET aliases = '[]',
    updated_at = datetime('now','+9 hours')
WHERE id = 86;

-- id=35 클라리티 프로: "클라리티" 단독 제거
UPDATE device_info
SET aliases = '["클라리티 롱펄","클라리티롱펄"]',
    updated_at = datetime('now','+9 hours')
WHERE id = 35;

-- id=46 피코플러스: "피코레이저" 제거
UPDATE device_info
SET aliases = '["피코플러스 MLA","피코플러스 토닝","피코플러스 피코프락셀","피코 플러스"]',
    updated_at = datetime('now','+9 hours')
WHERE id = 46;

-- ============================================================
-- B. device_info 통합 (2건)
-- ============================================================

-- B-1. CO2 통합: id=12 → id=62
UPDATE equipment
SET device_info_id = 62,
    updated_at = datetime('now','+9 hours')
WHERE device_info_id = 12;

UPDATE evt_treatments
SET device_info_id = 62,
    updated_at = datetime('now','+9 hours')
WHERE device_info_id = 12;

DELETE FROM device_info WHERE id = 12;

-- B-2. 아쎄라 통합: id=24 → id=73
UPDATE equipment
SET device_info_id = 73,
    updated_at = datetime('now','+9 hours')
WHERE device_info_id = 24;

UPDATE evt_treatments
SET device_info_id = 73,
    updated_at = datetime('now','+9 hours')
WHERE device_info_id = 24;

DELETE FROM device_info WHERE id = 24;

-- ============================================================
-- C. device_info 데이터 정정 (3건)
-- ============================================================

-- id=22 HPL: 분류 및 device_type 변경 (본문 PLACEHOLDER)
UPDATE device_info
SET category = '주사/부스터',
    device_type = 'injection',
    summary = '[PLACEHOLDER] HPL(Hydrolytic Phosphatidylcholine Lipolysis) 지방분해주사. 포스파티딜콜린 성분의 지방용해 주사.',
    mechanism = '[PLACEHOLDER] 포스파티딜콜린이 지방세포막을 파괴하여 지방 용해 및 흡수 촉진.',
    target = '[PLACEHOLDER] 국소지방(복부, 팔뚝, 허벅지), 체형 개선',
    updated_at = datetime('now','+9 hours')
WHERE id = 22;

-- id=23 APL: 분류 및 device_type 변경 (본문 PLACEHOLDER)
UPDATE device_info
SET category = '주사/부스터',
    device_type = 'injection',
    summary = '[PLACEHOLDER] APL(Amphiphilic Phospholipid Lipolysis) 지방분해주사. HPL과 다른 성분 조성의 별개 지방용해 주사.',
    mechanism = '[PLACEHOLDER] 양친매성 인지질 성분이 지방세포 파괴 및 대사 촉진.',
    target = '[PLACEHOLDER] 국소지방, 체형 개선',
    updated_at = datetime('now','+9 hours')
WHERE id = 23;

-- id=73 아쎄라: 분류 및 device_type 변경 (B-2 통합 이후 실행)
UPDATE device_info
SET category = '주사/부스터',
    device_type = 'injection',
    summary = '[PLACEHOLDER] 아쎄라 지방분해주사. 얼굴 및 바디 부위의 국소 지방 용해 주사 시술.',
    mechanism = '[PLACEHOLDER] 지방분해 성분 주입으로 지방세포 파괴 및 용해 촉진.',
    target = '[PLACEHOLDER] 얼굴 소안면, 팔자 지방, 바디 국소지방',
    updated_at = datetime('now','+9 hours')
WHERE id = 73;

-- ============================================================
-- D. equipment 미연결 매핑 일괄 업데이트 (573건, 정확 일치)
-- ============================================================
UPDATE equipment
SET device_info_id = (
    SELECT di.id FROM device_info di WHERE di.name = equipment.name LIMIT 1
),
updated_at = datetime('now','+9 hours')
WHERE device_info_id IS NULL
  AND name IN (SELECT name FROM device_info);

-- ============================================================
-- E. 클라리티 부천점 수정
-- ============================================================

-- eq.id=799 부천점 "클라리티" → "클라리티2" + device_info_id=34
UPDATE equipment
SET name = '클라리티2',
    device_info_id = 34,
    updated_at = datetime('now','+9 hours')
WHERE id = 799;

COMMIT;

-- ============================================================
-- 검증 쿼리 (실행 후 확인)
-- ============================================================
-- SELECT COUNT(*) FROM device_info;  -- 기대: 232 (234-2)
-- SELECT COUNT(*) FROM equipment WHERE device_info_id IS NULL;  -- 기대: 5 이하
-- SELECT COUNT(*) FROM equipment WHERE id=799 AND name='클라리티2' AND device_info_id=34;  -- 기대: 1
-- SELECT id, name, aliases FROM device_info WHERE id IN (27,22,73,86,35,46);
"""

# =========================================================
# 다수결 계산
# =========================================================

cur.execute("""
    SELECT di.id,
           e.category_id,
           COUNT(*) as cnt
    FROM device_info di
    JOIN equipment e ON e.device_info_id = di.id
    WHERE e.category_id IS NOT NULL
    GROUP BY di.id, e.category_id
    ORDER BY di.id, cnt DESC
""")
rows = cur.fetchall()

di_cats = defaultdict(list)
for di_id, cat_id, cnt in rows:
    di_cats[di_id].append((cnt, cat_id))

# Winner per device_info
majority = {}
for di_id, combos in di_cats.items():
    combos.sort(reverse=True)
    majority[di_id] = combos[0][1]  # highest count category_id

# All device_info ids
cur.execute("SELECT id FROM device_info")
all_di_ids = [r[0] for r in cur.fetchall()]
print(f"Total device_info: {len(all_di_ids)}")
print(f"With majority vote: {len(majority)}")
print(f"Without refs (will be NULL): {len(all_di_ids) - len(majority)}")

# Generate UPDATE statements
update_stmts = []
for di_id in sorted(all_di_ids):
    if di_id in majority:
        cat_id = majority[di_id]
        update_stmts.append(f"UPDATE device_info SET primary_category_id = {cat_id} WHERE id = {di_id};")

print(f"Generated {len(update_stmts)} UPDATE statements")

# =========================================================
# Build 002 SQL
# =========================================================

# Get branch_id for eq.id=80 광교
cur.execute("SELECT id, branch_id, name, category_id, quantity FROM equipment WHERE id=80")
eq80 = cur.fetchone()
print(f"\neq.id=80: {eq80}")

# Get branch_id for eq.id=614 목동
cur.execute("SELECT id, branch_id, name, category_id, quantity FROM equipment WHERE id=614")
eq614 = cur.fetchone()
print(f"eq.id=614: {eq614}")

# Get branch_id for eq.id=685 목포
cur.execute("SELECT id, branch_id, name, category_id, quantity FROM equipment WHERE id=685")
eq685 = cur.fetchone()
print(f"eq.id=685: {eq685}")

# Get branch_id for eq.id=690 목포
cur.execute("SELECT id, branch_id, name, category_id, quantity, note FROM equipment WHERE id=690")
eq690 = cur.fetchone()
print(f"eq.id=690: {eq690}")

# Check device_info id=72 aliases
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=72")
di72 = cur.fetchone()
print(f"\ndevice_info id=72 (실리프팅): {di72}")

# Check device_info id=31 aliases
cur.execute("SELECT id, name, aliases FROM device_info WHERE id=31")
di31 = cur.fetchone()
print(f"device_info id=31 (올리지오X): {di31}")

# Get max equipment id
cur.execute("SELECT MAX(id) FROM equipment")
max_eq_id = cur.fetchone()[0]
print(f"\nMax equipment id: {max_eq_id}")

# Get max device_info id
cur.execute("SELECT MAX(id) FROM device_info")
max_di_id = cur.fetchone()[0]
print(f"Max device_info id: {max_di_id}")

conn.close()

# Parse di72 aliases
di72_aliases_raw = di72[2] if di72 else '[]'
try:
    di72_aliases = json.loads(di72_aliases_raw)
except:
    di72_aliases = []

# Add new aliases for 실리프팅
new_di72_aliases = di72_aliases.copy()
for a in ["실루엣픽스실", "옥토실", "엠보스몰드실", "모노실"]:
    if a not in new_di72_aliases:
        new_di72_aliases.append(a)
di72_aliases_new_json = json.dumps(new_di72_aliases, ensure_ascii=False)
print(f"\nNew di72 aliases: {di72_aliases_new_json}")

# Parse di31 aliases for 올리지오X
di31_aliases_raw = di31[2] if di31 else '[]'
try:
    di31_aliases = json.loads(di31_aliases_raw)
except:
    di31_aliases = []

# Add Korean alias "올리지오 키스"
if "올리지오 키스" not in di31_aliases:
    di31_aliases.append("올리지오 키스")
di31_aliases_new_json = json.dumps(di31_aliases, ensure_ascii=False)
print(f"New di31 aliases: {di31_aliases_new_json}")

# eq.id=80 values
branch_id_80 = eq80[1]
category_id_80 = eq80[3]

# eq.id=614 values
branch_id_614 = eq614[1]
category_id_614 = eq614[3]

# eq.id=685 values
branch_id_685 = eq685[1]
category_id_685 = eq685[3]

# eq.id=690 values
branch_id_690 = eq690[1]
category_id_690 = eq690[3]
original_name_690 = eq690[2]

# New IDs for eq splits
new_eq_id_start = max_eq_id + 1
new_di_lpl_id = max_di_id + 1

# Build update statements string
update_block = "\n".join(update_stmts)

sql_002 = f"""\
-- ============================================================
-- 002_treatment_norm_stage_2-6_and_manual4.sql
-- 시술 정규화 2-6단계 + 수동 4건 처리
-- 생성일: 2026-05-19
-- 영향 row 수:
--   - device_info: primary_category_id 컬럼 추가 (232행 채움)
--   - equipment: 광교 eq.id=80 분리 (1→2), 목동 eq.id=614 정정,
--                목포 eq.id=685 분리 (1→6), 목포 eq.id=690 정정
--   - device_info: LPL 신규 등록, 실리프팅/올리지오X aliases 추가
-- 적용 전 백업 권장
-- ============================================================

BEGIN TRANSACTION;

-- ============================================================
-- 2-6-1. device_info에 primary_category_id 컬럼 추가
-- ============================================================
ALTER TABLE device_info ADD COLUMN primary_category_id INTEGER REFERENCES categories(id);

-- ============================================================
-- 2-6-2. primary_category_id 다수결 채움 (equipment.category_id 기준)
-- 참조 equipment가 없는 device_info row는 NULL 유지
-- ============================================================
{update_block}

-- ============================================================
-- 수동 처리 1. 광교 eq.id=80 "비타/크라" → "비타민" + "크라이오" 2건 분리
-- ============================================================

-- 새 row 1: 비타민 (device_info_id=92)
INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_80}, {category_id_80}, '비타민', 92, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

-- 새 row 2: 크라이오 (device_info_id=18)
INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_80}, {category_id_80}, '크라이오', 18, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

-- 원본 eq.id=80 삭제
DELETE FROM equipment WHERE id = 80;

-- ============================================================
-- 수동 처리 2. 목동 eq.id=614 "올리지오 키스 로 변경" 정정
-- ============================================================

-- device_info id=31 aliases에 "올리지오 키스" 추가
UPDATE device_info
SET aliases = '{di31_aliases_new_json}',
    updated_at = datetime('now','+9 hours')
WHERE id = 31;

-- equipment 업데이트: name 정정 + device_info_id 연결
UPDATE equipment
SET name = '올리지오 키스',
    device_info_id = 31,
    updated_at = datetime('now','+9 hours')
WHERE id = 614;

-- ============================================================
-- 수동 처리 3. 목포 eq.id=685 실리프팅 6종 분리
-- ============================================================

-- device_info id=72 (실리프팅) aliases 확장: 4종 추가
UPDATE device_info
SET aliases = '{di72_aliases_new_json}',
    updated_at = datetime('now','+9 hours')
WHERE id = 72;

-- 6개 row 삽입
INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_685}, {category_id_685}, '실루엣소프트', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_685}, {category_id_685}, '민트실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_685}, {category_id_685}, '실루엣픽스실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_685}, {category_id_685}, '옥토실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_685}, {category_id_685}, '엠보스몰드실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES ({branch_id_685}, {category_id_685}, '모노실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

-- 원본 eq.id=685 삭제
DELETE FROM equipment WHERE id = 685;

-- ============================================================
-- 수동 처리 4. 목포 eq.id=690 LPL 등록 + 정정
-- ============================================================

-- device_info 신규 등록: LPL
INSERT INTO device_info (name, category, summary, target, mechanism, aliases, device_type, is_verified, created_at, updated_at)
VALUES (
    'LPL',
    '관리기기(광선)',
    'LLLT 저출력 레이저 (Low Level Laser Therapy)',
    '피부 재생, 붓기 완화',
    '저출력 광선 자극으로 세포 활성화 및 항염증 효과',
    '["LLLT", "저출력레이저", "저출력 레이저"]',
    'care',
    0,
    datetime('now','+9 hours'),
    datetime('now','+9 hours')
);

-- equipment 업데이트: name 정리 + device_info_id 연결 + 원본 설명 note 보존
UPDATE equipment
SET name = 'LPL',
    device_info_id = (SELECT id FROM device_info WHERE name = 'LPL' ORDER BY id DESC LIMIT 1),
    note = '{original_name_690}',
    updated_at = datetime('now','+9 hours')
WHERE id = 690;

COMMIT;

-- ============================================================
-- 검증 쿼리 (실행 후 확인)
-- ============================================================
-- SELECT COUNT(*) FROM device_info;  -- 기대: 233 (232+LPL)
-- SELECT COUNT(*) as null_count FROM device_info WHERE primary_category_id IS NULL;  -- 최소화
-- SELECT COUNT(*) as filled FROM device_info WHERE primary_category_id IS NOT NULL;
-- SELECT COUNT(*) FROM equipment WHERE id IN (80, 685);  -- 기대: 0 (삭제됨)
-- SELECT COUNT(*) FROM equipment WHERE branch_id={branch_id_80} AND name IN ('비타민','크라이오');  -- 기대: 2
-- SELECT id, name, device_info_id FROM equipment WHERE id = 614;  -- 기대: 614, '올리지오 키스', 31
-- SELECT id, name, device_info_id FROM equipment WHERE id = 690;  -- 기대: 690, 'LPL', (new id)
-- SELECT id, name, aliases FROM device_info WHERE name = 'LPL';
-- SELECT id, name, aliases FROM device_info WHERE id = 72;  -- 실리프팅 aliases 확장 확인
-- SELECT id, name, aliases FROM device_info WHERE id = 31;  -- 올리지오X aliases 확장 확인
"""

# Write files
os.makedirs("C:/LocalGD/7_CODE/uni-portal/docs/_temp/treatment_norm/migrations", exist_ok=True)

with open("C:/LocalGD/7_CODE/uni-portal/docs/_temp/treatment_norm/migrations/001_treatment_norm_stage_2-1to4.sql", "w", encoding="utf-8") as f:
    f.write(sql_001)

with open("C:/LocalGD/7_CODE/uni-portal/docs/_temp/treatment_norm/migrations/002_treatment_norm_stage_2-6_and_manual4.sql", "w", encoding="utf-8") as f:
    f.write(sql_002)

print("\nSQL files written successfully.")
print("001 lines:", sql_001.count('\n'))
print("002 lines:", sql_002.count('\n'))
