# 유앤아이의원 통합 관리 시스템 — 프로젝트 로드맵

> 최종 수정: 2026-03-12
> 목적: 유앤아이의원 전 지점의 장비, 시술 이벤트, 그리고 향후 추가될 데이터를
> 하나의 NAS 서버에서 통합 관리하는 시스템 구축

---

## 1. 한눈에 보는 전체 구조도

```
┌───────────────────────────────────────────────┐
│            Synology NAS (Docker)               │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │     uni-portal (통합 앱) :8501          │  │
│  │                                         │  │
│  │  [장비관리] [이벤트] [카페마케팅] [대시보드] │  │
│  │                                         │  │
│  │  ┌───────────────────────────────────┐  │  │
│  │  │         equipment.db              │  │  │
│  │  │  branches | equipment | events    │  │  │
│  │  │  manuscripts | users | sync_log   │  │  │
│  │  └───────────────────────────────────┘  │  │
│  └─────────────────────────────────────────┘  │
│                                               │
└───────────────────────────────────────────────┘
          ↑
    사용자 접속 (하나의 URL)
    http://NAS_IP:8501
```

---

## 2. 초보자를 위한 쉬운 설명

### 이 프로젝트가 뭔가요?

유앤아이의원은 전국에 44개 지점이 있습니다.
각 지점마다 보유한 장비(레이저, 리프팅 기기 등)가 다릅니다.
이걸 엑셀(Google Sheets)로 관리하고 있었는데, 느리고 불안정해서
**자체 서버(NAS)**에서 돌아가는 **웹 프로그램**으로 바꾸는 프로젝트입니다.

### 비유로 이해하기

```
기존 방식 (Google Sheets):
  종이 장부 44권을 매번 꺼내서 합치는 것
  → 느리고, 누가 실수로 지울 수 있음

새로운 방식 (NAS + DB):
  하나의 전산 시스템에 모두 입력
  → 빠르고, 실수로 지울 수 없음
  → 검색, 통계, 비교가 즉시 가능
```

### 핵심 기술 스택

| 기술 | 역할 | 쉬운 비유 |
|---|---|---|
| **Python** | 프로그래밍 언어 | 프로그램을 만드는 도구 |
| **Streamlit** | 웹 화면을 만드는 도구 | 웹페이지 디자인 틀 |
| **SQLite** | 데이터베이스 | 엑셀 대신 쓰는 전자 장부 |
| **Docker** | 프로그램 포장 도구 | 택배 상자 (어디서든 실행 가능) |
| **NAS** | 회사 자체 서버 | 사무실에 있는 컴퓨터 서버 |

### 폴더 구조 설명

```
C:\LocalGD\7_CODE\uni-equipment\
│
├── publish/              ★ 배포용 코드 (실제 서비스되는 코드)
│   ├── app.py            → 메인 화면 (CSS, 사이드바, 탭 구성)
│   ├── ui_tabs.py        → 각 탭의 내용 (장비목록, 검색, 대시보드 등)
│   ├── data.py           → 데이터 불러오기/필터링
│   ├── sheets.py         → Google Sheets 연동 (추후 DB로 교체)
│   ├── config.py         → 설정값 (역할, 브랜딩)
│   ├── auth.py           → 로그인/권한 관리
│   ├── users.py          → 사용자 CRUD
│   ├── branch_sources.json → 지점별 데이터 소스 목록
│   └── requirements.txt  → 필요한 Python 패키지 목록
│
├── internal/             ★ 개발용 코드 (테스트, 디버그)
│   ├── app.py            → 개발 버전 앱
│   ├── test_*.py         → 각종 테스트 스크립트
│   ├── debug_*.py        → 디버그용 스크립트
│   └── credentials.json  → Google 인증 파일 (비공개!)
│
├── docs/                 ★ 문서/참고자료
│   └── (3) raw 시트 갱신 버튼.txt  → Google Apps Script
│
└── PROJECT_ROADMAP.md    ★ 이 파일 (전체 로드맵)
```

---

## 3. 프로젝트 목록

### 프로젝트 A: 장비 관리 시스템 (uni-equipment)

> **상태: Phase 1 완료 (Google Sheets 기반), Phase 2 예정 (DB 전환)**

**하는 일:**
- 44개 지점의 보유 장비 목록 조회
- 장비 사진 보유 여부 관리 (체크박스)
- 지점별/카테고리별 통계 대시보드
- 지점 간 장비 비교

**현재 데이터 흐름:**
```
Google Sheets (44개 지점 시트)
        ↓ API 호출
  Streamlit Cloud (publish/ 코드)
        ↓ 웹 브라우저
     사용자 화면
```

**목표 데이터 흐름:**
```
SQLite DB (NAS 내부)
        ↓ 직접 조회
  Streamlit (NAS Docker)
        ↓ 웹 브라우저
     사용자 화면
```

**DB 테이블 설계:**
```sql
-- 지점 테이블
CREATE TABLE branches (
    id          INTEGER PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,    -- '강남점', '대구점' 등
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 카테고리 테이블
CREATE TABLE categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT UNIQUE NOT NULL           -- '리프팅', '색소', '주사 시술' 등
);

-- 장비 테이블 (핵심)
CREATE TABLE equipment (
    id            INTEGER PRIMARY KEY,
    branch_id     INTEGER REFERENCES branches(id),
    category_id   INTEGER REFERENCES categories(id),
    name          TEXT NOT NULL,          -- '울쎄라피 프라임'
    quantity      INTEGER DEFAULT 1,
    photo_status  BOOLEAN DEFAULT FALSE,  -- 사진 보유 여부
    note          TEXT,                   -- 비고
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 사용자 테이블
CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role          TEXT DEFAULT 'viewer',  -- viewer, editor, admin
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 프로젝트 B: 시술 이벤트 시스템 (uni-events)

> **상태: 초기 개발 (ingestion/parser 구현됨)**

**하는 일:**
- 각 지점의 시술 이벤트 정보 수집
- 시술명, 가격, 이벤트 기간 정규화
- 지점별 이벤트 현황 대시보드

**기존 코드 위치:** `바탕화면/claude code/uni-events/`

**기존 코드 구성:**
```
uni-events/
├── ingestion/          → 데이터 수집 (Google Sheets 읽기, 파싱)
│   ├── sheet_reader.py → 시트에서 데이터 읽기
│   ├── parser.py       → 텍스트 파싱
│   ├── price_parser.py → 가격 정보 추출
│   ├── normalizer.py   → 시술명 정규화
│   └── validators.py   → 데이터 검증
├── normalization/      → 정규화 규칙 (JSON)
├── api/                → FastAPI 서버
├── database/           → DB 마이그레이션
├── scripts/            → 실행 스크립트
└── tests/              → 테스트 코드
```

**DB 테이블 설계:**
```sql
-- 시술 테이블
CREATE TABLE treatments (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,              -- '울쎄라', '피코슈어' 등
    category  TEXT,                       -- '리프팅', '색소' 등
    UNIQUE(name, category)
);

-- 이벤트 테이블
CREATE TABLE events (
    id            INTEGER PRIMARY KEY,
    branch_id     INTEGER NOT NULL,       -- 지점 ID (branches 테이블 참조)
    treatment_id  INTEGER REFERENCES treatments(id),
    original_price  INTEGER,              -- 정가
    event_price     INTEGER,              -- 이벤트가
    discount_rate   REAL,                 -- 할인율
    start_date      DATE,                 -- 시작일
    end_date        DATE,                 -- 종료일
    source_url      TEXT,                 -- 출처
    collected_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 프로젝트 C: 카페마케팅 원고 관리 (uni-cafe-marketing)

> **상태: 기획 단계**

**하는 일:**
- 지점별 월간 카페마케팅 원고 발행 현황 관리
- 원고 작성 상태 추적 (작성중/검토중/발행완료)
- 보유 장비 데이터와 연동하여 원고 대상 자동 매칭

**현재:** Google Sheets에서 별도 시트로 관리 중 (보유장비 시트와 연동)

**DB 테이블 설계:**
```sql
-- 원고 테이블
CREATE TABLE manuscripts (
    id            INTEGER PRIMARY KEY,
    branch_id     INTEGER REFERENCES branches(id),
    equipment_id  INTEGER REFERENCES equipment(id),  -- 관련 장비 연결
    title         TEXT NOT NULL,              -- '3월 울쎄라 이벤트 원고'
    month         TEXT NOT NULL,              -- '2026-03'
    status        TEXT DEFAULT 'draft',       -- draft, review, published
    report_status TEXT,                       -- 보고서 상태
    note          TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**연동 예시:**
```
강남점 프로필:
  보유 장비: 울쎄라 프라임, 인모드 ...     ← uni-equipment DB
  진행 이벤트: 울쎄라 30% 할인             ← uni-events DB
  카페마케팅 원고: 3월 울쎄라 원고 → 발행완료   ← uni-cafe-marketing
```

---

### 통합 앱 구조 (uni-portal)

> **상태: 기본 골격 완성 — 장비 관리 탭 구현 완료, 이벤트/카페마케팅 탭 placeholder**

**아키텍처 결정: 멀티 컨테이너 → 통합 앱**
- 별도 포트/페이지가 아닌 **하나의 앱, 하나의 DB, 하나의 URL**
- 탭으로 기능 분리: [장비관리] [이벤트] [카페마케팅] [대시보드] [가이드]
- 기능 추가 시 DB 테이블 + 탭 렌더링 함수만 추가하면 됨

**하는 일:**
- 장비 + 이벤트 + 카페마케팅 원고 데이터를 한 화면에서 조회
- 지점 프로필 (장비 현황 + 이벤트 현황 + 원고 현황)
- 장비-시술-원고 연관 분석
- 지점별 로그인/권한 관리 (지점 담당자는 자기 지점만 열람/수정)

**로그인 권한 구조:**
```
관리자 (admin)     → 전체 지점 열람/수정, 사용자 관리, 통계
지점담당자 (branch) → 자기 지점만 열람/수정, 장비 추가 가능
열람자 (viewer)    → 열람만 가능, 수정 불가
```

**통합 쿼리 예시:**
```sql
-- "울쎄라 보유 지점의 이벤트 + 원고 현황"
SELECT
    b.name AS 지점명,
    eq.name AS 장비명,
    ev.event_price AS 이벤트가,
    m.title AS 원고제목,
    m.status AS 원고상태
FROM branches b
JOIN equipment eq ON b.id = eq.branch_id
LEFT JOIN events ev ON b.id = ev.branch_id
LEFT JOIN manuscripts m ON eq.id = m.equipment_id
WHERE eq.name LIKE '%울쎄라%';
```

---

## 4. 새로운 기능을 추가하고 싶을 때 (확장 가이드)

통합 앱 구조이므로 새 기능 추가는 간단합니다:

### 예시: "지점별 매출 관리"를 추가한다면?

**Step 1: DB 테이블 추가 (init_db.py에 추가)**
```sql
CREATE TABLE sales (
    id          INTEGER PRIMARY KEY,
    branch_id   INTEGER NOT NULL,       -- ★ branches 공통 키
    month       TEXT NOT NULL,           -- '2026-03'
    revenue     INTEGER,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Step 2: 탭 렌더링 함수 추가 (ui_tabs.py)**
```python
def render_tab_sales():
    st.subheader("매출 관리")
    # ... 매출 관련 UI 구현
```

**Step 3: 탭 등록 (app.py)**
```python
tab_names = ["장비 관리", "이벤트", "카페마케팅", "매출 관리", ...]
```

**Step 4: 컨테이너 재시작**
```bash
docker-compose restart uni-portal
```

**핵심 규칙:**
```
┌─────────────────────────────────────────────────┐
│  새 기능을 추가할 때 반드시 지켜야 할 것:       │
│                                                 │
│  1. branches 테이블의 지점명을 공통 키로 사용    │
│  2. 같은 DB(equipment.db)에 테이블 추가         │
│  3. ui_tabs.py에 렌더링 함수 추가               │
│  4. app.py에 탭 등록                            │
│  5. 컨테이너 재시작으로 반영                    │
└─────────────────────────────────────────────────┘
```

---

## 5. 단계별 로드맵

```
[1단계] 장비 관리 DB화 + NAS 배포           ← 지금 시작
  ① SQLite DB 생성 + Google Sheets 데이터 이관
  ② 앱 코드 DB 기반 전환 (빠른 조회)
  ③ 앱에서 장비 추가/수정 기능 (CRUD)
  ④ 하루 1회 자동 동기화 (Sheets → DB, 신규 행만 추가)
  ⑤ Dockerfile + NAS 배포

[2단계] 로그인/권한 + 지점 오픈
  ⑥ 로그인 기능 (ID/PW)
  ⑦ 지점별 권한 (내 지점만 보기/수정)
  ⑧ 지점 담당자에게 사이트 주소 공유

[3단계] 시술 이벤트 연동
  ⑨ 이벤트 DB 설계 + 수집 모듈 정비
  ⑩ 이벤트 대시보드 + 장비 연동

[4단계] 카페마케팅 원고 연동
  ⑪ 원고 DB 테이블 추가 + 기존 시트 데이터 이관
  ⑫ 카페마케팅 탭 구현 + 장비/이벤트 자동 매칭

[최종] 통합 완성
  ⑬ 지점 프로필 (장비+이벤트+카페마케팅 한 화면)
  ⑭ Google Sheets 의존 종료 (선택적 내보내기만 유지)
```

### Google Sheets 전환 전략

```
1단계: Sheets = 입력 창구 (유지),  DB = 조회용
       본사가 먼저 새 시스템 사용, 지점은 변화 없음

2단계: Sheets = 입력 창구 (유지),  DB = 입력+조회
       지점 담당자도 새 시스템에서 직접 입력 가능

3~4단계: Sheets = 백업/열람용,     DB = 원본
         모든 입력이 새 시스템에서 이루어짐

최종:   Sheets = 선택적 내보내기만, DB = 완전한 원본
```

### 동기화 규칙 (데이터 안전)

```
매일 1회 자동 동기화 시:

  1. DB 자동 백업 (equipment_YYYY-MM-DD.db)
  2. Sheets의 각 행을 확인:
     ├── DB에 없는 행 → 새로 추가 ✅
     ├── DB에 있고 내용 동일 → 스킵 ⏭️
     └── DB에 있고 내용 다름 → 로그만 남김 📝 (덮어쓰지 않음)
  3. DB에만 있는 행 (내부에서 추가한 것) → 유지 ✅
  4. 결과 리포트: "추가 N건 / 스킵 N건 / 충돌 N건"

핵심: "절대 덮어쓰지 않는다" → 충돌은 로그로 남기고 사람이 판단
```

### 각 단계 상세

| 단계 | 작업 | 선행 조건 |
|---|---|---|
| ① DB 생성 | SQLite 스키마 + 데이터 이관 스크립트 | 없음 (바로 가능) |
| ② 앱 전환 | sheets.py → db.py 교체 | ① 완료 |
| ③ CRUD | 앱에서 장비 추가/수정/삭제 | ② 완료 |
| ④ 자동 동기화 | Sheets → DB 하루 1회 | ② 완료 |
| ⑤ NAS 배포 | Dockerfile + compose + 배포 | ③④ 완료 |
| ⑥ 로그인 | ID/PW 인증 시스템 | ⑤ 완료 |
| ⑦ 지점 권한 | 사용자별 소속 지점 필터링 | ⑥ 완료 |
| ⑧ 지점 오픈 | 담당자에게 접속 정보 전달 | ⑦ 완료 |
| ⑨~⑩ 이벤트 | 이벤트 DB 테이블 + 이벤트 탭 구현 | ⑤ 완료 |
| ⑪~⑫ 카페마케팅 | 원고 DB 테이블 + 카페마케팅 탭 구현 | ⑩ 완료 |
| ⑬~⑭ 통합 완성 | 지점 프로필 + Sheets 의존 종료 | 모두 완료 |

---

## 6. NAS 배포 구성

### docker-compose.yml (통합 앱 — 단일 컨테이너)

```yaml
version: "3.8"

services:
  uni-portal:
    build: .
    container_name: uni-portal
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
    restart: always
    mem_limit: 512m
    environment:
      - TZ=Asia/Seoul
```

하나의 컨테이너에서 장비/이벤트/카페마케팅을 모두 서비스.
기능 추가 시 DB 테이블 + 탭 렌더링 함수만 추가하면 됨.

### NAS 폴더 구조

```
/nas/uni-portal/                  ← NAS 공유폴더
├── docker-compose.yml
├── Dockerfile
├── entrypoint.sh
├── app.py                        ← 메인 앱 (탭 라우팅)
├── ui_tabs.py                    ← 탭 렌더링 함수들
├── db.py                         ← SQLite 읽기/쓰기
├── init_db.py                    ← DB 스키마 초기화
├── sync.py                       ← Sheets→DB 동기화
├── config.py                     ← 설정값
├── auth.py                       ← 인증
├── users.py                      ← 사용자 관리
├── requirements.txt
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml
└── data/                         ← DB 파일 (영구 보존)
    ├── equipment.db              ← 통합 DB (장비+이벤트+카페마케팅+사용자)
    └── backups/
        └── equipment_2026-03-12.db
```

---

## 7. NAS 관리자에게 전달할 요청서

```
[요청 사항]

1. Docker 패키지: 이미 설치됨 (확인 완료)

2. 공유 폴더 생성:
   - 경로: /nas/uni-portal/
   - 용도: 통합 관리 앱 코드 + 데이터베이스

3. 포트 개방 (내부망):
   - 8501번: 통합 관리 시스템 (하나의 포트만 필요)

4. 접속 범위:
   - 내부망만 (192.168.x.x) 또는
   - DDNS + 역방향 프록시 (외부 접속 필요 시)

5. 백업:
   - /nas/uni-portal/data/ 폴더를 정기 백업 대상에 포함
```

---

## 8. 용어 사전 (초보자용)

| 용어 | 설명 |
|---|---|
| **DB (데이터베이스)** | 데이터를 체계적으로 저장하는 시스템. 엑셀의 진화 버전 |
| **SQLite** | 파일 1개로 동작하는 가벼운 데이터베이스. 설치 필요 없음 |
| **Docker** | 프로그램을 "상자"에 넣어 어디서든 동일하게 실행하는 기술 |
| **컨테이너** | Docker로 만든 "상자" 하나. 프로그램 1개가 독립적으로 실행됨 |
| **NAS** | Network Attached Storage. 네트워크에 연결된 저장 장치(서버) |
| **포트** | 서버의 "문 번호". 8501번 문으로 들어가면 장비 관리 프로그램이 열림 |
| **볼륨 마운트** | Docker 컨테이너와 NAS 폴더를 연결하는 것. DB 파일이 영구 보존됨 |
| **Streamlit** | Python으로 웹 화면을 만드는 도구 (특정 사이트가 아닌 "도구") |
| **API** | 프로그램끼리 데이터를 주고받는 통로 |
| **CRUD** | Create(생성), Read(조회), Update(수정), Delete(삭제) — 데이터 기본 동작 |
| **마이그레이션** | 데이터를 기존 시스템에서 새 시스템으로 옮기는 작업 |
| **docker-compose** | 여러 Docker 컨테이너를 한 번에 관리하는 설정 파일 |
| **DDNS** | 집/회사 IP가 바뀌어도 고정 주소로 접속할 수 있게 해주는 서비스 |
