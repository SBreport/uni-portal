-- ============================================================
-- 003_광교_비타민_크라이오_중복정리.sql
-- 광교점 비타민/크라이오 manual INSERT 중복 정리
-- 생성일: 2026-05-26
-- 영향 row 수: equipment 2건 DELETE (manual source)
-- ============================================================
--
-- 배경:
--   002 마이그레이션에서 광교 eq.id=80 ("비타/크라")를 DELETE한 후
--   "비타민" (device_info_id=92) + "크라이오" (device_info_id=18) 2 row를
--   source='manual'로 INSERT 함.
--
--   그런데 사용자가 시트 정리를 마이그레이션 적용 전에 완료한 상태였기 때문에
--   시트의 "비타민" + "크라이오"가 sync 과정에서 source='sheets'로 별도 INSERT됨.
--
--   결과: 비타민 2 row (manual + sheets), 크라이오 2 row (manual + sheets) 중복.
--
-- 결정:
--   시트가 권위 룰에 따라 sheets source를 유지하고 manual row 삭제.
--
-- 로컬 상태 (참고):
--   로컬 DB에는 manual row(id=2385, 2386)만 존재하고 sheets row 미생성.
--   운영 DB에는 manual + sheets 각각 2쌍 = 4 row 중복 상태.
--   본 SQL은 source='manual' 조건을 사용하므로 양쪽 모두 안전하게 적용 가능.
-- ============================================================

BEGIN TRANSACTION;

-- DELETE 대상: 광교점 + source='manual' + 비타민/크라이오
-- 운영: manual row 2건 삭제 → sheets row 각 1건씩 유지
-- 로컬: manual row 2건 삭제 → 해당 name 자체가 사라짐 (sheets row 없음)
DELETE FROM equipment
WHERE source = 'manual'
  AND branch_id = (SELECT id FROM branches WHERE name = '광교점')
  AND name IN ('비타민', '크라이오');

COMMIT;

-- ============================================================
-- 검증 SELECT (실행 후 결과 확인)
-- ============================================================
-- SELECT id, name, source, device_info_id
-- FROM equipment
-- WHERE branch_id = (SELECT id FROM branches WHERE name = '광교점')
--   AND name IN ('비타민', '크라이오');
-- 운영 기대: 2건 (source='sheets' 각 1건씩)
-- 로컬 기대: 0건 (sheets row 없으므로)
