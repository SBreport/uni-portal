> 현재 구현된 실제 상태를 기록한 문서입니다.

# 프로젝트 구조 개요

유앤아이의원(피부과 다지점) 내부 통합 관리 시스템. 마케팅 원고, 플레이스 순위, 논문 분석, 이벤트, 민원 등을 한 포털에서 관리한다.

**기술스택**: Vue3 + Vite + Pinia + Tailwind4 / FastAPI + SQLite / Google Sheets 연동  
**배포**: Synology NAS + Docker + Portainer

---

## 폴더 구조 (루트 1-depth)

| 폴더 | 역할 |
|------|------|
| `api/` | FastAPI 백엔드 — 라우터, JWT 인증, 스케줄러 |
| `frontend/` | Vue3 SPA — views, components, stores, router |
| `data/` | SQLite DB 4개 (equipment.db가 메인) |
| `blog/` | 블로그 도메인 — Sheets 동기화, 노션 연동, DB CRUD |
| `cafe/` | 카페 마케팅 원고 관리 |
| `place/` | 네이버 플레이스 상위노출 추적 |
| `webpage/` | 웹페이지 노출 추적 |
| `equipment/` | 보유장비 + 시술사전 |
| `events/` | 이벤트 수집·파싱·정규화 |
| `papers/` | 논문 분석 시스템 (Claude API 기반) |
| `treatment/` | 시술 카탈로그 |
| `complaints/` | 민원 관리 |
| `shared/` | 공통 DB 연결 (`get_conn`, DB 경로 상수) |
| `scripts/` | 유지보수 스크립트 (실사용 5개) |
| `checker/`, `SB_CHECKER/` | 플레이스 순위 외부 검증 모듈 |
| `normalization/` | 시술 카테고리 정규화 규칙 |
| `docs/` | 프로젝트 문서 (+ `_archive/`) |
| `_temp/` | 아카이브 — 미사용 코드·레거시 백업 |

---

## 도메인 모듈의 3-레이어 패턴

각 도메인(blog, cafe, place, webpage, equipment, events)은 동일한 구조를 따른다.

```
<domain>/
  sheets.py        — Google Sheets 읽기
  sync_to_db.py    — 시트 → SQLite 동기화
  db.py            — SQLite CRUD
```

해당 도메인의 API 라우터는 `api/routers/<domain>.py`에 위치한다.

---

## 데이터베이스

`shared/db.py`에 경로 상수(EQUIPMENT_DB, CAFE_DB, BLOG_DB, SYSTEM_DB) 정의.  
WAL 모드, busy_timeout 30초. 총 42개 테이블.

| 파일 | 크기 | 주요 내용 |
|------|------|-----------|
| `equipment.db` | 34MB | 장비, 이벤트, 사용자, 블로그, 논문, 민원, 플레이스·웹페이지 일별, 시술 등 대부분 |
| `cafe.db` | 836KB | 카페 마케팅 원고 |
| `blog.db` | 24KB | 블로그 포스트 + 계정 |
| `system.db` | 12KB | 시스템 설정, 순위체크 로그 |

---

## 프론트엔드 화면

| 경로 | 파일 | 기능 |
|------|------|------|
| `/login` | LoginView.vue | JWT 로그인 |
| `/` | HomeView.vue | 대시보드 (진행률·요약) |
| `/explorer` | ExplorerView.vue | 통합 검색/필터 |
| `/info` | InfoView.vue | 의료 정보 관리 |
| `/branch-info` | BranchInfoView.vue | 지점 정보 조회 |
| `/cafe` | CafeView.vue | 카페 마케팅 원고 |
| `/blog`, `/blog-all` | BlogView.vue | 블로그 (유앤아이/전체) |
| `/place` | PlaceView.vue | 플레이스 상위노출 |
| `/webpage` | WebpageView.vue | 웹페이지 노출 |
| `/equipment` | EquipmentView.vue | 보유장비 |
| `/events` | EventsView.vue | 이벤트 |
| `/papers` | PapersView.vue | 논문 |
| `/treatment-info` | TreatmentInfoView.vue | 시술 카탈로그 |
| `/complaints` | ComplaintsView.vue | 민원 |
| `/reports` | ReportsView.vue | 보고서 |
| `/admin` | AdminView.vue | 관리자 |

### 사이드바 메뉴 구조

```
HOME (/)
탐색기 (/explorer)
정보관리 (/info)
마케팅 [트리]
 ├─ 카페
 ├─ 블로그
 ├─ 블로그(all) — admin 전용
 ├─ 플레이스
 └─ 웹페이지
민원관리
─────────
보고서
관리자 모드 — admin 전용
```

---

## 역할 체계

```python
ROLE_HIERARCHY = {"viewer": 0, "branch": 1, "editor": 2, "admin": 3}
```

`viewer` + `branch_id` 유무에 따라 `viewer-branch` / `viewer-hq`로 분리.  
세부 권한 태그(permission): `cafe_write`, `cafe_publish` 등.

---

## API 엔드포인트 요약

`api/routers/` 내 18개 라우터, 총 약 191개 엔드포인트.

| 라우터 | 엔드포인트 수 |
|--------|--------------|
| blog | 22 |
| cafe | 17 |
| equipment | 17 |
| events | 15 |
| papers | 15 |
| encyclopedia | 13 |
| treatment_catalog | 12 |
| rank_checker | 9 |
| place | 10 |
| webpage | 10 |
| config | 7 |
| complaints | 7 |
| explorer | 7 |
| users | 4 |
| auth | 2 |
| branch_info | 3 |
| branches | 1 |
| reports | 3 |

---

## Google Sheets 연동

- 인증: 프로젝트 루트 `credentials.json` (서비스 계정)
- 시트 ID: 환경변수 `EVENT_SHEET_ID`, `CAFE_SHEET_ID` 등으로 관리
- 각 도메인 `sheets.py`에서 gspread 라이브러리로 읽어 DB에 동기화

---

> 이 문서는 현재 상태의 스냅샷입니다. 도메인 추가·삭제 등 큰 구조 변경 시 갱신이 필요합니다.  
> 최종 갱신일: 2026-04-17
