# 블로그 관리 시스템 — 구현 현황

> 최종 업데이트: 2026-03-24

---

## 1. 시스템 개요

노션에서 관리하던 블로그 게시글 기록을 CSV로 추출 → DB화하여 uni-portal 웹앱에서 조회·관리하는 시스템.

```
노션 블로그 DB → CSV 내보내기 → blog/import_csv.py → equipment.db (blog_posts)
                                  ↓ (enrich.py)        ↓
                              가공 컬럼 자동 채움    uni-portal 웹앱 블로그탭에서 조회
```

---

## 2. 데이터 구조

### 2.1 blog_posts 테이블 (16,448건)

**원본 컬럼 (CSV에서 그대로):**

| 컬럼 | 설명 |
|------|------|
| content_number | 노션 콘텐츠 번호 ("유앤창원 3") |
| title | 게시글 제목 (raw, URL 포함 가능) |
| keyword | 키워드 ("왕십리써마지") |
| tags | 관련 태그 |
| post_type | 종류 (raw, 계정명 혼재) |
| blog_channel | "br" (브랜드) / "opt" (최적) |
| blog_id | 네이버 블로그 계정 ID |
| post_number | 게시글 번호 |
| platform | "blog" / "cafe" / "other" |
| published_url | 발행 URL |
| author | 담당자 (복수 가능, 콤마 구분) |
| published_at | 발행일자 (YYYY-MM-DD) |
| status | 진행상황 (이모지 포함) |
| project | 프로젝트 (노션 URL 포함) |

**가공 컬럼 (enrich.py에서 자동 생성):**

| 컬럼 | 소스 | 설명 |
|------|------|------|
| branch_name | content_number | "유앤창원" (지점명) |
| slot_number | content_number | "3" (슬롯번호) |
| post_type_main | post_type | 대분류 (논문글/정보성글/홍보성글/임상글/키컨텐츠/소개글/최적) |
| post_type_sub | post_type | 소분류 (최적계정명 등) |
| project_month | project | "2026-03" (프로젝트 월) |
| project_branch | project | "유앤아이 천안" (프로젝트 지점) |
| status_clean | status | "보고 완료" (이모지 제거) |
| clean_title | title | URL/[출처] 제거, 빈 제목→keyword 대체 |
| author_main | author | "김다혜" (주담당자) |
| author_sub | author | "김보라" (부담당자) |
| needs_review | 자동판단 | 1=이상데이터, 0=정상 |

### 2.2 blog_accounts 테이블 (230건)

| 컬럼 | 설명 |
|------|------|
| blog_id | 네이버 블로그 계정 ID (UNIQUE) |
| account_name | 별명 (예: "메디썰") |
| account_group | 그룹 (예: "로컬최적1") |
| channel | "br" / "opt" |
| note | 비고 |

### 2.3 blog_sync_log 테이블

CSV 임포트 이력 기록.

---

## 3. 가공 로직 (blog/enrich.py)

재사용 가능한 순수 함수 모듈. DB 의존 없음.

**사용처:**
- `blog/migrate_enrich.py` — 기존 데이터 일괄 가공
- `blog/import_csv.py` — 신규 CSV 임포트 시 자동 가공
- `api/routers/blog.py` — 웹 CSV 업로드 시 호출

**주요 함수:**
- `parse_content_number()` — 지점명/슬롯 분리
- `normalize_post_type()` — 대분류/소분류 분리
- `parse_project()` — 연/월/지점 파싱
- `clean_status()` — 이모지 제거
- `clean_title()` — URL 제거, 빈 제목 대체
- `split_author()` — 주/부 담당자 분리
- `enrich_row()` — 위 함수들 조합, 가공 컬럼 dict 반환

---

## 4. API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| GET /blog/posts | 목록 (필터: 채널/종류/지점/프로젝트월/작성자/날짜/검토필요) |
| GET /blog/posts/{id} | 상세 (연결 논문 포함) |
| GET /blog/filter-options | 필터 드롭다운 옵션 |
| GET /blog/dashboard | 대시보드 집계 데이터 |
| GET /blog/stats | 통계 |
| GET /blog/accounts | 계정 목록 (게시글 수 포함) |
| PATCH /blog/accounts/{blog_id} | 계정 별명/그룹 수정 |
| POST /blog/upload-csv | CSV 업로드 (관리자) |

---

## 5. 프론트엔드 (BlogView.vue)

3탭 구조:

- **대시보드**: 요약 카드 + 지점별 바차트 + 월별 추이 + 종류별 분포 + 최근 발행
- **목록**: 필터 바 + 테이블 + 상세 패널 (가공 데이터 기반, 검토필요 하이라이트)
- **계정관리**: blog_accounts CRUD (인라인 편집)

---

## 6. 파일 목록

```
blog/
├── BLOG_SYSTEM.md          ← 이 문서
├── enrich.py               ← 데이터 가공 로직 모듈
├── migrate_enrich.py       ← 기존 데이터 일괄 가공 스크립트
├── import_csv.py           ← CSV → DB 임포트 (가공 자동 적용)
└── __init__.py

api/routers/blog.py         ← API 엔드포인트
frontend/src/api/blog.ts    ← API 클라이언트
frontend/src/views/BlogView.vue  ← 프론트엔드 UI (3탭)
```

---

## 7. 데이터 품질 현황

| 항목 | 수치 |
|------|------|
| 총 게시글 | 16,448건 |
| 지점 파싱 완료 | 16,251건 (98.8%) |
| 종류 파싱 완료 | 15,248건 (92.7%) |
| 프로젝트월 파싱 | 14,270건 (86.8%) |
| 검토 필요 (needs_review=1) | 1,162건 (7.1%) |
| 계정 수 | 230개 |
