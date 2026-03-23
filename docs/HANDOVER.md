# 유앤아이의원 통합 관리 시스템 — 인수인계 기획안

> 최종 업데이트: 2026-03-20

---

## 1. 프로젝트 개요

피부과 유앤아이의원의 다지점 운영을 위한 **통합 관리 시스템**.
장비, 이벤트, 카페 마케팅, 시술 정보를 하나의 플랫폼에서 관리한다.

### 기술 스택

| 계층 | 기술 | 비고 |
|------|------|------|
| 프론트엔드 | Vue 3 + TypeScript + Vite | Composition API, SPA |
| 상태관리 | Pinia | auth, cafe, equipment, events |
| UI | Tailwind CSS 4.2 | 유틸리티 기반 |
| 백엔드 | FastAPI (Python) | JWT 인증, 47개 API |
| DB | SQLite (WAL 모드) | `data/equipment.db` 단일 파일 |
| 레거시 | Streamlit | 병행 운영 중, 추후 제거 예정 |

### 운영 구조

```
사용자 → 포털 페이지 (portal/index.html)
           ├─ [Stream 버전] → Streamlit (:8501) — 레거시
           └─ [Fast 버전]   → Vue.js (:5173) → FastAPI (:8000)
```

- **DB 공유**: Streamlit과 FastAPI 양쪽에서 동일한 `data/equipment.db` 사용
- **비즈니스 로직 공유**: `cafe/db.py`, `equipment/db.py`, `events/db.py`를 양쪽에서 import
- **독립 인증**: Streamlit은 HMAC 토큰, FastAPI는 JWT(HS256)

---

## 2. 디렉토리 구조

```
uni-portal/
│
├── data/equipment.db              ← 공유 DB (SQLite, WAL)
├── credentials.json               ← Google Sheets API 인증 키
│
├── app.py, ui_tabs.py, auth.py    ← Streamlit 레거시 (수정 금지)
├── config.py, init_db.py, users.py
│
├── cafe/                          ← 카페 마케팅 비즈니스 로직
│   ├── db.py                      # DB CRUD (양쪽 공유)
│   ├── sync.py                    # Google Sheets → DB 동기화
│   └── ui.py                      # Streamlit UI (레거시)
│
├── equipment/                     ← 보유장비 비즈니스 로직
│   ├── db.py                      # DB CRUD + 장비사전
│   └── sync.py                    # Google Sheets → DB 동기화
│
├── events/                        ← 이벤트 비즈니스 로직
│   ├── db.py                      # DB CRUD + 검색
│   ├── sync.py                    # Google Sheets/Excel → DB 동기화
│   ├── parser.py, price_parser.py # 이벤트 파싱 엔진
│   ├── normalizer.py              # 시술명 정규화
│   └── validators.py              # 데이터 검증
│
├── api/                           ← FastAPI 백엔드
│   ├── main.py                    # CORS, 라우터 등록, root_path="/api"
│   ├── auth_jwt.py                # JWT 생성/검증 (HS256)
│   ├── deps.py                    # get_current_user, require_role
│   ├── models.py                  # Pydantic 스키마
│   └── routers/
│       ├── auth.py                # POST /login, GET /me
│       ├── users.py               # CRUD (admin only)
│       ├── cafe.py                # 17개 엔드포인트
│       ├── equipment.py           # 13개 엔드포인트
│       └── events.py              # 12개 엔드포인트
│
├── frontend/                      ← Vue.js SPA
│   ├── vite.config.ts             # 프록시: /api → localhost:8000
│   └── src/
│       ├── api/                   # axios 클라이언트 (모듈별)
│       │   ├── client.ts          # baseURL="/api", JWT 인터셉터
│       │   ├── cafe.ts
│       │   ├── equipment.ts
│       │   ├── events.ts
│       │   └── users.ts
│       ├── stores/                # Pinia 상태관리
│       │   ├── auth.ts
│       │   ├── cafe.ts
│       │   ├── equipment.ts
│       │   └── events.ts
│       ├── views/                 # 페이지 컴포넌트
│       │   ├── LoginView.vue
│       │   ├── HomeView.vue       # 대시보드
│       │   ├── EquipmentView.vue  # 보유장비 (2컬럼 레이아웃)
│       │   ├── EventsView.vue     # 이벤트
│       │   ├── CafeView.vue       # 카페 마케팅
│       │   ├── BlogView.vue       # 블로그 (placeholder)
│       │   ├── TreatmentInfoView.vue  # 시술정보 (사전+논문)
│       │   └── AdminView.vue      # 관리자 모드
│       ├── components/
│       │   ├── common/
│       │   │   ├── AppSidebar.vue  # 좌측 네비게이션
│       │   │   └── DataTable.vue   # 범용 테이블
│       │   └── cafe/
│       │       ├── CafeDashboard.vue
│       │       ├── ArticleList.vue
│       │       └── ArticleEditor.vue
│       └── router/index.ts
│
├── portal/index.html              ← 버전 선택 포털
├── docker-compose.yml             ← 4 컨테이너 (portal, streamlit, api, frontend)
└── HANDOVER.md                    ← 이 문서
```

---

## 3. 로컬 실행 방법

### 백엔드 (FastAPI)
```bash
cd uni-portal
pip install -r api/requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
# → http://localhost:8000/docs (Swagger UI)
```

### 프론트엔드 (Vue.js)
```bash
cd uni-portal/frontend
npm install
npm run dev
# → http://localhost:5173
```

Vite 개발 서버가 `/api/*` 요청을 `localhost:8000`으로 프록시한다.

### 레거시 Streamlit
```bash
cd uni-portal
streamlit run app.py --server.port 8501
```

---

## 4. 인증 구조

### JWT 흐름

```
로그인 → POST /auth/login (username, password)
       → bcrypt 비밀번호 검증 (AUTH_SALT 사용)
       → JWT(HS256) 토큰 발급 (24시간 유효)
       → 프론트: localStorage에 저장

API 호출 → Authorization: Bearer {token}
         → deps.py의 get_current_user()가 검증
         → 만료/무효 시 401 → 프론트 인터셉터가 /login으로 리다이렉트
```

### 역할 체계

| 역할 | 값 | 권한 |
|------|-----|------|
| 관리자 | `admin` | 전체 (동기화, 사용자관리 포함) |
| 편집자 | `editor` | 데이터 수정 가능 |
| 지점담당 | `branch` | 담당 지점 데이터 수정 |
| 뷰어 | `viewer` | 조회만 가능 |

---

## 5. 주요 화면별 기능

### 5-1. HOME (대시보드)

`GET /dashboard` → 전체 현황 요약 (지점 수, 장비, 이벤트, 카페, 시술사전, 최근 동기화)

### 5-2. 보유장비

**레이아웃: 2컬럼 고정 (35% 테이블 : 65% 상세)**

좌측 테이블:
- 지점 / 카테고리 / 장비명 / 수량 / 사진 / 비고
- 지점, 카테고리 드롭다운 필터 + 장비명 검색
- 수량, 사진 체크, 비고 인라인 편집 → 일괄 저장

우측 상세 패널:
- 미선택 시: "장비를 선택하세요" 안내
- 클릭 시: 헤더(장비명, 지점·카테고리·비고 한 줄), 3개 섹션:
  - **[T] 시술 정보**: device_info 테이블에서 분류/설명/부위/작용원리/별칭/보유 지점 수
  - **[E] 현재 이벤트**: 해당 지점의 현재 기간 이벤트 (가격, 할인율, 회차)
  - **[P] 관련 논문**: 준비 중 (추후 구현)

주요 API:
- `GET /equipment?branch=&category=&search=`
- `PATCH /equipment/{id}` (수량, 사진, 비고 수정)
- `GET /cafe/equipment-context?branch_name=&equipment_name=` (시술정보+이벤트 연계)

주의사항:
- DB 컬럼명은 `지점명`이지만 API에서 `지점`으로 정규화하여 반환
- 사진 값은 DB에서 `O`이지만 API에서 `있음`으로 정규화

### 5-3. 이벤트

- 기간별 이벤트 목록 조회
- 카테고리 필터, 가격 포맷
- 동기화: Google Sheets URL 또는 Excel 파일 업로드

### 5-4. 카페 마케팅

**지점 선택**: 기본값 "전체 지점" (대시보드는 지점 미선택으로도 조회 가능)

3개 서브뷰:
- **대시보드**: 전 지점 현황 요약 (기간 기준)
- **원고 목록**: 지점별 원고 리스트 (지점 선택 필요)
- **원고 작성/편집**: 제목/본문/키워드/댓글/피드백 (지점 선택 필요)

상태 흐름: `작성대기 → 작성완료 → 검수완료 → 발행완료` (+ 수정요청, 보류)

### 5-5. 시술정보

2개 서브탭:
- **시술사전**: 시술 CRUD (이름/카테고리/별칭/설명/부위/원리/참고), KPI 카드, 검색
- **시술논문**: placeholder (추후 구현 예정)

### 5-6. 마케팅 (트리 메뉴)

사이드바에서 **마케팅** 클릭 시 하위 메뉴가 트리 형태로 펼쳐짐:
- **카페** (`/cafe`): 카페 마케팅 원고 관리 (대시보드/원고목록/원고작성)
- **블로그** (`/blog`): placeholder
- **플레이스** (`/place`): placeholder — 네이버 플레이스 마케팅 관리
- **웹페이지** (`/webpage`): placeholder — 홈페이지 콘텐츠/랜딩페이지 관리

### 5-7. 보고서

placeholder — 지점별 운영 현황 리포트 생성/열람

### 5-8. 관리자 모드 (admin only)

3개 서브탭:
- **사용자**: 계정 CRUD (역할, 지점 배정, 비밀번호 변경)
- **데이터 동기화**: 3가지
  - 장비 시트 동기화 (Google Sheets → DB)
  - 이벤트 수집 (Google Sheets URL 또는 Excel, 2개월 단위)
  - 카페 원고 가져오기 (시트 링크 + 지점 선택, 연/월은 자동)
- **시술정보 관리**: 보유수 업데이트, JSON→DB 동기화

---

## 6. API 엔드포인트 요약 (47개)

### Auth (2개)
```
POST /auth/login          — 로그인 → JWT 토큰
GET  /auth/me             — 현재 사용자 정보
```

### Users (4개, admin only)
```
GET    /users             — 전체 사용자 목록
POST   /users             — 사용자 생성
PATCH  /users/{username}  — 사용자 수정
DELETE /users/{username}  — 사용자 삭제
```

### Equipment (13개)
```
GET    /equipment                        — 장비 목록 (필터: branch, category, search)
GET    /equipment/branches               — 지점 목록
GET    /equipment/categories             — 카테고리 목록
PATCH  /equipment/{id}                   — 장비 수정 (수량, 사진, 비고)
POST   /equipment/photo-changes          — 사진 상태 일괄 변경
GET    /equipment/device-info            — 시술사전 전체 조회
GET    /equipment/device-info/search     — 시술 검색
GET    /equipment/device-info/match      — 장비명으로 시술 매칭
POST   /equipment/device-info            — 시술 추가/수정
DELETE /equipment/device-info/{name}     — 시술 삭제
POST   /equipment/sync                   — Google Sheets 동기화
POST   /equipment/device-info/update-counts  — 보유수 재계산
POST   /equipment/device-info/sync-json  — JSON→DB 동기화
```

### Cafe (17개)
```
GET  /cafe/periods                             — 기간 목록
GET  /cafe/branches                            — 지점 목록
POST /cafe/branch-periods                      — 지점-기간 생성/조회
GET  /cafe/branch-periods/{id}/meta            — 지점-기간 메타
PATCH /cafe/branch-periods/{id}/meta           — 메타 수정
GET  /cafe/branch-periods/{id}/articles        — 원고 목록
GET  /cafe/articles/{id}                       — 원고 상세
PATCH /cafe/articles/{id}                      — 원고 수정
POST /cafe/articles/{id}/status                — 상태 변경
POST /cafe/articles/{id}/publish               — 발행 정보 등록
PUT  /cafe/articles/{id}/comments/{slot}       — 댓글 추가/수정
POST /cafe/articles/{id}/feedbacks             — 피드백 추가
GET  /cafe/articles/{id}/history               — 상태 이력
GET  /cafe/summary/{period_id}                 — 대시보드 요약
GET  /cafe/equipment-context                   — 장비 연계 정보
POST /cafe/sync                                — Google Sheets 동기화
```

### Events (11개)
```
GET  /events                  — 이벤트 목록
GET  /events/branches         — 지점 목록
GET  /events/categories       — 카테고리 목록
GET  /events/periods          — 기간 목록
GET  /events/search           — 이벤트 검색 (장비명 매칭 포함)
GET  /events/summary          — 기간별 요약
GET  /events/price-history    — 가격 변동 이력
GET  /events/treatments       — 시술 구성 목록
POST /events/treatments       — 시술 구성 추가
PATCH /events/treatments/{id} — 시술 구성 수정
POST /events/sync             — 동기화 (URL 또는 파일)
```

---

## 7. DB 스키마 (주요 테이블)

```
branches         — 지점 (id, name, short_name, region)
categories       — 장비 카테고리 (id, name)
equipment        — 보유장비 (id, branch_id, category_id, name, quantity, photo_status, note)
device_info      — 시술사전 (name, category, summary, target, mechanism, aliases, usage_count, is_verified)

cafe_periods     — 카페 기간 (year, month, label, is_current)
cafe_branch_periods — 지점-기간 매핑
cafe_articles    — 카페 원고 (title, body, keyword, category, equipment_name, status, ...)
cafe_comments    — 댓글 (article_id, slot_number, comment_text, reply_text)
cafe_feedbacks   — 피드백 (article_id, author, content)
cafe_status_history — 상태 변경 이력

evt_periods      — 이벤트 기간
evt_items        — 이벤트 항목
evt_item_components — 이벤트 시술 구성
evt_branches     — 이벤트 지점

users            — 사용자 (username, password_hash, role, branch_id, memo)
sync_log         — 동기화 이력
```

---

## 8. 동기화 흐름

### 장비 동기화
```
관리자 모드 → [장비 시트 동기화] 클릭
→ POST /equipment/sync
→ equipment/sync.py → Google Sheets API (credentials.json)
→ equipment 테이블 upsert
```

### 이벤트 동기화
```
관리자 모드 → URL 입력 또는 Excel 업로드
→ POST /events/sync
→ events/sync.py → 파싱(parser.py) → 정규화(normalizer.py) → DB upsert
```

### 카페 원고 동기화
```
관리자 모드 → 시트 링크 입력 + 지점 선택(선택사항)
→ POST /cafe/sync { sheet_url, branch_filter }
→ URL에서 sheet_id 추출 → 환경변수 CAFE_SHEET_ID 설정
→ cafe/sync.py → gspread → 워크시트 파싱 → DB upsert
→ 에러 발생 시 [CAFE SYNC ERROR] 로그 + 500 응답 (detail 포함)
```

---

## 9. 미구현 / 추후 작업

### 높은 우선순위

| 항목 | 설명 | 상태 |
|------|------|------|
| 카페 대시보드 UI | 전 지점 현황을 한 눈에 보는 대시보드 디자인 | 미착수 (피드백 대기) |
| 카페 동기화 에러 진단 | 동기화 실패 시 상세 에러 표시 추가 완료, 실제 테스트 필요 | 테스트 필요 |
| 블로그 탭 | placeholder 상태 | 미착수 |

### 중간 우선순위

| 항목 | 설명 |
|------|------|
| 시술논문 연동 | `treatment_papers` 테이블 신설, 시술사전과 JOIN, 보유장비 상세 패널에 표시 |
| CSV 내보내기 | 각 탭 데이터 CSV 다운로드 |
| 이벤트 가격 히스토리 UI | 기간별 가격 변동 차트 |
| 폼 유효성 검사 | 필수 필드 검증, 에러 메시지 |

### 낮은 우선순위

| 항목 | 설명 |
|------|------|
| 로딩 스켈레톤 | 데이터 로드 중 UI |
| 토스트 알림 | 저장/에러 시 토스트 팝업 |
| 모바일 반응형 | 현재 데스크톱 전용 |
| NAS Docker 배포 | docker-compose 구성 완료, 포트포워딩 미설정 |

### 시술논문 DB 설계안

```sql
CREATE TABLE treatment_papers (
  id INTEGER PRIMARY KEY,
  device_name TEXT,          -- device_info.name 매칭 키
  title TEXT,                -- 논문 제목
  authors TEXT,              -- 저자
  journal TEXT,              -- 학술지명
  year INTEGER,              -- 발행 연도
  doi TEXT,                  -- DOI 링크
  summary TEXT,              -- 2~3줄 요약
  key_findings TEXT,         -- 핵심 결과
  evidence_level TEXT,       -- 근거 수준 (A/B/C)
  tags TEXT,                 -- 태그 (쉼표 구분)
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

연동 포인트:
- 보유장비 상세 패널 → [P] 관련 논문 섹션
- 시술정보 → 시술논문 서브탭
- 카페 원고 작성 시 참고 자료로 활용

---

## 10. 알려진 주의사항

1. **DB 컬럼명 불일치**: `equipment/db.py`의 `load_data()`가 `지점명`을 반환하지만, API에서 `지점`으로 정규화. 수정 시 양쪽 확인 필요.
2. **사진 값 정규화**: DB에서 `O`, API에서 `있음`으로 변환. 프론트엔드는 `있음` 기준.
3. **Streamlit import**: `cafe/db.py` 등에서 `import streamlit as st`가 try/except로 감싸져 있음. FastAPI에서도 import 가능.
4. **CAFE_SHEET_ID 환경변수**: 카페 동기화 시 프론트에서 전달한 sheet_url에서 추출하여 동적으로 설정. 영구 설정이 아닌 요청별 오버라이드.
5. **Vite 프록시 rewrite**: `/api` prefix를 제거하고 `localhost:8000`으로 전달. FastAPI의 `root_path="/api"`는 Swagger UI용.
6. **Streamlit 백업**: `_streamlit_backup/` 폴더에 기존 Streamlit 관련 파일이 보존됨. 복원 방법은 해당 폴더의 README.md 참고.

---

## 11. 논문 분석 시스템 운영 매뉴얼

### 11.1 개요

미용의료 논문 PDF를 AI(Claude API)로 분석하여 서술형 요약을 생성하고 DB에 저장하는 시스템.
칼럼 작가가 논문 내용을 쉽게 참고할 수 있도록 전문 용어를 풀어서 설명하는 방식으로 요약됨.

```
논문 PDF → [papers/analyzer.py] → Claude API 분석 → 로컬 DB 저장
                                                        ↓
                                            JSON 파일로 출력 (paper_results/)
                                                        ↓
                                          웹앱에서 JSON 업로드 → NAS DB 반영
```

### 11.2 사전 준비

1. **Anthropic API 키 발급**: https://console.anthropic.com/ 에서 발급
2. **환경변수 설정**:
   ```bash
   # Windows (PowerShell)
   $env:ANTHROPIC_API_KEY = "sk-ant-api03-..."

   # Mac/Linux
   export ANTHROPIC_API_KEY="sk-ant-api03-..."
   ```
3. **Python 패키지 설치** (최초 1회):
   ```bash
   pip install anthropic pymupdf python-docx openpyxl
   ```

### 11.3 논문 분석 실행

```bash
# 프로젝트 루트에서 실행
cd uni-portal

# 폴더 내 모든 PDF 분석 (권장)
python papers/analyzer.py --dir "Z:\스마트브랜딩 팀 공유 폴더\블로그 폴더\유앤아이의원\0. 논문 관련\00_리프팅시술"

# 단일 파일 분석
python papers/analyzer.py paper.pdf

# 분석만 하고 DB 저장 안 함 (테스트용)
python papers/analyzer.py --dry-run paper.pdf

# 기존 JSON 결과에서 Word/Excel만 재출력
python papers/analyzer.py --export-only paper_results/papers_20260322.json
```

#### 분석 파이프라인 (자동)
```
PDF 텍스트 추출 → DOI 추출 → 학술 논문 검증 → 중복 체크 → CrossRef 메타데이터
→ Claude API 분석 → 장비/시술 매칭 → 로컬 DB 저장 + JSON/Word/Excel 출력
```

- **비학술 자료** (AI 정리본, 개인 컴파일): 자동 필터링 (API 비용 0)
- **중복 논문** (파일 해시/DOI/제목 일치): 자동 건너뜀 (API 비용 0)
- **1건당 소요 시간**: 약 30~60초 (Claude API 호출)
- **1건당 비용**: 약 $0.01~0.03 (토큰 사용량에 따라 다름)

### 11.4 분석 결과 웹앱에 업로드

분석 완료 후 `paper_results/` 폴더에 생성된 JSON 파일을 웹앱에 업로드:

1. 웹앱 접속 → **시술정보** → **시술논문** 탭 이동
2. 우상단 **"JSON 업로드"** 버튼 클릭
3. `paper_results/papers_YYYYMMDD_HHMMSS.json` 파일 선택
4. **업로드** 클릭
5. 결과 확인: `N건 등록, M건 중복 건너뜀`

> 중복 논문(DOI/제목 동일)은 자동으로 건너뛰므로 같은 파일을 여러 번 업로드해도 안전합니다.

### 11.5 권장 처리 순서 (대량 분석)

논문 PDF가 폴더별로 정리되어 있으므로 순서대로 처리:

```
00_리프팅시술 (46건) → 01_필러 보톡스 (16건) → 02_색소질환 (10건)
→ 03_스킨부스터 (29건) → 04_여드름 (3건) → 05_레이저시술 (2건)
→ 06_흉터 모공 (13건) → 07_제모 (3건) → 09_비만 (7건)
```

각 폴더 처리 후 생성된 JSON을 웹앱에 업로드하면 됩니다.

### 11.6 관련 파일

| 파일 | 역할 |
|------|------|
| `papers/analyzer.py` | CLI 분석 도구 (메인) |
| `paper_results/` | 분석 결과 출력 (JSON/Word/Excel) |
| `papers/SYSTEM.md` | 시스템 상세 구조 문서 |
| `api/routers/papers.py` | 논문 API (조회/등록/수정/삭제/JSON업로드) |
| `frontend/src/views/PapersView.vue` | 논문 열람 UI |

### 11.7 분석 프롬프트 수정

분석 결과의 형식이나 내용을 변경하려면 `papers/analyzer.py`의 `ANALYSIS_PROMPT` 변수를 수정합니다.

주요 규칙:
- **제목 번역**: 원문 의미 최대한 보존, 과도한 함축 금지
- **서술 방식**: 글머리 기호 나열 X, 서술형 줄 글
- **전문 용어**: 첫 등장 시 괄호 안 쉬운 설명 추가
- **근거 수준**: 0(미분류)~5(메타분석) 자동 판정
