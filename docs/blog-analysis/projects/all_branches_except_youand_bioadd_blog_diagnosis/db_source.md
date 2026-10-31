# DB 기준

## 기준 DB

- 로컬 DB: `data/equipment.db`
- 기준 테이블: `blog_posts`
- 생성일: 2026-06-30

## 분석 대상 기간

- 2026-01-01 ~ 2026-06-30
- 기준 컬럼: `published_at`

## DB 갱신 시 절차

1. 운영 서비스에서 최신 블로그 DB 스냅샷을 다운로드한다.
2. 다운로드한 DB를 `docs/blog-analysis/db-snapshots/` 하위에 보관한다.
3. 로컬 분석 기준 DB인 `data/equipment.db`에 반영한다.
4. 본 프로젝트의 CSV를 재생성한다.
5. `target_audit.md`의 집계가 변경되었는지 확인한다.

## 주의

- 이 프로젝트는 유앤아이 계열과 bioadd lab 7개 지점을 제외한다.
- DB 갱신 후 제외 조건이 새 지점명 패턴을 충분히 잡는지 다시 확인해야 한다.

