# 유앤아이의원 통합 관리 시스템 — 작업 기록

> 최종 업데이트: 2026-03-20
> 목적: Streamlit → FastAPI+Vue 마이그레이션 과정의 모든 작업 이력을 기록하여 후속 고도화에 활용

---

## 목차

1. [프로젝트 구조](#1-프로젝트-구조)
2. [기술 스택](#2-기술-스택)
3. [파일 맵 (전체)](#3-파일-맵)
4. [화면별 구현 현황](#4-화면별-구현-현황)
5. [API 엔드포인트 맵](#5-api-엔드포인트-맵)
6. [DB 스키마 핵심](#6-db-스키마-핵심)
7. [작업 이력 (상세)](#7-작업-이력-상세)
8. [버그 수정 이력](#8-버그-수정-이력)
9. [알려진 이슈 & 미완성](#9-알려진-이슈--미완성)
10. [다음 작업 계획](#10-다음-작업-계획)

---

## 1. 프로젝트 구조

```
uni-portal/
├── api/                          # FastAPI 백엔드
│   ├── main.py                   # 앱 엔트리, CORS, 라우터 등록
│   ├── auth_jwt.py               # JWT 토큰 생성/검증 (HS256)
│   ├── deps.py                   # 의존성 주입 (인증 가드)
│   ├── models.py                 # Pydantic 스키마
│   └── routers/
│       ├── auth.py               # 로그인/사용자 정보
│       ├── users.py              # 사용자 CRUD (관리자)
│       ├── cafe.py               # 카페 마케팅 (17 엔드포인트)
│       ├── equipment.py          # 보유장비 (13 엔드포인트)
│       └── events.py             # 이벤트 (12 엔드포인트)
│
├── cafe/                         # 카페 모듈 (Streamlit/FastAPI 공용)
│   ├── db.py                     # DB CRUD (load_cafe_articles 등)
│   ├── sync.py                   # 구글 시트 동기화
│   └── ui.py                     # Streamlit UI (레거시)
│
├── equipment/                    # 장비 모듈
│   ├── db.py                     # DB CRUD + 장비사전
│   └── sync.py                   # 구글 시트 동기화
│
├── events/                       # 이벤트 모듈
│   ├── db.py                     # DB CRUD + 검색 (지점 ㄱㄴㄷ순)
│   ├── sync.py                   # 구글 시트/엑셀 동기화
│   ├── parser.py                 # 이벤트 파싱 엔진
│   ├── price_parser.py           # 가격 추출
│   ├── normalizer.py             # 시술명 정규화
│   └── validators.py             # 데이터 검증
│
├── frontend/                     # Vue.js SPA
│   ├── src/
│   │   ├── api/                  # Axios 클라이언트
│   │   │   ├── client.ts         # 기본 설정 (baseURL, timeout 30s, JWT 인터셉터)
│   │   │   ├── cafe.ts           # 카페 API (동기화 timeout 180s)
│   │   │   ├── equipment.ts      # 장비 API
│   │   │   ├── events.ts         # 이벤트 API
│   │   │   └── users.ts          # 사용자 API
│   │   ├── components/
│   │   │   ├── common/
│   │   │   │   ├── AppSidebar.vue     # 사이드바 (트리메뉴)
│   │   │   │   └── DataTable.vue      # 공용 테이블 컴포넌트
│   │   │   └── cafe/
│   │   │       ├── ArticleEditor.vue  # 원고 편집기
│   │   │       ├── ArticleList.vue    # 원고 목록 (구버전, 미사용)
│   │   │       ├── ArticleListV1.vue  # 원고 목록 V1 (2단 구조)
│   │   │       ├── ArticleListV2.vue  # 원고 목록 V2 (3컬럼+사이드패널)
│   │   │       └── CafeDashboard.vue  # 카페 대시보드
│   │   ├── stores/               # Pinia 상태관리
│   │   │   ├── auth.ts
│   │   │   ├── cafe.ts           # SummaryRow 인터페이스 포함
│   │   │   ├── equipment.ts
│   │   │   └── events.ts
│   │   ├── views/                # 페이지 뷰
│   │   │   ├── HomeView.vue
│   │   │   ├── LoginView.vue
│   │   │   ├── CafeView.vue      # 서브탭: 대시보드/원고목록/원고작성/발행결과
│   │   │   ├── EquipmentView.vue  # 35:65 2컬럼, 상세패널
│   │   │   ├── EventsView.vue    # 검색+가격필터
│   │   │   ├── AdminView.vue     # 데이터동기화, 시술정보관리
│   │   │   ├── DictionaryView.vue
│   │   │   ├── TreatmentInfoView.vue
│   │   │   ├── BlogView.vue      # 플레이스홀더
│   │   │   ├── PlaceView.vue     # 플레이스홀더
│   │   │   ├── WebpageView.vue   # 플레이스홀더
│   │   │   ├── ReportsView.vue   # 플레이스홀더
│   │   │   └── PapersView.vue
│   │   └── router/
│   │       └── index.ts          # 11개 라우트, 인증 가드
│   └── vite.config.ts            # /api 프록시 → localhost:8000
│
├── data/                         # SQLite DB 파일
│   └── equipment.db              # 전체 공유 DB (WAL 모드)
│
├── portal/                       # 버전 선택 포털
│   └── index.html                # Stream vs Fast 선택
│
├── docker-compose.yml
├── Dockerfile / Dockerfile.api / Dockerfile.frontend
├── HANDOVER.md                   # 인수인계 기획안
├── PROJECT_ROADMAP.md            # 로드맵
└── WORK_LOG.md                   # ← 이 파일
```

---

## 2. 기술 스택

| 계층 | 기술 | 버전 | 비고 |
|------|------|------|------|
| 프론트엔드 | Vue 3 + TypeScript | Composition API | SPA, Vite 7.3 |
| 상태관리 | Pinia | | auth, cafe, equipment, events |
| UI | Tailwind CSS | 4.2 | 유틸리티 기반 |
| 테이블 | TanStack Vue Table | | DataTable 컴포넌트 |
| 백엔드 | FastAPI (Python) | | JWT(HS256), bcrypt |
| DB | SQLite | WAL 모드 | 단일 파일 공유 |
| 외부 연동 | gspread + google-auth | | 구글 시트 동기화 |
| 레거시 | Streamlit | :8501 | 병행 운영 중 |

### 주요 설정 패턴

```
Vite 프록시: /api/* → localhost:8000/* (prefix strip)
FastAPI root_path="/api" → Swagger UI용
Axios baseURL: '/api', timeout: 30000 (동기화만 180000)
JWT: HS256, localStorage 저장, 인터셉터 자동 첨부
```

---

## 3. 파일 맵

### Vue 컴포넌트 (21개)

| 파일 | 역할 | 상태 |
|------|------|------|
| `App.vue` | 루트 레이아웃 | ✅ 완료 |
| `LoginView.vue` | 로그인 | ✅ 완료 |
| `HomeView.vue` | 홈 대시보드 | ✅ 기본 완료 |
| `CafeView.vue` | 카페 메인 (4 서브탭) | ✅ 완료 |
| `CafeDashboard.vue` | 카페 대시보드 테이블 | ✅ 완료 |
| `ArticleListV1.vue` | 원고 목록 V1 (3컬럼: 순번\|제목+본문\|댓글) | ✅ 완료 |
| `ArticleListV2.vue` | 원고 목록 V2 (4컬럼: 메타\|본문\|댓글\|사이드패널) | ✅ 완료 |
| `ArticleList.vue` | 원고 목록 (초기 버전, 미사용) | ⚠️ 레거시 |
| `ArticleEditor.vue` | 원고 편집기 | ✅ 완료 |
| `EquipmentView.vue` | 보유장비 (35:65 2컬럼) | ✅ 완료 |
| `EventsView.vue` | 이벤트 (검색+가격필터) | ✅ 완료 |
| `AdminView.vue` | 관리자 모드 | ✅ 완료 |
| `DictionaryView.vue` | 장비 사전 | ✅ 완료 |
| `TreatmentInfoView.vue` | 시술 정보 | ✅ 완료 |
| `BlogView.vue` | 블로그 | 📋 플레이스홀더 |
| `PlaceView.vue` | 플레이스 | 📋 플레이스홀더 |
| `WebpageView.vue` | 웹페이지 | 📋 플레이스홀더 |
| `ReportsView.vue` | 보고서 | 📋 플레이스홀더 |
| `PapersView.vue` | 논문 | 📋 플레이스홀더 |
| `AppSidebar.vue` | 좌측 사이드바 | ✅ 완료 |
| `DataTable.vue` | 공용 테이블 | ✅ 완료 |

### API 라우터 (5개, 총 47+ 엔드포인트)

| 파일 | 엔드포인트 수 |
|------|-------------|
| `routers/auth.py` | 2 |
| `routers/users.py` | 3 |
| `routers/cafe.py` | 17 |
| `routers/equipment.py` | 13 |
| `routers/events.py` | 12 |

### Pinia 스토어 (4개)

| 스토어 | 주요 상태 |
|--------|----------|
| `auth` | token, username, role, isLoggedIn |
| `cafe` | periods, branches, articles, summary, currentArticle |
| `equipment` | items, filters, selectedItem |
| `events` | events, branches, filters (global/price/branch) |

---

## 4. 화면별 구현 현황

### 4-1. 사이드바 (AppSidebar.vue)

```
메뉴 구조:
H  HOME           → /
E  보유장비        → /equipment
V  이벤트          → /events
T  시술정보        → /treatment-info
M  마케팅 ▼        (트리 메뉴, 자동 펼침)
   C 카페          → /cafe
   B 블로그        → /blog
   P 플레이스      → /place
   W 웹페이지      → /webpage
───────────────────
R  보고서          → /reports
A  관리자 모드     → /admin (admin만 표시)
```

- 트리 메뉴: CSS transition으로 접기/펼치기
- 마케팅 하위 페이지 접속시 자동 펼침
- 현재 활성 라우트 파란색 하이라이트

### 4-2. 카페 마케팅 (CafeView.vue)

**서브탭 구성**: `대시보드` | `원고 목록` | `원고 작성` | `발행 결과`

**필터 바**: 지점 선택(전체 기본), 연도, 월

#### 대시보드 (CafeDashboard.vue)
- KPI 카드 5개: 전체원고, 발행완료, 미착수, 발행률, 지점수
- 지점별 테이블: 지점, 담당자, 작가, 총건수, 진행상황(프로그레스바)
- **토글**: 유형별 상세 (정보성/후기성/슈퍼세트) 접기/펼치기
- **지점 클릭**: 해당 지점 원고 목록으로 이동 (`emit('go-branch')`)

#### 원고 목록 — V1 (ArticleListV1.vue)
```
레이아웃: 3컬럼 그리드
┌──52px──┬────── minmax(0,480px) ──┬────── 1fr ──────────────┐
│  순번   │ [장비태그] 제목          │ 댓1 내용...              │
│ 상태배지 │ 본문 내용...            │   ↩ 대댓글...            │
│         │                        │ 댓2 내용...              │
│         │                        │   ↩ 대댓글...            │
└─────────┴────────────────────────┴─────────────────────────┘
```
- 상태 필터 칩 (전체/작성대기/작성완료/...)
- 검색 (제목/본문/장비/키워드)
- 교대 배경색, hover 효과
- 편집 버튼 → 원고 작성 탭으로 이동

#### 원고 목록 — V2 (ArticleListV2.vue)
```
레이아웃: 4컬럼 그리드
┌─180px──┬───── 1fr ─────┬───── 1fr ─────┬──150px──┐
│ 순번    │ 본문           │ 댓1 ...       │ 키워드   │
│ 상태    │               │  ↩ 대댓글     │ 카테고리  │
│ 제목    │               │ 댓2 ...       │ 작성03.05│
│ [장비]  │               │  ↩ 대댓글     │ 수정03.18│
│ 🔗 ✏️  │               │               │[상태변경▼]│
│         │               │               │ 🔗 ✏️   │
└─────────┴───────────────┴───────────────┴─────────┘
```
- 사이드 패널: 키워드, 카테고리, 작성일/수정일, 빠른 상태 변경 드롭다운
- `quickStatusChange()`: 목록에서 바로 상태 변경 가능

#### V1/V2 전환 토글
- 우측 상단 "레이아웃: [V1 2단] [V2 3컬럼]" 버튼
- 담당자와 함께 피드백 후 하나 확정 예정

#### 원고 작성 (ArticleEditor.vue)
- `◀ #N < 현재글 > #N ▶` 네비게이션
- 키워드/카테고리/장비/제목/본문 편집
- 댓글/대댓글 슬롯별 편집
- 피드백 영역 (→ 여백 최대 활용 예정)
- 상태 변경 + 발행 URL 입력

#### 발행 결과 (신규)
- 테이블 컬럼: 지점명 | # | 발행일 | 카페명 | 발행링크 | 유형 | 제목 | 발행여부
- `발행여부`: URL 유무로 "발행"/"미발행" 배지

### 4-3. 보유장비 (EquipmentView.vue)

```
레이아웃: 상시 2컬럼 (35% : 65%)
┌─── 35% 테이블 ──────┬─── 65% 상세 패널 ─────────────────┐
│ 지점 카테고리 장비명  │ 장비명                            │
│ w-14 w-16    w-28    │ 지점 · 카테고리 · 수량 · 비고      │
│                      │ ────────────────────────           │
│ [클릭 → 상세]        │ [T] 시술 정보 (별칭 태그)          │
│                      │ [E] 현재 이벤트 (% OFF 배지)       │
│                      │ [P] 관련 논문 (준비 중)            │
└──────────────────────┴────────────────────────────────────┘
```
- 필터: 지점, 카테고리
- 클릭 시 `GET /cafe/equipment-context` 호출
- 비고가 있으면 헤더에 한 줄로 표시

### 4-4. 이벤트 (EventsView.vue)
- 필터 바: 지점 선택, 이벤트명 검색, 테이블 내 검색, 가격대 검색 (만원 단위)
- 컬럼: 이벤트명(320px), 비고(100px) + hover 툴팁
- 가격 필터: `min * 10000`, `max * 10000` 비교

### 4-5. 관리자 모드 (AdminView.vue)
- 탭: `데이터 동기화` | `시술정보 관리`
- 카페 동기화: 링크 + 지점 선택만 (연도/월 자동)
- 동기화 실패 시 상세 에러 표시 (타임아웃/연결오류/상태코드)

---

## 5. API 엔드포인트 맵

### 인증 (auth.py)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/auth/login` | 로그인 → JWT 발급 |
| GET | `/auth/me` | 현재 사용자 정보 |

### 사용자 (users.py)
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/users` | 전체 목록 |
| POST | `/users` | 생성 |
| DELETE | `/users/{id}` | 삭제 |

### 카페 (cafe.py) — 17개
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/cafe/periods` | 기간 목록 |
| GET | `/cafe/branches` | 지점 목록 |
| POST | `/cafe/branch-periods` | 지점-기간 생성/조회 |
| GET | `/cafe/branch-periods/{id}/meta` | 메타 정보 |
| GET | `/cafe/branch-periods/{id}/articles` | 원고 목록 (body + comments_json 포함) |
| GET | `/cafe/articles/{id}` | 원고 상세 |
| PATCH | `/cafe/articles/{id}` | 원고 수정 |
| POST | `/cafe/articles/{id}/status` | 상태 변경 |
| POST | `/cafe/articles/{id}/publish` | 발행 |
| PUT | `/cafe/articles/{id}/comments/{slot}` | 댓글 저장 |
| POST | `/cafe/articles/{id}/feedbacks` | 피드백 추가 |
| GET | `/cafe/articles/{id}/history` | 상태 이력 |
| GET | `/cafe/summary/{period_id}` | 대시보드 요약 |
| POST | `/cafe/sync` | 구글 시트 동기화 |
| GET | `/cafe/equipment-context` | 장비 연계 시술+이벤트 |

### 장비 (equipment.py) — 13개
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/equipment` | 전체 목록 (지점명→지점, 사진 O→있음 정규화) |
| GET | `/equipment/branches` | 지점 목록 |
| GET | `/equipment/categories` | 카테고리 목록 |
| GET | `/equipment/{id}` | 상세 |
| ... | ... | (총 13개) |

### 이벤트 (events.py) — 12개
| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/events` | 전체 목록 |
| GET | `/events/branches` | 지점 목록 (ㄱㄴㄷ순) |
| GET | `/events/search` | 검색 |
| ... | ... | (총 12개) |

---

## 6. DB 스키마 핵심

### 컬럼명 정규화 패턴 (중요!)

DB와 API 사이 컬럼명 불일치가 있으며 API에서 정규화:

| DB 컬럼 | API 응답 | 처리 위치 |
|---------|---------|----------|
| `지점명` | `지점` | `equipment.py` rename_map |
| `순번` | `id` | `equipment.py` rename_map |
| `사진` = `O` | `사진` = `있음` | `equipment.py` lambda |

### 카페 원고 쿼리 (cafe/db.py)
```sql
SELECT a.id, a.article_order, a.keyword, a.category, a.equipment_name,
       a.title, a.body, a.status, a.published_url, a.created_at, a.updated_at,
       COALESCE(cmt.comment_count, 0) AS comment_count,
       COALESCE(cmt.comments_json, '[]') AS comments_json
FROM cafe_articles a
LEFT JOIN (
    SELECT article_id, COUNT(*) AS comment_count,
           '[' || GROUP_CONCAT(
               '{"slot":' || slot_number ||
               ',"comment":' || json_quote(COALESCE(comment_text, '')) ||
               ',"reply":' || json_quote(COALESCE(reply_text, '')) || '}'
           ) || ']' AS comments_json
    FROM cafe_comments
    WHERE comment_text != '' OR reply_text != ''
    GROUP BY article_id
) cmt ON cmt.article_id = a.id
WHERE a.branch_period_id = ?
ORDER BY a.article_order
```

### 이벤트 지점 정렬 (events/db.py)
```sql
-- 변경 전: ORDER BY er.sort_order, eb.name
-- 변경 후: ORDER BY eb.name   ← ㄱㄴㄷ순
```

---

## 7. 작업 이력 (상세)

### 세션 1 — 초기 구축 & 기본 기능

| # | 작업 | 파일 | 설명 |
|---|------|------|------|
| 1 | FastAPI 백엔드 구축 | `api/` 전체 | JWT 인증, 47개 API 엔드포인트 |
| 2 | Vue SPA 프론트엔드 | `frontend/` 전체 | Vite + Vue3 + Pinia + Tailwind |
| 3 | 포털 페이지 | `portal/index.html` | Stream/Fast 버전 선택 |
| 4 | Docker 구성 | `docker-compose.yml` 등 | 3-서비스 (api, frontend, streamlit) |

### 세션 2 — 기능 고도화

| # | 작업 | 관련 파일 | 상세 |
|---|------|----------|------|
| 5 | 카페 동기화 오류 진단 | `api/routers/cafe.py` | try/except + traceback 로깅 추가 |
| 6 | 관리자 탭 텍스트 변경 | `AdminView.vue` | 동기화→데이터동기화, 시술사전→시술정보 |
| 7 | 카페 동기화 UI 간소화 | `AdminView.vue` | 연도/월 제거, 링크+지점만 유지 |
| 8 | 카페 기본 지점 변경 | `CafeView.vue` | "지점 선택" → "전체 지점" 기본값 |
| 9 | 장비 필터 버그 수정 | `api/routers/equipment.py` | 지점명→지점, O→있음 정규화 |
| 10 | 장비 상세 패널 추가 | `EquipmentView.vue` | 클릭→시술정보+이벤트 연계, 35:65 비율 |
| 11 | 장비 비고 한줄 표시 | `EquipmentView.vue` | 지점·카테고리·수량·비고 inline |
| 12 | 이벤트 검색 이동 | `EventsView.vue` | 필터바로 이동, 가격대 검색 추가 |
| 13 | 이벤트 비고 hover | `EventsView.vue` | truncate + title tooltip |
| 14 | 사이드바 트리 메뉴 | `AppSidebar.vue` | 마케팅 하위 트리, 자동 펼침 |
| 15 | 플레이스홀더 뷰 추가 | `BlogView.vue` 등 | 블로그/플레이스/웹페이지/보고서 |
| 16 | 라우터 확장 | `router/index.ts` | /blog, /place, /webpage, /reports |
| 17 | 지점 ㄱㄴㄷ순 정렬 | `events/db.py` | ORDER BY eb.name |
| 18 | 원고 에디터 네비 수정 | `ArticleEditor.vue` | currentId ref 추가, prev/next 수정 |
| 19 | 원고 목록 리디자인 | `cafe/db.py` + `ArticleList.vue` | body+comments_json SQL, 카드형 |

### 세션 3 — 원고 목록 고도화 & 대시보드

| # | 작업 | 관련 파일 | 상세 |
|---|------|----------|------|
| 20 | 원고 목록 V1 2단 구조 | `ArticleListV1.vue` | 상하 2단: 제목+본문 / 댓글쌍 |
| 21 | 원고 목록 V2 3컬럼 | `ArticleListV2.vue` | 메타\|본문\|댓글 3컬럼 블록 |
| 22 | V1/V2 전환 토글 | `CafeView.vue` | 레이아웃 버튼 추가 |
| 23 | V1 3컬럼 재구성 | `ArticleListV1.vue` | 52px\|제목+본문\|댓글 구조 |
| 24 | V1 본문폭 제한 | `ArticleListV1.vue` | minmax(0, 480px) |
| 25 | V2 사이드 패널 추가 | `ArticleListV2.vue` | 키워드/카테고리/날짜/상태변경/액션 |
| 26 | 대시보드 구글시트 분석 | — | CSV 데이터 구조 분석 (42지점) |
| 27 | 대시보드 고도화 | `CafeDashboard.vue` | 담당자/작가/진행상황/유형토글/비고 |
| 28 | 지점 클릭→원고 이동 | `CafeView.vue` + `CafeDashboard.vue` | goToBranch() emit |
| 29 | 동기화 타임아웃 수정 | `api/cafe.ts` (client) | 30s → 180s (동기화만) |
| 30 | 발행결과 탭 신규 | `CafeView.vue` | 지점명/발행일/카페명/링크/유형/제목/발행여부 |
| 31 | 탭 재구성 | `CafeView.vue` | 대시보드-원고목록-원고작성-발행결과 |

---

## 8. 버그 수정 이력

| # | 증상 | 원인 | 해결 | 파일 |
|---|------|------|------|------|
| B1 | 장비 필터 작동 안 함 | DB `지점명` vs API `지점` 불일치 | rename_map 정규화 | `equipment.py` |
| B2 | 장비 사진 "O" 표시 | DB `O` vs UI `있음` 불일치 | lambda 정규화 | `equipment.py` |
| B3 | 동기화 실패 에러 없음 | try/except 미적용 | traceback 로깅 추가 | `cafe.py` |
| B4 | 원고 ◀▶ 네비 오류 | props.articleId 미갱신 | currentId ref 분리 | `ArticleEditor.vue` |
| B5 | 지점 순서 불일치 | sort_order 우선 정렬 | ORDER BY eb.name | `events/db.py` |
| B6 | 동기화 프론트 타임아웃 | Axios 30초 < 실제 소요시간 | 동기화만 180초 | `api/cafe.ts` |

---

## 9. 알려진 이슈 & 미완성

### 미완성 기능

| 항목 | 현황 | 우선도 |
|------|------|--------|
| 카페 동기화 실제 테스트 | 로깅 추가됨, 실환경 검증 필요 | 🔴 높음 |
| 대시보드 담당자/작가 매칭 | 동기화 후 데이터 확인 필요 | 🔴 높음 |
| 원고 작성 피드백 영역 확대 | 레이아웃 여백 최대 활용 예정 | 🟡 중간 |
| ArticleList V1/V2 확정 | 담당자 피드백 후 하나 제거 | 🟡 중간 |
| 시술논문 연동 | DB 스키마 설계됨, UI 플레이스홀더 | 🟢 낮음 |
| 블로그/플레이스/웹페이지 | 플레이스홀더만 존재 | 🟢 낮음 |
| 보고서 탭 | 플레이스홀더 | 🟢 낮음 |
| NAS Docker 배포 | docker-compose 준비됨, 포트포워딩 미설정 | 🟢 낮음 |

### 알려진 기술 이슈

| 이슈 | 설명 |
|------|------|
| Streamlit/FastAPI DB 동시접근 | WAL 모드로 대응 중, 동시 쓰기 시 lock 가능 |
| 구글 시트 인증 | gspread 설치 + 서비스 계정 credentials 필요 |
| 발행결과 데이터 부족 | published_at, published_by 등 미입력 원고 다수 |

---

## 10. 다음 작업 계획

### 즉시 (다음 세션)

1. **Streamlit 스타일 → FastAPI 스타일 전환**
   - 현재 `cafe/db.py`, `equipment/db.py`, `events/db.py`는 Streamlit과 공유
   - FastAPI 전용으로 분리하거나, Streamlit 의존성 제거
   - 목표: Streamlit 없이 FastAPI+Vue만으로 완전 독립 운영

2. **카페 대시보드 데이터 정합성**
   - 동기화 실행 → 담당자/작가 이름 정상 표시 확인
   - 구글 시트 컬럼 매핑 검증

3. **원고 작성 피드백 영역 확대**
   - 현재 여백 → 피드백 칸 전체 활용

### 중기

4. **V1/V2 확정 후 레거시 제거**
5. **블로그/플레이스/웹페이지 콘텐츠 구현**
6. **보고서 탭 — 월간 리포트 자동 생성**
7. **시술논문 DB 연동 + 장비 패널 연계**

### 장기

8. **Streamlit 완전 제거**
9. **NAS Docker 배포 + 포트포워딩**
10. **다중 사용자 동시 편집 처리**

---

## 참고: 구글 시트 원본 데이터 구조

```
순번 | 지점명 | 스마트 담당자 | 원고작가 | 진행상황 | 정보성 | 피드백 | 후기성 | 피드백 | 슈퍼세트 | 피드백 | 시술사진 | 현장사진 | 나노사진 | 비고
```

- 42개 지점, 각 지점당 20건 원고
- 담당자: 오현정, 강태우, 김보라, 배재준, 최은주
- 작가: S오현정, S손현진, 자체 제작
- 진행상황: "20 / 20" 형식
- 사진: URL 또는 "없음(12/12)" 형식
