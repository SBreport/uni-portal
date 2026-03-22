# 유앤아이의원 통합 관리 시스템 — 데이터 아키텍처

> 최종 업데이트: 2026-03-22
> 상태: 기획안 (검토 후 구현 예정)

---

## 1. 시스템 목적

**명확한 사실(Fact)**을 기반으로 **콘텐츠(Content)**를 발행하고 추적 관리하는 시스템.

```
┌─────────────────────────────────────────────────┐
│                  Fact Layer (사실)                │
│                                                   │
│  장비사전        논문/연구        이벤트/가격       │
│  (device_info)  (papers)        (evt_items)       │
│  127건 등록      3건 분석 완료    1,699건 시술      │
│                                                   │
│  "이 장비가 뭔지"  "근거가 뭔지"  "얼마에 파는지"    │
├─────────────────────────────────────────────────┤
│                     ↕ 참조                        │
├─────────────────────────────────────────────────┤
│               Content Layer (콘텐츠)              │
│                                                   │
│  카페 원고         블로그 원고        (추후 확장)   │
│  (월 20건×42지점)  (장문 콘텐츠)      플레이스/웹   │
│                                                   │
│  "어떻게 홍보하는지"  "어떤 글을 쓰는지"             │
└─────────────────────────────────────────────────┘
```

---

## 2. 현재 구조의 문제점

### 2.1 단일 DB 문제

```
equipment.db (현재: 모든 것이 한 파일)
├── device_info (장비사전)     ← Fact
├── papers (논문)              ← Fact
├── equipment (보유장비)       ← Fact
├── evt_* (이벤트)             ← Fact
├── cafe_articles (카페원고)   ← Content ⚠️
├── cafe_comments (댓글)       ← Content ⚠️
├── users (사용자)             ← System ⚠️
└── ...
```

**문제:**
- DB 업로드 시 카페 원고가 덮어쓰임 (이미 발생)
- 장비 정보 업데이트와 원고 작업이 서로 간섭
- 월별 원고 이력 관리가 어려움
- 백업/복원 시 전체를 다뤄야 함

### 2.2 크로스 참조 부재

- 카페 원고에 장비명이 텍스트로만 저장 (device_info와 FK 연결 없음)
- 블로그 시스템 자체가 없음
- 같은 장비에 대해 카페/블로그에서 뭘 썼는지 추적 불가
- 논문 정보가 콘텐츠 작성에 활용되지 않음

---

## 3. 제안 구조: 4-DB 분리

```
data/
├── equipment.db     Fact DB — 장비·시술·논문·이벤트 (관리자)
├── cafe.db          카페 콘텐츠 DB (편집자/작가)
├── blog.db          블로그 콘텐츠 DB (편집자/작가)
└── system.db        시스템 DB — 사용자·설정·로그 (시스템)
```

### 각 DB 상세

```
equipment.db (Fact — 장비/시술/논문/이벤트)
├── device_info          장비/시술 사전 (127건)
├── papers               논문/연구자료
├── equipment            지점별 보유장비
├── branches             지점 목록
├── categories           장비 카테고리
├── evt_periods          이벤트 기간
├── evt_branches         이벤트 지점
├── evt_categories       시술 카테고리
├── evt_treatments       시술 마스터 (1,699건)
├── evt_items            이벤트 상품
├── evt_item_components  패키지 구성
├── evt_ingestion_logs   수집 로그
├── evt_category_aliases 카테고리 별명
└── sync_log             장비 동기화 로그

cafe.db (Content — 카페 원고)
├── cafe_periods             기간 (연/월)
├── cafe_branch_periods      지점별 기간 메타 (담당자/작가)
├── cafe_articles            원고 (device_info_id FK 참조)
├── cafe_comments            댓글/대댓글
├── cafe_feedbacks           피드백
├── cafe_status_log          상태 이력
└── cafe_sync_log            동기화 로그

blog.db (Content — 블로그 원고)
├── blog_articles            블로그 원고 (device_info_id FK 참조)
├── blog_tags                태그 (장비 연결)
├── blog_comments            댓글 (선택)
├── blog_status_log          상태 이력
└── blog_sync_log            동기화 로그

system.db (System — 사용자/설정)
├── users                    사용자 계정
├── settings                 시스템 설정 (신규)
└── audit_log                관리 로그 (신규)
```

### 3.1 왜 4개로 나누는가

| 구분 | equipment.db | cafe.db | blog.db | system.db |
|------|:---:|:---:|:---:|:---:|
| **성격** | 사실/마스터 | 카페 콘텐츠 | 블로그 콘텐츠 | 시스템 |
| **변경 빈도** | 드묾 | 매일 | 주 1~2회 | 드묾 |
| **관리 주체** | 관리자 | 편집자/작가 | 편집자/작가 | 관리자 |
| **업로드** | 로컬→서버 | 구글시트→서버 | 웹앱 직접 | 자동 |
| **백업 주기** | 월 1회 | 주 1회 | 주 1회 | 월 1회 |
| **독립 업로드** | ✅ 카페 영향 없음 | ✅ 장비 영향 없음 | ✅ 카페 영향 없음 | ✅ |

### 3.2 월별 DB vs 단일 DB

| 방식 | 장점 | 단점 |
|------|------|------|
| **월별 DB** (content_202603.db) | 월별 독립, 깔끔한 아카이빙 | 크로스 월 검색 어려움, 파일 관리 복잡 |
| **단일 DB** (content.db) | 크로스 검색 용이, 관리 단순 | 파일이 커질 수 있음 |

**추천: 채널별 DB 분리** — 카페/블로그 각각 별도 DB. 채널별 독립 관리 + 장비 DB 참조.

---

## 4. 크로스 참조 구조

### 4.1 콘텐츠↔장비 연결 (content_device_links)

```sql
-- content.db
CREATE TABLE content_device_links (
    id            INTEGER PRIMARY KEY,
    content_type  TEXT NOT NULL,        -- 'cafe' / 'blog'
    content_id    INTEGER NOT NULL,     -- cafe_articles.id 또는 blog_articles.id
    device_info_id INTEGER NOT NULL,    -- equipment.db의 device_info.id 참조
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**활용 예시:**
- 보유장비 탭 → 써마지FLX 클릭 → "관련 콘텐츠" 섹션에 카페 3건, 블로그 1건 표시
- 카페 원고 작성 시 → 장비 선택 → 자동으로 해당 장비의 논문/이벤트 정보 참조

### 4.2 논문↔콘텐츠 연결 (paper_blog_links)

```sql
-- equipment.db
CREATE TABLE paper_blog_links (
    id            INTEGER PRIMARY KEY,
    paper_id      INTEGER NOT NULL,     -- papers.id
    content_type  TEXT NOT NULL,         -- 'cafe' / 'blog'
    content_id    INTEGER NOT NULL,      -- 해당 콘텐츠 id
    link_url      TEXT,                  -- 발행 URL
    title         TEXT,                  -- 콘텐츠 제목
    author        TEXT,                  -- 작성자
    published_at  TEXT,                  -- 발행일
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**활용 예시:**
- 시술논문 탭 → 써마지 논문 → "관련 게시글: 카페 링크1, 블로그 링크2"
- 블로그 원고 작성 시 → 참조 논문 선택 → 자동 연결

### 4.3 크로스 체크 뷰

```
장비: 써마지FLX
├── 📋 장비 사전: RF 리프팅, 6.78MHz...
├── 📄 관련 논문: "써마지 4세대 피부 탄력 개선 효과" (Level 1)
├── 💰 현재 이벤트: 강남점 300샷 99만원, 600샷 169만원
├── ☕ 카페 원고:
│   ├── 2026.03 강남점 "강남피부과추천 받고싶어요" (발행완료)
│   ├── 2026.02 건대점 "써마지 효과 후기" (발행완료)
│   └── 2026.01 광교점 "써마지vs울쎄라 비교" (발행완료)
└── 📝 블로그 원고:
    └── 2026.03 "써마지FLX의 원리와 효과" (작성완료)
```

---

## 5. 블로그 테이블 설계 (신규)

```sql
-- content.db
CREATE TABLE blog_articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    branch_id       INTEGER,             -- 지점 (NULL=본사)
    title           TEXT NOT NULL,
    body            TEXT,
    category        TEXT,                -- 시술후기/장비소개/의학정보/이벤트
    writer          TEXT,                -- 작성자
    status          TEXT DEFAULT '작성대기',  -- 작성대기/작성완료/검수완료/발행완료
    published_url   TEXT,
    published_at    TEXT,
    year            INTEGER,
    month           INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE blog_tags (
    id              INTEGER PRIMARY KEY,
    article_id      INTEGER NOT NULL,
    device_info_id  INTEGER,             -- equipment.db 참조
    tag_name        TEXT NOT NULL         -- 자유 태그
);
```

---

## 6. 데이터 흐름도

```
[관리자 업무]                           [편집자/작가 업무]

 장비사전 등록/수정                       카페 원고 작성
 논문 분석/업로드                         블로그 원고 작성
 이벤트 시트 동기화                       댓글/대댓글 작성
 장비 시트 동기화                         상태 변경/발행
       │                                      │
       ▼                                      ▼
  equipment.db                           content.db
  (Fact Layer)                          (Content Layer)
       │                                      │
       └──────── 참조 (device_info_id) ────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  웹앱 화면 통합   │
              │                 │
              │ 장비 클릭 →     │
              │  사전+논문+이벤트│
              │  +카페+블로그   │
              │  한눈에 보기     │
              └─────────────────┘
```

---

## 7. 마이그레이션 계획

### Phase 1: DB 분리 (우선)
1. `content.db` 생성
2. `equipment.db`에서 cafe_* 테이블을 `content.db`로 이전
3. API 라우터에서 DB 연결 경로 분리
4. 기존 기능 정상 동작 확인

### Phase 2: 크로스 참조 (다음)
1. `content_device_links` 테이블 생성
2. 카페 원고의 equipment_name → device_info_id FK 연결
3. 보유장비 상세 패널에 "관련 콘텐츠" 섹션 추가

### Phase 3: 블로그 시스템 (이후)
1. `blog_articles`, `blog_tags` 테이블 생성
2. 블로그 탭 UI 구현 (카페와 유사 구조)
3. `paper_blog_links` 테이블로 논문↔블로그 연동

### Phase 4: 통합 뷰 (최종)
1. 장비별 "전체 연관 정보" 통합 패널
2. 크로스 채널 콘텐츠 추적 대시보드
3. 월별/채널별 콘텐츠 발행 현황 리포트

---

## 8. 4-DB 구조 적합성 검토

### 8.1 목표 시나리오별 검증

**시나리오 A: 장비사전 업데이트 (관리자)**
```
관리자 → equipment.db 업로드 → device_info 127→130건
cafe.db = 영향 없음 ✅
blog.db = 영향 없음 ✅
```

**시나리오 B: 카페 원고 월간 동기화 (편집자)**
```
편집자 → 구글시트 동기화 → cafe.db에 3월 원고 840건 저장
equipment.db = 영향 없음 ✅
blog.db = 영향 없음 ✅
```

**시나리오 C: 장비 클릭 → 전체 연관 정보 조회**
```
보유장비 탭 → 써마지FLX 클릭
 ├── equipment.db → device_info (사전 정보) ✅
 ├── equipment.db → papers (관련 논문) ✅
 ├── equipment.db → evt_items (현재 이벤트) ✅
 ├── cafe.db → cafe_articles WHERE device_info_id=2 (카페 원고) ✅
 └── blog.db → blog_articles WHERE device_info_id=2 (블로그) ✅
```
→ 3개 DB를 조회하지만, device_info_id로 연결되므로 정확한 결과.
→ API 레이어에서 3개 DB 결과를 합쳐서 프론트에 전달.

**시나리오 D: 크로스 채널 체크**
```
3월 카페 원고 "써마지 추천" (cafe.db, device_info_id=2)
2월 블로그 "써마지FLX 원리" (blog.db, device_info_id=2)
→ 같은 device_info_id=2로 연결 → 크로스 체크 가능 ✅
```

**시나리오 E: 논문 → 관련 게시글 조회**
```
시술논문 탭 → 써마지 논문 클릭
 ├── equipment.db → papers (논문 상세)
 ├── cafe.db → WHERE device_info_id = papers.device_info_id (카페 원고)
 └── blog.db → WHERE device_info_id = papers.device_info_id (블로그)
→ 논문과 같은 장비의 콘텐츠 자동 연결 ✅
```

**시나리오 F: 담당자 교체 시 인수인계**
```
카페 담당자 교체 → cafe.db만 설명하면 됨 ✅
장비 담당자 교체 → equipment.db만 설명하면 됨 ✅
전체 시스템 인수인계 → 4개 DB 역할만 이해하면 됨 ✅
```

### 8.2 추가 DB 필요성 검토

| 후보 | 필요성 | 판단 |
|------|:------:|------|
| **place.db** (플레이스) | 🟡 | 추후 플레이스 관리 시 분리 가능. 당장은 불필요 |
| **webpage.db** (웹페이지) | 🟡 | 추후 웹페이지 관리 시 분리 가능. 당장은 불필요 |
| **reports.db** (보고서) | ❌ | 보고서는 다른 DB 조합으로 생성. 별도 저장 불필요 |
| **analytics.db** (통계) | 🟢 | 조회수/클릭 등 추적 시 필요. 현재는 불필요 |

**결론: 현재 4-DB 구조로 충분. 플레이스/웹페이지는 blog.db 패턴을 복제하면 됨.**

### 8.3 주의사항

| 항목 | 설명 |
|------|------|
| **FK 무결성** | SQLite는 cross-DB FK를 지원하지 않음. API 레이어에서 검증 |
| **트랜잭션** | 2개 이상 DB에 걸친 트랜잭션 불가. 각 DB 독립 커밋 |
| **device_info_id 동기화** | equipment.db의 id가 변경되면 cafe/blog가 깨짐. id는 절대 변경 금지 |
| **Docker Volume** | 4개 DB 파일 모두 같은 볼륨(/app/data/)에 저장. 볼륨 1개로 충분 |

---

## 9. 현재 시스템 적합성 평가

| 항목 | 현재 | 목표 | 갭 |
|------|:----:|:----:|:--:|
| 장비 사전 | ✅ 127건 | ✅ | — |
| 논문 DB | ✅ 3건 | 확대 필요 | 소 |
| 이벤트 | ✅ 1,699건 | ✅ | — |
| 카페 원고 | ✅ 동작 중 | DB 분리 필요 | 중 |
| 블로그 | ❌ placeholder | 신규 구현 | 대 |
| 장비↔콘텐츠 연결 | ⚠️ 텍스트만 | FK 연결 | 중 |
| 논문↔콘텐츠 연결 | ❌ | 신규 | 중 |
| 크로스 채널 추적 | ❌ | 신규 | 대 |
| DB 분리 | ❌ 단일 파일 | 2파일 분리 | 중 |

**결론:** 현재 시스템의 기반(FastAPI+Vue+SQLite)은 적합. DB 분리와 크로스 참조 테이블 추가가 핵심 보완 사항.
