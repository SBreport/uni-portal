# 유앤아이의원 통합 관리 시스템 — 프로젝트 로드맵

> 최종 업데이트: 2026-04-03
> 관리자: smartbranding (jogons)
> 기술 스택: FastAPI + Vue 3 + SQLite (Streamlit 전환 완료)
> 현재 버전: v1.9

---

## 1. 프로젝트 개요

유앤아이의원(44개 지점) 통합 관리 시스템.
장비, 이벤트, 카페 마케팅, 블로그, 플레이스, 웹페이지, 시술 정보, 논문 분석을 하나의 플랫폼에서 관리.

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

## 2. 완료 상태 (v1.9 기준, 2026-04-03)

### ✅ 완료

| # | 기능 | 완료일 | 비고 |
|---|------|--------|------|
| 1 | SQLite DB 구축 + Google Sheets 이관 | 2026-02 | 장비/이벤트/카페 |
| 2 | FastAPI 백엔드 (50+ API) | 2026-03 | Streamlit → 단독 전환 |
| 3 | Vue.js 프론트엔드 SPA | 2026-03 | 로그인, 전체 탭 구성 |
| 4 | JWT 로그인 + 권한 관리 | 2026-03 | admin/editor/branch/viewer |
| 5 | 보유장비 탭 | 2026-03 | 필터, 상세패널, 시술연동, 논문연동 |
| 6 | 이벤트 탭 | 2026-03 | 필터, 가격검색, 비고 툴팁 |
| 7 | 시술정보 탭 (시술사전 + 시술논문) | 2026-03 | 시술사전 CRUD, 논문 열람 |
| 8 | 카페 마케팅 탭 — 침투 원고 | 2026-03 | 대시보드, 원고목록(V1/V2), 원고작성, 발행결과 |
| 9 | 마케팅 트리 메뉴 | 2026-03 | 카페/블로그/플레이스/웹페이지 구조 |
| 10 | 논문 분석 CLI | 2026-03 | Claude API, 자동매칭, Word/Excel 출력 |
| 11 | 논문 JSON/PDF 업로드 (웹) | 2026-03 | 중복 체크 포함 |
| 12 | Docker 배포 (NAS) | 2026-03 | Portainer Stack 관리 |
| 13 | Streamlit → FastAPI 완전 전환 | 2026-03 | `_streamlit_backup/`에 보존 |
| 14 | 블로그 탭 v1 | 2026-03 | 계정별 게시글 관리, 노션 API 연동 |
| 15 | 플레이스 대시보드 v1 | 2026-04 | 월별 상위노출 현황, 일별 히트맵 |
| 16 | 웹페이지 노출 대시보드 v1 | 2026-04 | 월별 노출 현황, 실행사 매핑, 총노출일/작업진행일 |

---

## 3. 고도화 로드맵 (v2.0)

### Phase A: 카페 마케팅 고도화

**현재 상태:** 카페침투 원고 작성/검토/진행상황 체크까지 완료

| # | 기능 | 우선순위 | 설명 |
|---|------|:-------:|------|
| A-1 | **댓글침투 관리** | 🔴 높음 | 다른 사람 게시글에 댓글로 바이럴하는 방식 기록/관리. 타겟 게시글 URL, 댓글 내용, 작성자, 작성일, 상태 추적 |
| A-2 | **발행 결과 추적** | 🔴 높음 | 카페침투 원고가 실제로 어디에 발행되었는지 기록 & 공유. 발행 카페명, URL, 발행일, 노출 상태 |
| A-3 | **침투 결과 대시보드** | 🟡 중간 | 카페침투 + 댓글침투 결과를 통합 집계. 지점별/월별 바이럴 성과 가시화 |

**카페 바이럴 2종류 정리:**
- 카페침투: 타겟 카페에 회원인 척 자연스럽게 원고(제목+게시글+댓글+대댓글) 발행 → 현재 구현 완료
- 댓글침투: 타인 게시글에 자연스러운 추천 댓글로 바이럴 → 신규 구현 필요

### Phase B: 블로그 고도화

**현재 상태:** 노션 API로 계정별 게시글 목록 조회 가능

| # | 기능 | 우선순위 | 설명 |
|---|------|:-------:|------|
| B-1 | **자동 일일 동기화** | 🔴 높음 | 하루 1회 자동으로 노션→DB 갱신 (cron/스케줄러) |
| B-2 | **논문↔블로그 연동** | 🟡 중간 | paper_blog_links 테이블 활용, 블로그 글에 참조 논문 연결 |

### Phase C: 시술정보 · 장비 크로스체크 강화

**현재 상태:** 시술정보 DB + 보유장비 각각 독립 동작, 기본 연동만 구현

| # | 기능 | 우선순위 | 설명 |
|---|------|:-------:|------|
| C-1 | **시술↔장비 양방향 연결** | 🔴 높음 | 시술 조회 시 해당 장비 정보, 장비 조회 시 적용 시술 목록 유기적 표시 |
| C-2 | **크로스체크 뷰** | 🟡 중간 | 특정 부위/시술 검색 → 관련 장비, 이벤트, 논문, 카페/블로그 콘텐츠 통합 조회 |
| C-3 | **데이터 정합성 검증** | 🟡 중간 | 장비↔시술 매핑이 올바르게 적용되었는지 자동 검증 리포트 |

### Phase D: 플레이스 · 웹페이지 고도화

**현재 상태:** 구글 시트 기반 월별 정보 조회 v1 완료

| # | 기능 | 우선순위 | 설명 |
|---|------|:-------:|------|
| D-1 | **일별 단위 추적** | 🔴 높음 | 월별이 아닌 일자 기준 카운트. 3→4월 전환 시에도 일별 데이터 연속 조회 가능 |
| D-2 | **실제 순위 수집** | 🟡 중간 | 네이버 키워드 검색 시 실제 노출 순위를 직접 수집 → DB 누적 (애드로그 API 등 별도 조사 예정) |
| D-3 | **구글시트 vs 실측 크로스체크** | 🟡 중간 | 기존 구글시트 데이터와 실측 순위 데이터 비교 대시보드 |

### Phase E: 민원 관리 (신규)

**현재 상태:** 미구현 (완전 신규 기능)

| # | 기능 | 우선순위 | 설명 |
|---|------|:-------:|------|
| E-1 | **민원 게시판** | 🔴 높음 | 게시판 형태. 지점별 민원 등록, 진행상황 추적 |
| E-2 | **역할별 뷰** | 🔴 높음 | 원장: 자기 지점 민원 확인 / 본사: 전 지점 민원 관리 / 대행사: 지점별 대응 현황 |
| E-3 | **민원 상태 워크플로** | 🟡 중간 | 접수→처리중→처리완료→종결 상태 이력 관리 |

### Phase F: 보고서 (최종 단계)

**현재 상태:** 미구현 (모든 기능 완료 후 진행)

| # | 기능 | 우선순위 | 설명 |
|---|------|:-------:|------|
| F-1 | **지점별 마케팅 보고서** | 🟡 | 카페/블로그/플레이스/웹페이지 마케팅 성과 통합 리포트 |
| F-2 | **지점 계정 전용 뷰** | 🟡 | 지점별 ID 배정 → 로그인 시 자기 지점 리포트만 열람 |
| F-3 | **HTML/PDF 다운로드** | 🟡 | 보고서를 HTML 또는 PDF로 내보내기 |

---

## 4. 구현 순서 (제안)

```
[Sprint 1] 기반 강화
  ├── B-1  블로그 자동 동기화 (cron)
  ├── D-1  플레이스/웹페이지 일별 추적
  └── C-1  시술↔장비 양방향 연결

[Sprint 2] 카페 확장 + 민원
  ├── A-1  댓글침투 관리
  ├── A-2  발행 결과 추적
  └── E-1  민원 게시판 + 역할별 뷰

[Sprint 3] 데이터 수집 + 크로스체크
  ├── D-2  실제 순위 수집 (API 연동)
  ├── D-3  구글시트 vs 실측 크로스체크
  ├── C-2  크로스체크 통합 뷰
  └── B-2  논문↔블로그 연동

[Sprint 4] 보고서 + 마무리
  ├── A-3  침투 결과 대시보드
  ├── E-3  민원 상태 워크플로 고도화
  ├── F-1  지점별 보고서
  ├── F-2  지점 전용 뷰
  └── F-3  HTML/PDF 다운로드
```

---

## 5. 팀 구성 (에이전트 기반)

### Opus (아키텍트 / 최종 결정권자)
- 전체 작업 계획 수립 및 우선순위 결정
- 각 Sonnet 에이전트에게 작업 지시 및 결과 검증
- 아키텍처 결정, 코드 리뷰, 충돌 해결
- Skill 기반 QA/리뷰 실행 (/autoplan, /review, /design-review)

### Sonnet 팀원 (기능별 병렬 작업)

| 팀원 | 담당 영역 | 주요 작업 |
|------|----------|----------|
| **Frontend** | Vue/TS UI | 뷰 컴포넌트, 대시보드, 반응형 레이아웃 |
| **Backend** | FastAPI/DB | API 엔드포인트, DB 스키마, 쿼리 최적화 |
| **Data/Sync** | 데이터 파이프라인 | Google Sheets 동기화, cron 자동화, 순위 수집 |
| **QA** | 테스트/검증 | 브라우저 QA, 버그 리포트, 성능 체크 |

### 작업 방식
1. Opus가 Sprint별 상세 태스크 분배
2. 각 Sonnet이 worktree에서 독립 작업
3. Opus가 결과 리뷰 후 머지
4. Sprint 완료 시 /qa + /design-review 실행

---

## 6. 권한 체계

| 역할 | 코드 | 할 수 있는 것 |
|------|------|-------------|
| 관리자 | admin | 전체 접근 + 사용자 관리 + 동기화 + 논문 폴더 분석 |
| 편집자 | editor | 원고 작성/수정 + 논문 JSON 업로드 + PDF 웹 분석 |
| 지점담당 | branch | 자기 지점 열람/수정 + 민원 등록 + 보고서 열람 |
| 열람자 | viewer | 열람만 가능 |

---

## 7. 시스템 구조도

```
uni-portal/
├── api/                          # FastAPI 백엔드
│   ├── main.py                   # 앱 진입점, CORS, 라우터 등록
│   ├── auth_jwt.py               # JWT 생성/검증
│   ├── deps.py                   # get_current_user, require_role
│   ├── models.py                 # Pydantic 스키마
│   └── routers/
│       ├── auth.py               # POST /login, GET /me
│       ├── users.py              # 사용자 CRUD
│       ├── cafe.py               # 카페 마케팅
│       ├── blog.py               # 블로그 관리
│       ├── equipment.py          # 보유장비
│       ├── events.py             # 이벤트
│       ├── papers.py             # 논문
│       ├── place.py              # 플레이스
│       └── webpage.py            # 웹페이지
│
├── frontend/                     # Vue 3 SPA
│   ├── src/
│   │   ├── views/                # 페이지 컴포넌트 (13개)
│   │   ├── components/           # 공통/탭별 컴포넌트
│   │   ├── stores/               # Pinia 상태관리
│   │   ├── api/                  # Axios API 클라이언트
│   │   └── router/               # Vue Router
│   └── vite.config.ts
│
├── cafe/db.py                    # 카페 DB 모듈
├── blog/                         # 블로그 모듈
├── equipment/                    # 장비 DB/동기화/매칭 모듈
├── events/                       # 이벤트 모듈
├── papers/                       # 논문 분석 모듈
├── place/                        # 플레이스 모듈
│
├── data/equipment.db             # SQLite 통합 DB
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.frontend
└── init_db.py                    # DB 스키마 초기화
```

---

## 8. 배포 정보

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

## 9. 문서 관리 체계

| 문서 | 역할 | 갱신 시점 |
|------|------|----------|
| **PROJECT_ROADMAP.md** | 전체 로드맵 + 진행 상태 | 기능 추가/완료 시 |
| **ARCHITECTURE.md** | 데이터 아키텍처 설계 | DB/구조 변경 시 |
| **WORK_LOG.md** | 작업 이력 (변경 사항 기록) | 매 작업 세션 종료 시 |
| **papers/SYSTEM.md** | 논문 분석 시스템 상세 | 논문 관련 변경 시 |

---

## 10. 핵심 참조 파일

| 용도 | 파일 |
|------|------|
| DB 스키마 | `init_db.py` |
| API 전체 목록 | `api/routers/*.py` 또는 `/api/docs` (Swagger) |
| 프론트엔드 라우팅 | `frontend/src/router/index.ts` |
| 사이드바 메뉴 | `frontend/src/components/common/AppSidebar.vue` |
| 논문 분석 프롬프트 | `papers/analyzer.py` → `ANALYSIS_PROMPT` |
| Docker 구성 | `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.frontend` |
