# 블로그 분석 DB 관리 기준

블로그 분석은 어떤 DB 시점으로 분석했는지가 중요하다. 분석 결과를 다시 해석하거나 다음 프로젝트에서 이어갈 수 있도록 원천 DB와 반영 DB를 반드시 기록한다.

## 1. DB 역할

블로그 분석에서 DB는 두 종류로 구분한다.

- 원본 스냅샷 DB: 운영 웹에서 내려받은 블로그 분석용 DB
- 로컬 반영 DB: 프로젝트 로컬 서비스 DB인 `data/equipment.db`

원본 스냅샷 DB는 운영 시점의 블로그 관련 테이블만 담는다. 로컬 반영 DB는 전체 서비스 DB이므로 파일 해시와 용량이 다를 수 있다.

## 2. 현재 표준 위치

- 로컬 반영 DB: `data/equipment.db`
- 로컬 DB 백업: `_백업/`
- 원본 스냅샷 DB 보관: `docs/blog-analysis/db-snapshots/{프로젝트명}/`
- 프로젝트별 DB 기준 문서: 각 프로젝트 폴더의 `db_source.md`

원본 스냅샷 DB는 다운로드 폴더에만 두지 않는다. 장기 재현이 필요한 분석은 `db-snapshots/` 하위에 보관본을 두고, 파일명, 위치, 생성 시각, 해시, 주요 row 수를 문서에 남긴다.

## 3. 새 분석 전 체크리스트

새 블로그 분석 프로젝트를 시작할 때는 다음을 확인한다.

1. 운영 웹의 블로그 데이터가 최신인지 확인한다.
2. 관리자 화면에서 블로그 분석 DB 스냅샷을 다운로드한다.
3. 스냅샷을 `docs/blog-analysis/db-snapshots/{프로젝트명}/`에 복사한다.
4. 현재 `data/equipment.db`를 `_백업/`에 백업한다.
5. 스냅샷의 `blog_posts` 최신 발행일과 row 수를 확인한다.
6. 로컬 DB에 스냅샷을 반영한다.
7. 반영 후 `data/equipment.db`의 `blog_posts` row 수와 최신 발행일을 확인한다.
8. 프로젝트 폴더에 `db_source.md`를 작성한다.

## 4. 운영 웹에서 스냅샷 받기

운영 웹에서 다음 메뉴를 사용한다.

- 관리자 모드
- 데이터 로그
- 블로그 데이터 관리
- `블로그 분석 DB 다운로드`

현재 구현된 백엔드 엔드포인트는 다음과 같다.

```text
GET /blog/download-snapshot.db
```

스냅샷에 포함되는 주요 테이블은 다음과 같다.

- `blog_posts`
- `blog_accounts`
- `blog_sync_log`
- `notion_sync_log`
- `paper_blog_links`
- `evt_branches`
- `snapshot_meta`

## 5. 로컬 반영 전 백업

스냅샷을 로컬 DB에 반영하기 전에는 반드시 백업을 만든다.

예시:

```bash
mkdir -p _백업
cp data/equipment.db _백업/equipment_before_blog_snapshot_YYYYMMDD_HHMMSS.db
```

## 6. 검증 명령

스냅샷 또는 로컬 DB의 블로그 데이터 상태는 다음 명령으로 확인한다.

```bash
sqlite3 data/equipment.db "
SELECT 'blog_posts', COUNT(*) FROM blog_posts;
SELECT 'min_published', MIN(published_at), 'max_published', MAX(published_at)
FROM blog_posts
WHERE published_at != '';
SELECT 'latest_updated', MAX(updated_at) FROM blog_posts;
"
```

파일 식별용 해시는 다음처럼 기록한다.

```bash
shasum -a 256 data/equipment.db
shasum -a 256 /path/to/blog_snapshot_YYYYMMDD_HHMMSS.db
```

## 7. 주의 사항

- 분석 결과에는 DB 파일 자체보다 DB 기준 문서가 더 중요하다.
- 다운로드 폴더의 스냅샷은 임시 위치로 본다.
- 분석에 사용한 스냅샷은 `db-snapshots/`에 보관한다.
- 로컬 DB를 갱신하면 기존 분석 숫자가 바뀔 수 있다.
- 이미 완료된 프로젝트는 그 당시 사용한 DB 기준을 유지한다.
- 새 스냅샷으로 다시 분석할 때는 기존 프로젝트를 덮어쓰지 않고 새 프로젝트 폴더를 만든다.
