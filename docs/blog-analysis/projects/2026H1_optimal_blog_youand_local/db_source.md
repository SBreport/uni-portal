# DB 기준

이 문서는 `2026H1_optimal_blog_youand_local` 프로젝트가 어떤 DB를 기준으로 분석되었는지 기록한다.

## 1. 분석 반영 DB

- 경로: `data/equipment.db`
- 파일 크기: 약 40MB
- 파일 수정 시각: 2026-06-29 18:35
- SHA-256: `278cf18aa75470061c24b7da5d84ec11f31040c992a3a309878f97699b032606`

분석에 사용한 주요 테이블은 다음과 같다.

- `blog_posts`
- `blog_accounts`
- `blog_sync_log`
- `evt_branches`

## 2. 원본 스냅샷 DB

- 파일명: `blog_snapshot_20260629_183327.db`
- 보관 위치: `docs/blog-analysis/db-snapshots/2026H1_optimal_blog_youand_local/blog_snapshot_20260629_183327.db`
- 최초 다운로드 위치: `/Users/jogon/Downloads/blog_snapshot_20260629_183327.db`
- 파일 크기: 약 16MB
- SHA-256: `681e338adc04c0b31797a86ac4240f7ee17acdc84dc1c6e099f52ed17e5e4faf`

스냅샷 포함 테이블:

- `blog_accounts`
- `blog_posts`
- `blog_sync_log`
- `evt_branches`
- `notion_sync_log`
- `paper_blog_links`
- `snapshot_meta`

## 3. 반영 전 로컬 백업

- 경로: `_백업/equipment_before_blog_snapshot_20260629_183448.db`
- 파일 크기: 약 39MB
- SHA-256: `cd1d74d00f83dbba4cd4b11a7abc411144fac0fc067979f2dea44d0ad14982b0`

## 4. 데이터 상태

`data/equipment.db` 기준:

| 항목 | 값 |
| --- | ---: |
| `blog_posts` row 수 | 21,512 |
| 최저 발행일 | 2024-04-11 |
| 최고 발행일 | 2026-06-30 |
| `blog_posts.updated_at` 최신값 | 2026-06-29 18:32:54 |

원본 스냅샷 DB 기준:

| 항목 | 값 |
| --- | ---: |
| `blog_posts` row 수 | 21,512 |
| 최저 발행일 | 2024-04-11 |
| 최고 발행일 | 2026-06-30 |
| `blog_posts.updated_at` 최신값 | 2026-06-29 18:32:54 |

## 5. 이번 프로젝트 추출 기준

이번 프로젝트는 위 DB의 `blog_posts`에서 2026년 1~6월 최적블로그 원고를 추출해 분석했다.

최종 HTML 리포트에서는 다음 보정이 반영되어 있다.

- 준최/NB 68건 제외
- 홍보성글로 잘못 분류된 최적 원고 1건 보정 포함
- 최종 분석 대상 3,406건

## 6. 다음에 DB 갱신이 필요할 때

새로운 운영 데이터로 다시 분석해야 하면 다음 절차를 따른다.

1. 운영 웹 관리자 모드에서 `블로그 분석 DB 다운로드`를 실행한다.
2. 새 스냅샷 파일명을 기록한다.
3. 새 스냅샷을 `docs/blog-analysis/db-snapshots/{프로젝트명}/`에 보관한다.
4. 현재 `data/equipment.db`를 `_백업/`에 백업한다.
5. 새 스냅샷을 로컬 DB에 반영한다.
6. `blog_posts` row 수, 최고 발행일, 최신 업데이트 시각을 확인한다.
7. 기존 프로젝트를 덮어쓰지 않고 새 프로젝트 폴더를 만든다.
8. 새 프로젝트 폴더에 `db_source.md`를 새로 작성한다.

공통 절차는 `../../standards/블로그분석_DB관리기준.md`를 따른다.
