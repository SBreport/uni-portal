# 유앤아이의원 통합 관리 시스템 — 작업 기록

> 최종 업데이트: 2026-03-22 (세션2)
> 기술 스택: FastAPI + Vue 3 (Composition API) + TypeScript + Tailwind CSS 4.2 + SQLite

---

## 1. 프로젝트 구조 (FastAPI 전환 후)

```
uni-portal/
├── api/                     # FastAPI 백엔드
│   ├── main.py              # 앱 엔트리포인트
│   ├── models.py            # Pydantic 스키마
│   └── routers/
│       ├── auth.py          # JWT 인증
│       ├── users.py         # 사용자 관리
│       ├── cafe.py          # 카페 마케팅 (17+ endpoints)
│       ├── equipment.py     # 보유장비
│       ├── events.py        # 이벤트
│       └── papers.py        # 논문/연구자료 (신규)
├── frontend/                # Vue.js 프론트엔드
│   ├── src/
│   │   ├── views/           # 메인 뷰
│   │   │   ├── HomeView.vue
│   │   │   ├── CafeView.vue
│   │   │   ├── EquipmentView.vue
│   │   │   ├── EventsView.vue
│   │   │   ├── AdminView.vue
│   │   │   ├── ReportsView.vue    (placeholder)
│   │   │   ├── PlaceView.vue      (placeholder)
│   │   │   └── WebpageView.vue    (placeholder)
│   │   ├── components/
│   │   │   ├── cafe/
│   │   │   │   ├── ArticleListV1.vue   # 3컬럼 그리드 (순번+상태|제목+본문|댓글)
│   │   │   │   ├── ArticleListV2.vue   # 4컬럼 (원고정보|본문|댓글|메타+액션)
│   │   │   │   ├── ArticleEditor.vue
│   │   │   │   └── CafeDashboard.vue
│   │   │   └── common/
│   │   │       ├── AppSidebar.vue      # 트리형 사이드바
│   │   │       └── DataTable.vue
│   │   ├── stores/          # Pinia 상태관리
│   │   ├── api/             # Axios API 클라이언트
│   │   └── router/          # Vue Router
│   └── vite.config.ts
├── cafe/                    # 카페 DB/동기화 모듈
│   ├── db.py
│   └── sync.py
├── equipment/               # 장비 DB/동기화/매칭 모듈
│   ├── db.py
│   ├── matcher.py           # 공용 장비 매칭 엔진 (Single Source of Truth)
│   └── sync.py
├── events/                  # 이벤트 DB/동기화/파서 모듈
│   ├── db.py
│   ├── sync.py
│   ├── parser.py
│   ├── normalizer.py
│   ├── validators.py
│   └── price_parser.py
├── data/
│   └── equipment.db         # SQLite DB (WAL mode)
├── _streamlit_backup/       # Streamlit 버전 백업 (2026-03-22)
├── docker-compose.yml       # FastAPI + Vue 2서비스
├── Dockerfile.api
├── Dockerfile.frontend
├── init_db.py               # DB 스키마 (25개 테이블) + 시드 데이터
└── requirements.txt         # FastAPI 의존성
```

---

## 2. 완료된 작업

### 2.1 카페 마케팅 (CafeView)

#### 탭 구성: 대시보드 — 원고 목록 — 원고 작성 — 발행 결과

#### 대시보드
- 전체 지점 요약 카드 (전체 원고, 발행 완료, 미착수, 발행률, 지점 수)
- 지점별 테이블: 지점/담당자/작가/총건수/진행상황
- 유형별 상세 토글 (정보성·후기성·슈퍼세트) — 접기/펼치기

#### 원고 목록 (V1/V2 레이아웃 선택)
- **V1 — 3컬럼 그리드**: `52px | minmax(0,480px) | 1fr`
  - 1열: 순번 + 상태 배지 (세로 정렬, 최소 공간)
  - 2열: 장비 태그 + 제목 + 본문 (8줄 clamp)
  - 3열: 댓글·대댓글 쌍으로 묶어 표시
- **V2 — 4컬럼 블록 + 사이드 패널**: `180px | 1fr | 1fr | 150px`
  - 원고정보 | 본문 | 댓글·대댓글 | **메타+빠른액션**
  - 사이드: 키워드, 카테고리, 작성/수정일, 상태 변경 드롭다운, 발행/편집 링크
- 상단: 상태 필터 칩 + 전체 검색
- 레이아웃 전환 버튼 (우상단)
- 교대 배경색 + hover 하이라이트

#### 원고 작성 (ArticleEditor)
- 원고 메타(키워드/카테고리/장비명) 편집
- 본문 작성 + 실시간 저장
- 댓글·대댓글 3슬롯
- **◀ ▶ 네비게이션**: `currentId` 내부 ref로 독립 관리 (번호만 표시)
- 상태 변경 + 이력 조회

#### 발행 결과
- 컬럼: 지점명 / # / 발행일 / 카페명 / 발행링크 / 유형 / 제목 / 발행여부
- 발행/미발행 배지 표시

#### 동기화
- 구글 시트 → DB 동기화 (gspread + google-auth)
- **타임아웃**: 프론트 30초 → 180초 수정 (42개 지점 대응)
- 에러 로깅 (traceback) + 프론트엔드 상세 에러 메시지
- 카페 동기화 UI 간소화 (링크+지점만 유지, 연도/월 자동)

### 2.2 보유장비 (EquipmentView)

- 영구 2컬럼: 35% 테이블 : 65% 상세 패널
- 장비 클릭 → 시술 정보 + 현재 이벤트 연동 표시 (GET /cafe/equipment-context)
- 이벤트 할인율 배지, 장비 별명 태그
- 필터: 지점/카테고리
- **DB 컬럼명 정규화**: `지점명→지점`, 사진값 `O→있음` (equipment.py)
- 상세 패널 헤더: 장비명 + 지점·카테고리·수량·비고 한 줄
- 3섹션: [T] 시술 정보, [E] 현재 이벤트, [P] 관련 논문 (papers 연동 예정)

### 2.3 이벤트 (EventsView)

- 테이블 내 검색 + 이벤트명 검색 (필터바 통합)
- **가격대 필터** (만원 단위 입력 → ×10000 비교)
- 비고 컬럼: truncate + hover title 툴팁
- 이벤트명 320px, 비고 100px
- 지점 순서: ㄱㄴㄷ순 (`ORDER BY eb.name`)

### 2.4 사이드바 (AppSidebar)

- 트리형 마케팅 메뉴 (chevron 회전 애니메이션, CSS transition)
  - 하위: 카페 / 블로그 / 플레이스 / 웹페이지
  - 하위 탭 진입 시 자동 확장
- 메뉴 순서: HOME → 보유장비 → 이벤트 → 시술정보 → 마케팅(트리) → separator → 보고서 → 관리자 모드

### 2.5 관리자 모드 (AdminView)

- 탭명: 동기화→데이터 동기화, 시술사전 관리→시술정보 관리
- 카페 동기화 UI: 시트 링크 + 지점 선택만 유지

### 2.6 Streamlit → FastAPI 전환 (2026-03-22)

| 작업 | 상세 |
|------|------|
| **백업** | `_streamlit_backup/` — 13개 파일 + README |
| **제거** | `app.py`, `ui_tabs.py`, `auth.py`, `cafe/ui.py`, `events/ui.py`, `.streamlit/`, `Dockerfile`, `entrypoint.sh` |
| **정리** | `cafe/db.py`, `equipment/db.py`, `events/db.py` — `st.cache_data` 제거 |
| **정리** | `users.py` — `st.secrets` 참조 제거, 환경변수만 사용 |
| **Docker** | `docker-compose.yml` — Streamlit+portal 서비스 제거, api+frontend만 |
| **Portal** | `index.html` — 버전 선택 → FastAPI 단일 접속 |
| **의존성** | `requirements.txt` — streamlit/st-aggrid 제거, FastAPI 의존성 |

### 2.7 논문 DB 구축 (2026-03-22)

- `papers` 테이블 생성 (init_db.py + 실제 DB)
- API 라우터: `api/routers/papers.py`
  - CRUD: GET/POST/PATCH/DELETE `/papers`
  - 장비별: `GET /papers/by-device/{device_info_id}`
  - 시술별: `GET /papers/by-treatment/{treatment_id}`
  - 일괄 등록: `POST /papers/bulk` (외부 프로그램 연동용)
- Pydantic 모델: `PaperCreate`, `PaperUpdate`

---

## 3. DB 스키마 요약 (25개 테이블)

| 영역 | 테이블 | 역할 |
|------|--------|------|
| 장비 | `branches`, `categories`, `equipment` | 지점/카테고리/장비 목록 |
| 장비 | `device_info` | 시술/장비 정보 사전 (aliases, summary, mechanism) |
| 장비 | `sync_log` | 장비 동기화 로그 |
| 이벤트 | `evt_regions`, `evt_branches` | 지역/지점 (43개) |
| 이벤트 | `evt_periods` | 이벤트 기간 (격월) |
| 이벤트 | `evt_categories`, `evt_category_aliases` | 시술 카테고리 + 별명 매핑 |
| 이벤트 | `evt_treatments` | 시술 마스터 사전 (60+ 시드) |
| 이벤트 | `evt_items`, `evt_item_components` | 이벤트 상품 + 패키지 구성 |
| 이벤트 | `evt_ingestion_logs` | 이벤트 수집 로그 |
| 카페 | `cafe_periods`, `cafe_branch_periods` | 월별 기간 + 지점 메타 (담당자/작가) |
| 카페 | `cafe_articles` | 원고 (월 20건/지점) |
| 카페 | `cafe_comments` | 댓글/대댓글 (3슬롯) |
| 카페 | `cafe_feedbacks`, `cafe_status_log` | 피드백, 상태 이력 |
| 카페 | `cafe_sync_log` | 카페 동기화 로그 |
| 논문 | `papers` | 논문/연구자료 |
| 공통 | `users` | 사용자 계정 |

---

## 4. API 엔드포인트 (50+개)

| 영역 | 엔드포인트 | 설명 |
|------|-----------|------|
| 인증 | `POST /auth/login`, `GET /auth/me` | JWT HS256 |
| 사용자 | CRUD `/users` | 계정 관리 |
| 카페 | `GET /cafe/periods`, `/branches` | 기간/지점 |
| 카페 | `GET /cafe/branch-periods/{bpId}/articles` | 원고 목록 (body+comments JSON 포함) |
| 카페 | `PATCH /cafe/articles/{id}` | 원고 수정 |
| 카페 | `POST /cafe/articles/{id}/status` | 상태 변경 |
| 카페 | `PUT /cafe/articles/{id}/comments/{slot}` | 댓글 저장 |
| 카페 | `POST /cafe/sync` | 구글 시트 동기화 (timeout 180s) |
| 카페 | `GET /cafe/summary/{periodId}` | 대시보드 요약 |
| 카페 | `GET /cafe/equipment-context` | 장비→시술+이벤트 연동 |
| 장비 | `GET /equipment` | 장비 목록 (컬럼명 정규화) |
| 장비 | `GET /equipment/device-info` | 시술 사전 |
| 이벤트 | `GET /events` | 이벤트 목록 |
| 이벤트 | `GET /events/treatments` | 시술 사전 |
| 이벤트 | `GET /events/search` | 시술명 검색 |
| 논문 | `GET/POST /papers` | 논문 CRUD |
| 논문 | `POST /papers/bulk` | 일괄 등록 |
| 논문 | `GET /papers/by-device/{id}` | 장비별 논문 |
| 논문 | `GET /papers/by-treatment/{id}` | 시술별 논문 |
| 공통 | `GET /health`, `GET /dashboard` | 헬스체크, HOME 대시보드 |

---

## 5. 논문(papers) 테이블 상세

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | PK | 자동 증가 |
| `device_info_id` | FK → device_info | 관련 장비/시술 사전 연결 |
| `treatment_id` | FK → evt_treatments | 관련 시술 마스터 연결 |
| `doi` | TEXT | Digital Object Identifier |
| `title` | TEXT | 논문 제목 (원문) |
| `title_ko` | TEXT | 한국어 제목 |
| `authors` | TEXT | 저자 |
| `journal` | TEXT | 학술지명 |
| `pub_year` | INT | 출판 연도 |
| `abstract_summary` | TEXT | AI 요약 또는 직접 입력 |
| `key_findings` | TEXT | 핵심 발견 사항 |
| `keywords` | TEXT(JSON) | 키워드 배열 `["RF","리프팅"]` |
| `evidence_level` | INT(0~5) | 근거 수준 (5=메타분석, 1=전문가의견) |
| `study_type` | TEXT | RCT/코호트/메타분석 등 |
| `sample_size` | TEXT | 표본 크기 |
| `source_url` | TEXT | 원문 링크 |
| `source_file` | TEXT | 로컬 파일 경로 |
| `status` | TEXT | draft/reviewed/verified/deleted |

### 외부 연동 예시

```python
import requests

papers = [{
    "device_info_id": 5,
    "title": "HIFU for facial lifting: a meta-analysis",
    "title_ko": "안면 리프팅을 위한 HIFU: 메타분석",
    "authors": "Kim et al.",
    "journal": "J Dermatol Surg",
    "pub_year": 2024,
    "abstract_summary": "AI가 생성한 논문 요약...",
    "key_findings": "평균 30% 피부 탄력 개선",
    "keywords": '["HIFU", "울쎄라"]',
    "evidence_level": 5,
    "study_type": "메타분석",
    "status": "reviewed"
}]
requests.post("http://localhost:8000/papers/bulk", json=papers)
```

---

### 2.8 장비 매칭 로직 통합 (2026-03-22)

- **문제**: 장비 매칭 로직이 3곳에 분산 (각각 정밀도 다름)
- **해결**: `equipment/matcher.py` 공용 모듈 생성 (Single Source of Truth)

| 호출처 | Before | After |
|--------|--------|-------|
| `equipment/db.py` | 자체 4단계+한글체크 | `matcher.match_devices()` |
| `paper_analyzer.py` | 자체 3단계 (한글체크 없음) | `matcher.match_from_names()` |
| `cafe/db.py` | 단순 substring | `matcher.match_devices()` |

- 매칭 우선순위: 정확→순방향포함→역방향포함→aliases
- 한글 경계 체크: 울쎄라 ≠ 울쎄라피, 써마지 = 써마지FLX
- 검증: 3곳 모두 동일 장비 id 반환 확인

### 2.9 DB 파일 관리 기능 (2026-03-22)

- **관리자 모드 → 데이터 동기화** 탭에 DB 업로드/다운로드 추가
- `POST /equipment/db-upload`: 로컬 DB를 서버에 업로드 (자동 백업)
- `GET /equipment/db-download`: 서버 DB를 로컬에 다운로드 (백업용)
- 업로드 후 검증: 테이블 목록, device_info/papers 건수 표시
- NAS 담당자 없이 웹 브라우저에서 직접 DB 관리 가능

### 2.10 NAS Docker 배포 완료 (2026-03-22)

- Portainer Stack으로 GitHub → 자동 빌드 배포
- 포트포워딩: 외부:11973 → NAS:8080 (FastAPI+Vue)
- Streamlit 컨테이너 제거, FastAPI 단일 버전 운영
- **주의**: `users.py`에서 Streamlit 참조 제거 시 `invalidate_users_cache` 누락 → import 오류 해결

---

## 6. 미완료/보류 항목

| 항목 | 상태 | 우선순위 | 비고 |
|------|------|:--------:|------|
| **DB 업로드 테스트** | 미확인 | 🔴 | 관리자모드→데이터동기화→DB업로드로 로컬 DB 반영 |
| **논문↔블로그 연동** | 미구현 | 🟡 | paper_blog_links 테이블 + UI |
| **웹앱 논문 분석** | 미구현 | 🟡 | editor 이상 권한, PDF 업로드→Claude API 분석 |
| 대시보드 지점 클릭→원고목록 | 미구현 | 🟡 | CafeView subView + branch 연동 |
| 원고 작성 피드백 영역 확장 | 미구현 | 🟡 | 여백 최대 활용 |
| 블로그/플레이스/웹페이지 | placeholder | 🟢 | 콘텐츠 TBD |
| 보고서 탭 | placeholder | 🟢 | 콘텐츠 TBD |

---

## 7. 알려진 이슈 & 해결 이력

| 이슈 | 원인 | 해결 |
|------|------|------|
| 카페 동기화 프론트 타임아웃 | Axios 기본 30s < 42지점 소요시간 | cafe.ts timeout 180000 |
| 장비 필터 미작동 | DB `지점명` vs API `지점` 불일치 | equipment.py rename_map 정규화 |
| 원고 ◀▶ 네비 오류 | props.articleId 내부 갱신 안 됨 | currentId ref 독립 관리 |
| 담당자 "스마트 담당자" 표시 | 동기화 미실행 시 기본값 | 동기화 실행 필요 |
| 사진값 O vs 있음 | DB원본 "O" vs 화면 "있음" | equipment.py apply 정규화 |
| NAS 로그인 실패 (500) | users.py `st` 참조 잔존 | Streamlit 참조 완전 제거 |
| NAS 컨테이너 crash | `invalidate_users_cache` import 누락 | users.py에 함수 추가 |
| NAS DB 0건 | Docker Volume ≠ File Station 경로 | 웹앱 DB 업로드 기능으로 해결 |
| GitHub push 차단 | API 키 감지 (Secret Scanning) | .gitignore + git filter-branch |

---

## 8. 개발 환경

```bash
# 백엔드
cd uni-portal
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# 프론트엔드
cd frontend
npm install
npm run dev   # localhost:5173 → /api proxy → localhost:8000

# Docker 배포
docker-compose up --build
# api: :8000, frontend: :8080
```
