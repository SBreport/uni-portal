-- ============================================================
-- 005. 필 시리즈 device_info 마스터 신규 등록
-- ============================================================
-- 목적: 라라필/핑크필/블랙필/호박필이 device_info에 없어 매칭 시 substring으로 '밀크필'(id=90)에 잘못 잡힘
-- 해결: 각 필 종류를 별도 마스터로 등록 → force remap으로 자동 정확 매핑
-- 영향: device_info 4 row INSERT, primary_category_id=7(기타)
-- 적용 후: Equipment 정리 도구 > '강제 전체 재매핑' 실행 권장
-- ============================================================

BEGIN TRANSACTION;

-- 라라필
INSERT INTO device_info (name, category, summary, target, mechanism, aliases, device_type, is_verified, primary_category_id, created_at, updated_at)
VALUES (
    '라라필',
    '필링',
    '[PLACEHOLDER] 라라필 — 수분 보충 화학 필링 (본문 작성 필요)',
    '[PLACEHOLDER] 피부결, 수분, 톤 개선',
    '[PLACEHOLDER] 화학 박피로 각질 제거 + 보습 성분 흡수 촉진',
    '[]',
    'care',
    0,
    7,
    datetime('now','+9 hours'),
    datetime('now','+9 hours')
);

-- 핑크필
INSERT INTO device_info (name, category, summary, target, mechanism, aliases, device_type, is_verified, primary_category_id, created_at, updated_at)
VALUES (
    '핑크필',
    '필링',
    '[PLACEHOLDER] 핑크필 — 재생/탄력 화학 필링 (본문 작성 필요)',
    '[PLACEHOLDER] 피부 재생, 탄력, 톤 개선',
    '[PLACEHOLDER] 화학 박피 + 재생 성분 흡수',
    '[]',
    'care',
    0,
    7,
    datetime('now','+9 hours'),
    datetime('now','+9 hours')
);

-- 블랙필
INSERT INTO device_info (name, category, summary, target, mechanism, aliases, device_type, is_verified, primary_category_id, created_at, updated_at)
VALUES (
    '블랙필',
    '필링',
    '[PLACEHOLDER] 블랙필 — 각질 제거 화학 필링 (본문 작성 필요)',
    '[PLACEHOLDER] 모공, 각질, 피지',
    '[PLACEHOLDER] 화학 박피로 각질·피지 제거',
    '[]',
    'care',
    0,
    7,
    datetime('now','+9 hours'),
    datetime('now','+9 hours')
);

-- 호박필
INSERT INTO device_info (name, category, summary, target, mechanism, aliases, device_type, is_verified, primary_category_id, created_at, updated_at)
VALUES (
    '호박필',
    '필링',
    '[PLACEHOLDER] 호박필 — 호박 추출물 화학 필링 (본문 작성 필요)',
    '[PLACEHOLDER] 수분, 탄력, 톤',
    '[PLACEHOLDER] 호박 추출물 기반 화학 박피',
    '[]',
    'care',
    0,
    7,
    datetime('now','+9 hours'),
    datetime('now','+9 hours')
);

COMMIT;

-- 검증 SELECT (주석)
-- SELECT id, name, category, primary_category_id FROM device_info WHERE name IN ('라라필','핑크필','블랙필','호박필');
-- 기대: 4 row, primary_category_id=7
