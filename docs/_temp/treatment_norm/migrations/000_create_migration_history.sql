-- 마이그레이션 이력 테이블 생성
-- 이 파일은 DB 마이그레이션 기능 자체를 위한 첫 마이그레이션입니다.
-- 적용 후 이후 모든 마이그레이션이 이 테이블에 기록됩니다.

CREATE TABLE IF NOT EXISTS migration_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filename     TEXT NOT NULL,
    sql_hash     TEXT,           -- SHA256, 같은 파일 재적용 방지
    applied_at   TIMESTAMP NOT NULL,
    applied_by   TEXT,           -- user_id
    backup_path  TEXT,           -- 적용 전 자동 백업 경로
    success      INTEGER NOT NULL,  -- 0/1
    error_log    TEXT,
    summary      TEXT            -- 적용 결과 요약 (몇 row 영향 등)
);
