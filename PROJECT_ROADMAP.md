# 유앤아이의원 통합 관리 시스템 — 프로젝트 로드맵

> 최종 업데이트: 2026-03-22
> 관리자: smartbranding (jogons)
> 기술 스택: FastAPI + Vue 3 + SQLite (Streamlit 전환 완료)

---

## 1. 프로젝트 개요

유앤아이의원(44개 지점) 통합 관리 시스템.
장비, 이벤트, 카페 마케팅, 시술 정보, 논문 분석을 하나의 플랫폼에서 관리.

```
사용자 → NAS (Docker)
           ├── uni-api       (FastAPI :8000)   — 백엔드 API
           ├── uni-frontend  (Vue.js  :8080)   — 프론트엔드 SPA
           └── equipment.db                    — SQLite 단일 DB
```

### 기술 스택

| 계층 | 기술 | 비고 |
|------|------|------|
| 프론트엔드 | Vue 3 + TypeScript + Vite | Composition API, SPA |
| 상태관리 | Pinia | auth, cafe, equipment, events, papers |
| UI | Tailwind CSS 4.2 | 유틸리티 기반 |
| 백엔드 | FastAPI (Python) | JWT 인증, 50+ API |
| DB | SQLite (WAL 모드) | `data/equipment.db` 단일 파일 |
| 논문 분석 | Claude API + PyMuPDF | `papers/analyzer.py` CLI |
| 배포 | Docker + Portainer | Synology NAS |

---

## 2. 현재 완료 상태 (2026-03-22)

### ✅ 완료

| # | 기능 | 완료일 | 비고 |
|---|------|--------|------|
| 1 | SQLite DB 구축 + Google Sheets 이관 | 2026-02 | 장비/이벤트/카페 |
| 2 | FastAPI 백엔드 (50+ API) | 2026-03 | Streamlit 병행 → 단독 전환 |
| 3 | Vue.js 프론트엔드 SPA | 2026-03 | 로그인, 전체 탭 구성 |
| 4 | JWT 로그인 + 권한 관리 | 2026-03 | admin/editor/branch/viewer |
| 5 | 보유장비 탭 | 2026-03 | 필터, 상세패널, 시술연동, 논문연동 |
| 6 | 이벤트 탭 | 2026-03 | 필터, 가격검색, 비고 툴팁 |
| 7 | 시술정보 탭 (시술사전 + 시술논문) | 2026-03 | 시술사전 CRUD, 논문 열람 |
| 8 | 카페 마케팅 탭 | 2026-03 | 대시보드, 원고목록(V1/V2), 원고작성, 발행결과 |
| 9 | 마케팅 트리 메뉴 | 2026-03 | 카페/블로그/플레이스/웹페이지 구조 |
| 10 | 논문 분석 CLI (papers/analyzer.py) | 2026-03 | Claude API, 자동매칭, Word/Excel 출력 |
| 11 | 논문 JSON 업로드 (웹) | 2026-03 | 중복 체크 포함 |
| 12 | 논문 폴더 분석 (관리자 모드) | 2026-03 | 웹에서 로컬 폴더 지정 → 분석 |
| 13 | Docker 배포 (NAS) | 2026-03 | Portainer Stack 관리 |
| 14 | Streamlit → FastAPI 완전 전환 | 2026-03 | `_streamlit_backup/`에 보존 |

### 🔧 진행 중

| # | 기능 | 상태 | 비고 |
|---|------|------|------|
| 15 | 카페 대시보드 고도화 | 진행 중 | 담당자/작가 매칭 이슈 |
| 16 | 논문 대량 처리 | 대기 | 394건 PDF, 폴더별 순차 처리 예정 |

### ❌ 미구현

| # | 기능 | 우선순위 | 설명 |
|---|------|---------|------|
| 17 | **PDF 웹 분석 (editor용)** | 높음 | 웹에서 PDF 1~2건 직접 업로드 → AI 분석 |
| 18 | **블로그 탭** | 높음 | 블로그 게시글 관리 + 논문 연동 |
| 19 | **논문↔블로그 연동** | 높음 | paper_blog_links 테이블 준비 완료, UI 미구현 |
| 20 | **보고서 탭** | 중간 | 플레이스홀더 상태 |
| 21 | **플레이스 탭** | 낮음 | 플레이스홀더 상태 |
| 22 | **웹페이지 탭** | 낮음 | 플레이스홀더 상태 |
| 23 | **파일 구조 최적화** | 중간 | Streamlit 잔여 파일 정리, api/ 구조 개선 |
| 24 | **자동 일일 동기화** | 낮음 | 현재 수동만 가능 (관리자 모드) |
| 25 | **카페 동기화 안정화** | 중간 | gspread 인증/타임아웃 이슈 |

---

## 3. 시스템 구조도

```
uni-portal/
├── api/                          # FastAPI 백엔드
│   ├── main.py                   # 앱 진입점, CORS, 라우터 등록
│   ├── auth_jwt.py               # JWT 생성/검증
│   ├── deps.py                   # get_current_user, require_role
│   ├── models.py                 # Pydantic 스키마
│   ├── requirements.txt          # API 전용 의존성
│   └── routers/
│       ├── auth.py               # POST /login, GET /me
│       ├── users.py              # 사용자 CRUD
│       ├── cafe.py               # 카페 마케팅 17개
│       ├── equipment.py          # 보유장비 10개
│       ├── events.py             # 이벤트 12개
│       └── papers.py             # 논문 10개+
│
├── frontend/                     # Vue 3 SPA
│   ├── src/
│   │   ├── views/                # 페이지 컴포넌트
│   │   ├── components/           # 공통/탭별 컴포넌트
│   │   ├── stores/               # Pinia 상태관리
│   │   ├── api/                  # Axios API 클라이언트
│   │   └── router/               # Vue Router
│   └── vite.config.ts
│
├── cafe/db.py                    # 카페 DB 모듈 (공유)
├── equipment/db.py               # 장비 DB 모듈 (공유)
├── events/db.py                  # 이벤트 DB 모듈 (공유)
├── users.py                      # 사용자 관리 (공유)
├── papers/analyzer.py             # 논문 분석 CLI
│
├── data/equipment.db             # SQLite 통합 DB
├── paper_results/                # 분석 결과 출력
├── _streamlit_backup/            # Streamlit 백업
│
├── docker-compose.yml            # api + frontend
├── Dockerfile.api
├── Dockerfile.frontend
└── init_db.py                    # DB 스키마 초기화
```

---

## 4. 권한 체계

| 역할 | 코드 | 할 수 있는 것 |
|------|------|-------------|
| 관리자 | admin | 전체 접근 + 사용자 관리 + 동기화 + 논문 폴더 분석 |
| 편집자 | editor | 원고 작성/수정 + 논문 JSON 업로드 + PDF 웹 분석 |
| 지점담당 | branch | 자기 지점 열람/수정 |
| 열람자 | viewer | 열람만 가능 |

---

## 5. 다음 단계 로드맵

### Phase 5: 논문 + 블로그 연동 (다음 우선)

```
① PDF 웹 분석 (editor용) — 시술논문 탭에서 PDF 업로드 → AI 분석
② 논문 대량 처리 — 로컬에서 394건 폴더별 순차 분석
③ 블로그 탭 구현 — 게시글 관리 시스템
④ 논문↔블로그 연동 — paper_blog_links 테이블 활용
```

### Phase 6: 보고서 + 마케팅 확장

```
⑤ 보고서 탭 — 지점별/월별 종합 리포트
⑥ 플레이스 탭 — 네이버 플레이스 관리
⑦ 웹페이지 탭 — 홈페이지 관리
```

### Phase 7: 운영 안정화

```
⑧ 파일 구조 최적화 — Streamlit 잔여 정리, 모듈 구조 개선
⑨ 자동 일일 동기화 — cron/스케줄러 기반
⑩ 카페 동기화 안정화 — 인증/타임아웃 이슈 해결
```

---

## 6. 문서 관리 체계

### 문서 목록 및 역할

| 문서 | 역할 | 갱신 시점 |
|------|------|----------|
| **PROJECT_ROADMAP.md** | 전체 로드맵 + 진행 상태 | 기능 추가/완료 시 |
| **docs/HANDOVER.md** | 인수인계용 (구조, API, DB, 운영 매뉴얼) | 신규 기능 배포 시 |
| **papers/SYSTEM.md** | 논문 분석 시스템 상세 | 논문 관련 변경 시 |
| **WORK_LOG.md** | 작업 이력 (변경 사항 기록) | 매 작업 세션 종료 시 |

### 폐기/통합 대상

| 문서 | 처리 |
|------|------|
| `equipment/GUIDE.md` | → docs/HANDOVER.md에 통합 또는 삭제 검토 |
| `_temp/PAPER_ANALYSIS_GUIDE.md (deprecated)` | → papers/SYSTEM.md + docs/HANDOVER.md 11장에 통합됨 |

### 문서 갱신 규칙

```
1. 새 기능 구현 완료 시:
   → PROJECT_ROADMAP.md: "미구현" → "완료"로 이동, 완료일 기입
   → docs/HANDOVER.md: 해당 섹션 업데이트
   → WORK_LOG.md: 작업 내용 기록

2. 새 세션 시작 시:
   → PROJECT_ROADMAP.md 먼저 읽고 현재 상태 파악
   → WORK_LOG.md 최근 항목 확인

3. 인수인계 시:
   → docs/HANDOVER.md를 주 문서로 전달
   → PROJECT_ROADMAP.md로 전체 진행 상태 파악
   → papers/SYSTEM.md는 논문 관련 작업 시에만 참조

4. 관리자 변경 시:
   → 이 문서(PROJECT_ROADMAP.md)의 "관리자" 항목 갱신
   → docs/HANDOVER.md의 접속 정보/인증 정보 확인

5. 분기별 프로젝트 점검 시 (아래 체크리스트 실행):
   → 죽은 코드, 불필요 파일, 보안 점검
   → 점검 결과를 WORK_LOG.md에 기록
```

### 분기별 점검 체크리스트

> 마지막 점검: 2026-03-22

```
[ 코드 위생 ]
□ 사용하지 않는 Vue 컴포넌트 확인 (import 없는 .vue 파일)
□ 사이드바/라우터에 없는 뷰 파일 확인
□ 사용하지 않는 Pinia store / API 클라이언트 확인
□ 빈 placeholder 뷰 목록 갱신 (구현 예정 여부 확인)

[ 파일 구조 ]
□ 루트 레벨 .py 파일 정리 (1회성 스크립트 → _legacy/ 이동)
□ _streamlit_backup/, _legacy/ 폴더 필요 여부 확인
□ paper_results/ 오래된 결과 파일 정리
□ __pycache__/ 정리

[ 보안 ]
□ credentials.json이 .gitignore에 포함되어 있는지 확인
□ .env, settings.local.json이 Git에 추적되지 않는지 확인
□ API Key가 코드에 하드코딩되어 있지 않은지 확인
□ GitHub Secret Scanning 알림 없는지 확인

[ 문서 ]
□ PROJECT_ROADMAP.md 진행 상태 최신인지 확인
□ docs/HANDOVER.md 신규 기능 반영되었는지 확인
□ WORK_LOG.md 최근 작업 기록되었는지 확인
□ 폐기 대상 문서 정리

[ 배포 ]
□ Docker 이미지 빌드 정상 여부
□ NAS 볼륨(DB) 백업 상태
□ requirements.txt와 api/requirements.txt 동기화 확인
```

### 2026-03-22 점검 결과

| 항목 | 결과 | 조치 |
|------|------|------|
| ArticleList.vue | 죽은 코드 | **삭제** |
| DictionaryView.vue | 사이드바/라우터 미등록 | **삭제** |
| portal/ | Streamlit 제거 후 미사용 | **_legacy/ 이동** |
| migrate_branch_name.py | 1회성 완료 | **_legacy/ 이동** |
| credentials.json | .gitignore 확인 | ✅ 정상 |
| 코드 내 API Key | 없음 | ✅ 정상 |

---

## 7. 배포 정보

| 항목 | 값 |
|------|-----|
| NAS | Synology (Docker + Portainer) |
| 외부 접속 | `smartbranding.synology.me:8080` |
| Stack 이름 | `uni-portal` |
| Git | `github.com/SBreport/uni-portal` (private) |
| DB 볼륨 | `uni-portal_portal-data` |
| 배포 방법 | Portainer → Stack → Pull and redeploy |

### 배포 절차

```
1. 로컬에서 코드 수정 + 테스트
2. git push origin main
3. Portainer → Stacks → uni-portal → Pull and redeploy
4. Containers에서 uni-api, uni-frontend 상태 확인
5. 브라우저에서 접속 테스트
```

---

## 8. 핵심 참조 파일

| 용도 | 파일 |
|------|------|
| DB 스키마 | `init_db.py` |
| API 전체 목록 | `api/routers/*.py` 또는 `/api/docs` (Swagger) |
| 프론트엔드 라우팅 | `frontend/src/router/index.ts` |
| 사이드바 메뉴 | `frontend/src/components/common/AppSidebar.vue` |
| 논문 분석 프롬프트 | `papers/analyzer.py` → `ANALYSIS_PROMPT` |
| Docker 구성 | `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.frontend` |
