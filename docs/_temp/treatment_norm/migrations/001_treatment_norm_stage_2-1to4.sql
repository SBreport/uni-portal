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
