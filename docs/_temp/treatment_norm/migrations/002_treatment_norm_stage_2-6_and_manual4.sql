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
UPDATE device_info SET primary_category_id = 1 WHERE id = 2;
UPDATE device_info SET primary_category_id = 1 WHERE id = 3;
UPDATE device_info SET primary_category_id = 1 WHERE id = 4;
UPDATE device_info SET primary_category_id = 1 WHERE id = 5;
UPDATE device_info SET primary_category_id = 4 WHERE id = 6;
UPDATE device_info SET primary_category_id = 4 WHERE id = 7;
UPDATE device_info SET primary_category_id = 2 WHERE id = 8;
UPDATE device_info SET primary_category_id = 2 WHERE id = 9;
UPDATE device_info SET primary_category_id = 2 WHERE id = 10;
UPDATE device_info SET primary_category_id = 5 WHERE id = 11;
UPDATE device_info SET primary_category_id = 5 WHERE id = 13;
UPDATE device_info SET primary_category_id = 5 WHERE id = 14;
UPDATE device_info SET primary_category_id = 5 WHERE id = 15;
UPDATE device_info SET primary_category_id = 7 WHERE id = 17;
UPDATE device_info SET primary_category_id = 7 WHERE id = 18;
UPDATE device_info SET primary_category_id = 7 WHERE id = 19;
UPDATE device_info SET primary_category_id = 7 WHERE id = 20;
UPDATE device_info SET primary_category_id = 7 WHERE id = 21;
UPDATE device_info SET primary_category_id = 6 WHERE id = 22;
UPDATE device_info SET primary_category_id = 6 WHERE id = 23;
UPDATE device_info SET primary_category_id = 6 WHERE id = 25;
UPDATE device_info SET primary_category_id = 6 WHERE id = 26;
UPDATE device_info SET primary_category_id = 1 WHERE id = 27;
UPDATE device_info SET primary_category_id = 1 WHERE id = 28;
UPDATE device_info SET primary_category_id = 1 WHERE id = 29;
UPDATE device_info SET primary_category_id = 1 WHERE id = 30;
UPDATE device_info SET primary_category_id = 1 WHERE id = 31;
UPDATE device_info SET primary_category_id = 1 WHERE id = 32;
UPDATE device_info SET primary_category_id = 1 WHERE id = 33;
UPDATE device_info SET primary_category_id = 2 WHERE id = 34;
UPDATE device_info SET primary_category_id = 2 WHERE id = 35;
UPDATE device_info SET primary_category_id = 3 WHERE id = 36;
UPDATE device_info SET primary_category_id = 3 WHERE id = 37;
UPDATE device_info SET primary_category_id = 3 WHERE id = 38;
UPDATE device_info SET primary_category_id = 3 WHERE id = 39;
UPDATE device_info SET primary_category_id = 3 WHERE id = 40;
UPDATE device_info SET primary_category_id = 3 WHERE id = 41;
UPDATE device_info SET primary_category_id = 3 WHERE id = 42;
UPDATE device_info SET primary_category_id = 3 WHERE id = 43;
UPDATE device_info SET primary_category_id = 3 WHERE id = 44;
UPDATE device_info SET primary_category_id = 2 WHERE id = 45;
UPDATE device_info SET primary_category_id = 2 WHERE id = 46;
UPDATE device_info SET primary_category_id = 2 WHERE id = 47;
UPDATE device_info SET primary_category_id = 2 WHERE id = 48;
UPDATE device_info SET primary_category_id = 2 WHERE id = 49;
UPDATE device_info SET primary_category_id = 8 WHERE id = 50;
UPDATE device_info SET primary_category_id = 2 WHERE id = 51;
UPDATE device_info SET primary_category_id = 5 WHERE id = 52;
UPDATE device_info SET primary_category_id = 5 WHERE id = 53;
UPDATE device_info SET primary_category_id = 1 WHERE id = 54;
UPDATE device_info SET primary_category_id = 4 WHERE id = 55;
UPDATE device_info SET primary_category_id = 3 WHERE id = 56;
UPDATE device_info SET primary_category_id = 3 WHERE id = 57;
UPDATE device_info SET primary_category_id = 3 WHERE id = 58;
UPDATE device_info SET primary_category_id = 1 WHERE id = 59;
UPDATE device_info SET primary_category_id = 1 WHERE id = 60;
UPDATE device_info SET primary_category_id = 3 WHERE id = 61;
UPDATE device_info SET primary_category_id = 2 WHERE id = 62;
UPDATE device_info SET primary_category_id = 2 WHERE id = 63;
UPDATE device_info SET primary_category_id = 8 WHERE id = 64;
UPDATE device_info SET primary_category_id = 2 WHERE id = 65;
UPDATE device_info SET primary_category_id = 5 WHERE id = 66;
UPDATE device_info SET primary_category_id = 3 WHERE id = 67;
UPDATE device_info SET primary_category_id = 3 WHERE id = 68;
UPDATE device_info SET primary_category_id = 7 WHERE id = 69;
UPDATE device_info SET primary_category_id = 3 WHERE id = 70;
UPDATE device_info SET primary_category_id = 3 WHERE id = 71;
UPDATE device_info SET primary_category_id = 1 WHERE id = 72;
UPDATE device_info SET primary_category_id = 6 WHERE id = 73;
UPDATE device_info SET primary_category_id = 2 WHERE id = 75;
UPDATE device_info SET primary_category_id = 2 WHERE id = 76;
UPDATE device_info SET primary_category_id = 5 WHERE id = 77;
UPDATE device_info SET primary_category_id = 1 WHERE id = 78;
UPDATE device_info SET primary_category_id = 6 WHERE id = 79;
UPDATE device_info SET primary_category_id = 3 WHERE id = 80;
UPDATE device_info SET primary_category_id = 3 WHERE id = 81;
UPDATE device_info SET primary_category_id = 3 WHERE id = 82;
UPDATE device_info SET primary_category_id = 5 WHERE id = 83;
UPDATE device_info SET primary_category_id = 2 WHERE id = 84;
UPDATE device_info SET primary_category_id = 2 WHERE id = 85;
UPDATE device_info SET primary_category_id = 7 WHERE id = 86;
UPDATE device_info SET primary_category_id = 1 WHERE id = 87;
UPDATE device_info SET primary_category_id = 2 WHERE id = 88;
UPDATE device_info SET primary_category_id = 3 WHERE id = 89;
UPDATE device_info SET primary_category_id = 7 WHERE id = 90;
UPDATE device_info SET primary_category_id = 7 WHERE id = 91;
UPDATE device_info SET primary_category_id = 7 WHERE id = 92;
UPDATE device_info SET primary_category_id = 7 WHERE id = 93;
UPDATE device_info SET primary_category_id = 7 WHERE id = 94;
UPDATE device_info SET primary_category_id = 1 WHERE id = 95;
UPDATE device_info SET primary_category_id = 1 WHERE id = 96;
UPDATE device_info SET primary_category_id = 3 WHERE id = 97;
UPDATE device_info SET primary_category_id = 6 WHERE id = 98;
UPDATE device_info SET primary_category_id = 6 WHERE id = 99;
UPDATE device_info SET primary_category_id = 2 WHERE id = 100;
UPDATE device_info SET primary_category_id = 7 WHERE id = 101;
UPDATE device_info SET primary_category_id = 3 WHERE id = 102;
UPDATE device_info SET primary_category_id = 3 WHERE id = 103;
UPDATE device_info SET primary_category_id = 5 WHERE id = 104;
UPDATE device_info SET primary_category_id = 1 WHERE id = 105;
UPDATE device_info SET primary_category_id = 1 WHERE id = 106;
UPDATE device_info SET primary_category_id = 5 WHERE id = 107;
UPDATE device_info SET primary_category_id = 2 WHERE id = 108;
UPDATE device_info SET primary_category_id = 7 WHERE id = 110;
UPDATE device_info SET primary_category_id = 2 WHERE id = 111;
UPDATE device_info SET primary_category_id = 5 WHERE id = 112;
UPDATE device_info SET primary_category_id = 1 WHERE id = 113;
UPDATE device_info SET primary_category_id = 5 WHERE id = 114;
UPDATE device_info SET primary_category_id = 1 WHERE id = 115;
UPDATE device_info SET primary_category_id = 2 WHERE id = 116;
UPDATE device_info SET primary_category_id = 8 WHERE id = 117;
UPDATE device_info SET primary_category_id = 2 WHERE id = 118;
UPDATE device_info SET primary_category_id = 2 WHERE id = 119;
UPDATE device_info SET primary_category_id = 1 WHERE id = 120;
UPDATE device_info SET primary_category_id = 3 WHERE id = 121;
UPDATE device_info SET primary_category_id = 6 WHERE id = 122;
UPDATE device_info SET primary_category_id = 1 WHERE id = 123;
UPDATE device_info SET primary_category_id = 7 WHERE id = 124;
UPDATE device_info SET primary_category_id = 5 WHERE id = 125;
UPDATE device_info SET primary_category_id = 3 WHERE id = 126;
UPDATE device_info SET primary_category_id = 3 WHERE id = 127;
UPDATE device_info SET primary_category_id = 5 WHERE id = 128;
UPDATE device_info SET primary_category_id = 2 WHERE id = 129;
UPDATE device_info SET primary_category_id = 7 WHERE id = 130;
UPDATE device_info SET primary_category_id = 1 WHERE id = 131;
UPDATE device_info SET primary_category_id = 1 WHERE id = 132;
UPDATE device_info SET primary_category_id = 1 WHERE id = 133;
UPDATE device_info SET primary_category_id = 6 WHERE id = 134;
UPDATE device_info SET primary_category_id = 7 WHERE id = 135;
UPDATE device_info SET primary_category_id = 1 WHERE id = 136;
UPDATE device_info SET primary_category_id = 1 WHERE id = 137;
UPDATE device_info SET primary_category_id = 1 WHERE id = 138;
UPDATE device_info SET primary_category_id = 1 WHERE id = 139;
UPDATE device_info SET primary_category_id = 1 WHERE id = 140;
UPDATE device_info SET primary_category_id = 1 WHERE id = 141;
UPDATE device_info SET primary_category_id = 1 WHERE id = 142;
UPDATE device_info SET primary_category_id = 1 WHERE id = 143;
UPDATE device_info SET primary_category_id = 6 WHERE id = 144;
UPDATE device_info SET primary_category_id = 6 WHERE id = 145;
UPDATE device_info SET primary_category_id = 6 WHERE id = 146;
UPDATE device_info SET primary_category_id = 6 WHERE id = 147;
UPDATE device_info SET primary_category_id = 6 WHERE id = 148;
UPDATE device_info SET primary_category_id = 6 WHERE id = 149;
UPDATE device_info SET primary_category_id = 6 WHERE id = 150;
UPDATE device_info SET primary_category_id = 6 WHERE id = 151;
UPDATE device_info SET primary_category_id = 6 WHERE id = 152;
UPDATE device_info SET primary_category_id = 6 WHERE id = 153;
UPDATE device_info SET primary_category_id = 6 WHERE id = 154;
UPDATE device_info SET primary_category_id = 6 WHERE id = 155;
UPDATE device_info SET primary_category_id = 6 WHERE id = 156;
UPDATE device_info SET primary_category_id = 2 WHERE id = 157;
UPDATE device_info SET primary_category_id = 2 WHERE id = 158;
UPDATE device_info SET primary_category_id = 5 WHERE id = 159;
UPDATE device_info SET primary_category_id = 2 WHERE id = 160;
UPDATE device_info SET primary_category_id = 2 WHERE id = 161;
UPDATE device_info SET primary_category_id = 2 WHERE id = 162;
UPDATE device_info SET primary_category_id = 2 WHERE id = 163;
UPDATE device_info SET primary_category_id = 5 WHERE id = 164;
UPDATE device_info SET primary_category_id = 2 WHERE id = 165;
UPDATE device_info SET primary_category_id = 2 WHERE id = 166;
UPDATE device_info SET primary_category_id = 2 WHERE id = 167;
UPDATE device_info SET primary_category_id = 4 WHERE id = 168;
UPDATE device_info SET primary_category_id = 5 WHERE id = 169;
UPDATE device_info SET primary_category_id = 4 WHERE id = 170;
UPDATE device_info SET primary_category_id = 4 WHERE id = 171;
UPDATE device_info SET primary_category_id = 4 WHERE id = 172;
UPDATE device_info SET primary_category_id = 4 WHERE id = 173;
UPDATE device_info SET primary_category_id = 4 WHERE id = 174;
UPDATE device_info SET primary_category_id = 5 WHERE id = 175;
UPDATE device_info SET primary_category_id = 7 WHERE id = 176;
UPDATE device_info SET primary_category_id = 5 WHERE id = 177;
UPDATE device_info SET primary_category_id = 5 WHERE id = 178;
UPDATE device_info SET primary_category_id = 5 WHERE id = 179;
UPDATE device_info SET primary_category_id = 5 WHERE id = 180;
UPDATE device_info SET primary_category_id = 5 WHERE id = 181;
UPDATE device_info SET primary_category_id = 5 WHERE id = 182;
UPDATE device_info SET primary_category_id = 5 WHERE id = 183;
UPDATE device_info SET primary_category_id = 5 WHERE id = 184;
UPDATE device_info SET primary_category_id = 3 WHERE id = 185;
UPDATE device_info SET primary_category_id = 3 WHERE id = 186;
UPDATE device_info SET primary_category_id = 3 WHERE id = 187;
UPDATE device_info SET primary_category_id = 3 WHERE id = 188;
UPDATE device_info SET primary_category_id = 3 WHERE id = 189;
UPDATE device_info SET primary_category_id = 3 WHERE id = 190;
UPDATE device_info SET primary_category_id = 3 WHERE id = 191;
UPDATE device_info SET primary_category_id = 3 WHERE id = 192;
UPDATE device_info SET primary_category_id = 3 WHERE id = 193;
UPDATE device_info SET primary_category_id = 3 WHERE id = 194;
UPDATE device_info SET primary_category_id = 3 WHERE id = 195;
UPDATE device_info SET primary_category_id = 3 WHERE id = 196;
UPDATE device_info SET primary_category_id = 3 WHERE id = 197;
UPDATE device_info SET primary_category_id = 3 WHERE id = 198;
UPDATE device_info SET primary_category_id = 7 WHERE id = 199;
UPDATE device_info SET primary_category_id = 3 WHERE id = 200;
UPDATE device_info SET primary_category_id = 3 WHERE id = 201;
UPDATE device_info SET primary_category_id = 3 WHERE id = 202;
UPDATE device_info SET primary_category_id = 3 WHERE id = 203;
UPDATE device_info SET primary_category_id = 3 WHERE id = 204;
UPDATE device_info SET primary_category_id = 3 WHERE id = 205;
UPDATE device_info SET primary_category_id = 3 WHERE id = 206;
UPDATE device_info SET primary_category_id = 3 WHERE id = 207;
UPDATE device_info SET primary_category_id = 3 WHERE id = 208;
UPDATE device_info SET primary_category_id = 3 WHERE id = 209;
UPDATE device_info SET primary_category_id = 7 WHERE id = 210;
UPDATE device_info SET primary_category_id = 7 WHERE id = 211;
UPDATE device_info SET primary_category_id = 7 WHERE id = 212;
UPDATE device_info SET primary_category_id = 7 WHERE id = 213;
UPDATE device_info SET primary_category_id = 7 WHERE id = 214;
UPDATE device_info SET primary_category_id = 6 WHERE id = 215;
UPDATE device_info SET primary_category_id = 7 WHERE id = 216;
UPDATE device_info SET primary_category_id = 7 WHERE id = 217;
UPDATE device_info SET primary_category_id = 7 WHERE id = 218;
UPDATE device_info SET primary_category_id = 7 WHERE id = 219;
UPDATE device_info SET primary_category_id = 7 WHERE id = 220;
UPDATE device_info SET primary_category_id = 7 WHERE id = 221;
UPDATE device_info SET primary_category_id = 7 WHERE id = 222;
UPDATE device_info SET primary_category_id = 7 WHERE id = 223;
UPDATE device_info SET primary_category_id = 7 WHERE id = 224;
UPDATE device_info SET primary_category_id = 7 WHERE id = 225;
UPDATE device_info SET primary_category_id = 7 WHERE id = 226;
UPDATE device_info SET primary_category_id = 7 WHERE id = 227;
UPDATE device_info SET primary_category_id = 7 WHERE id = 228;
UPDATE device_info SET primary_category_id = 7 WHERE id = 229;
UPDATE device_info SET primary_category_id = 7 WHERE id = 230;
UPDATE device_info SET primary_category_id = 4 WHERE id = 231;
UPDATE device_info SET primary_category_id = 7 WHERE id = 232;
UPDATE device_info SET primary_category_id = 5 WHERE id = 233;
UPDATE device_info SET primary_category_id = 1 WHERE id = 234;

-- ============================================================
-- 수동 처리 1. 광교 eq.id=80 "비타/크라" → "비타민" + "크라이오" 2건 분리
-- ============================================================

-- 새 row 1: 비타민 (device_info_id=92)
INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (2, 7, '비타민', 92, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

-- 새 row 2: 크라이오 (device_info_id=18)
INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (2, 7, '크라이오', 18, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

-- 원본 eq.id=80 삭제
DELETE FROM equipment WHERE id = 80;

-- ============================================================
-- 수동 처리 2. 목동 eq.id=614 "올리지오 키스 로 변경" 정정
-- ============================================================

-- device_info id=31 aliases에 "올리지오 키스" 추가
UPDATE device_info
SET aliases = '["올리지오 X", "올리지오x", "올리지오", "올리지오 KISS", "올리지오 키스"]',
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
SET aliases = '["실 리프팅", "민트실", "민트실리프팅", "실루엣소프트", "실루엣소프트 실리프팅", "실루엣픽스실", "옥토실", "엠보스몰드실", "모노실"]',
    updated_at = datetime('now','+9 hours')
WHERE id = 72;

-- 6개 row 삽입
INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (17, 1, '실루엣소프트', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (17, 1, '민트실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (17, 1, '실루엣픽스실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (17, 1, '옥토실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (17, 1, '엠보스몰드실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

INSERT INTO equipment (branch_id, category_id, name, device_info_id, quantity, source, created_at, updated_at)
VALUES (17, 1, '모노실', 72, 1, 'manual', datetime('now','+9 hours'), datetime('now','+9 hours'));

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
    note = 'LPL (LLLT 저출력레이저 ) PDT할때 또는 피부재생붓기완화목적으로 사용',
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
-- SELECT COUNT(*) FROM equipment WHERE branch_id=2 AND name IN ('비타민','크라이오');  -- 기대: 2
-- SELECT id, name, device_info_id FROM equipment WHERE id = 614;  -- 기대: 614, '올리지오 키스', 31
-- SELECT id, name, device_info_id FROM equipment WHERE id = 690;  -- 기대: 690, 'LPL', (new id)
-- SELECT id, name, aliases FROM device_info WHERE name = 'LPL';
-- SELECT id, name, aliases FROM device_info WHERE id = 72;  -- 실리프팅 aliases 확장 확인
-- SELECT id, name, aliases FROM device_info WHERE id = 31;  -- 올리지오X aliases 확장 확인

-- LPL(id=235) primary_category_id 보정 (eq.id=690 category_id=7 기타)
UPDATE device_info SET primary_category_id = 7, updated_at = datetime('now','+9 hours') WHERE id = 235;
