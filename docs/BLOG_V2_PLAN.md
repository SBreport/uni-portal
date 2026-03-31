# 블로그 관리 v2 기획안

> 작성일: 2026-03-31
> 최종 수정: 2026-03-31 (1차 피드백 반영)
> 상태: 기획 단계

---

## 목차

1. [논문글 ↔ 논문 DB 연동](#1-논문글--논문-db-연동)
2. [키워드 검색량 + 노출순위 추적](#2-키워드-검색량--노출순위-추적)
3. [지점별 키워드 선점 모니터링](#3-지점별-키워드-선점-모니터링)

---

## 1. 논문글 ↔ 논문 DB 연동

### 목적
블로그 DB의 논문글(`post_type_main = '논문글'`)이 어떤 원본 논문을 참조했는지 파악하여,
시술정보 → 논문탭에서 "이 논문 → 이런 블로그 글로 발행됨"을 역추적할 수 있도록 한다.

### 현재 상태
- `paper_blog_links` 테이블 이미 존재 (paper_id ↔ blog_post_id 매핑)
- **서버 논문 DB**: 1차 구축 완료 (추후 보강 예정)
- 블로그 DB: `post_type_main = '논문글'` 약 225건
- **문제**: 현재 두 DB 간 연결 데이터가 비어있음

### 핵심 이슈

#### 이슈 1: DB에 없는 논문 참조
논문글이 참조한 원본 논문이 현재 서버 DB에 존재하지 않을 수 있음.

**대응 방안:**
```
매칭 결과 3가지 상태:
  ✅ 매칭됨     — 서버 DB 논문과 정확히 연결됨
  ⚠️ DB 미보유  — 참조 논문은 식별했으나 DB에 없음 → 논문 정보 임시 저장
  ❓ 식별 불가  — 어떤 논문을 참조했는지 파악 불가 → 수동 매칭 필요
```

- **DB 미보유 논문 처리**: 본문에서 논문 제목/저자/DOI를 추출하여 `unmatched_papers` 임시 테이블에 저장.
  추후 해당 논문을 확보하여 DB 보강 시 자동으로 매칭 전환.
- **매칭 기준은 100% 서버 DB 기반**. Z드라이브 PDF 직접 참조 없음.

#### 이슈 2: 다대다(N:M) 관계
논문글과 논문은 1:1이 아닐 수 있음.

```
케이스 A — 1:N (논문글 1개 → 논문 여러 편 참조)
  "보톡스 최신 논문 정리" → 논문 3편 참조

케이스 B — N:1 (논문 1편 → 여러 논문글에서 참조)
  "Efficacy of BTX-A..." → 강남점 글, 서초점 글에서 각각 참조

케이스 C — N:M
  복합 참조
```

**대응 방안:**
- `paper_blog_links`는 이미 N:M 구조 (junction table) → 구조 변경 불필요
- UI에서 논문글 1개에 복수 논문 연결 지원
- 논문 상세에서 "이 논문을 참조한 글 N건" 역방향 조회

#### 이슈 3: 자동 매칭 정확도 검증 필요
논문글 본문만으로 원본 논문을 정확히 식별할 수 있는지 **사전 테스트 필수**.

**검증 계획:**
```
Step 1: 샘플 테스트 (10~20건)
  - 논문글 본문 크롤링 → 논문 제목/저자/DOI 추출 시도
  - 추출된 정보로 서버 DB 매칭 시도
  - 정확도 측정 (정확 매칭 / 후보 복수 / 식별 불가)

Step 2: 결과에 따라 전략 결정
  - 정확도 80%↑ → 자동 매칭 + 수동 보정
  - 정확도 50~80% → 자동 후보 추천 + 수동 확정
  - 정확도 50%↓ → 수동 매칭 위주, 자동은 보조
```

### 매칭 전략

**자동 매칭 방법 (우선순위)**
1. **본문 크롤링 (핵심)**: 발행 URL 본문에서 논문 제목, 저자명, DOI, 저널명 직접 추출
2. **키워드 기반**: 논문글의 `keyword`에서 시술명 추출 → 서버 DB `keywords`, `title_ko` 매칭
3. **수동 매칭 UI**: 자동매칭 실패 시, 대시보드에서 수동 연결

### 구현 범위

| 항목 | 설명 | 우선순위 |
|------|------|----------|
| 샘플 매칭 테스트 | 10~20건 본문 크롤링 → 매칭 가능성 검증 | **P0** |
| 자동 매칭 엔진 | 본문 크롤링 + keyword 유사도 기반 후보 추천 | P1 |
| 매칭 관리 UI | 논문글 목록에서 "연결된 논문" 확인/수정 (복수 연결 지원) | P1 |
| 논문탭 역방향 | 논문 상세에서 "참조한 블로그 글 N건" 목록 표시 | P1 |
| 미보유 논문 관리 | DB에 없는 참조 논문 임시 저장 + 보강 시 자동 전환 | P1 |
| 매칭 통계 | 매칭/미보유/식별불가 현황 대시보드 | P2 |

### DB 변경

```sql
-- 기존 테이블 활용 (구조 변경 없음, N:M 이미 지원)
-- paper_blog_links: link_type 값 확장
--   'auto_content'  — 본문 크롤링 자동 매칭
--   'auto_keyword'  — 키워드 기반 자동 매칭
--   'manual'        — 수동 매칭
--   confidence 컬럼 추가 (자동매칭 신뢰도 0~1)

-- 신규: DB 미보유 논문 임시 저장
CREATE TABLE unmatched_papers (
    id              INTEGER PRIMARY KEY,
    blog_post_id    INTEGER REFERENCES blog_posts(id),
    extracted_title TEXT,              -- 본문에서 추출한 논문 제목
    extracted_authors TEXT,            -- 추출한 저자명
    extracted_doi   TEXT,              -- 추출한 DOI
    extracted_journal TEXT,            -- 추출한 저널명
    matched_paper_id INTEGER,          -- 추후 DB 보강 시 매칭된 paper_id
    status          TEXT DEFAULT 'unmatched',  -- unmatched / matched / ignored
    created_at      TEXT DEFAULT (datetime('now'))
);
```

---

## 2. 키워드 검색량 + 노출순위 추적

### 목적
블로그 글의 `keyword`에 대해:
- 네이버 월간 검색량 (PC/모바일) 확인
- 해당 글이 **네이버 통합검색 (첫 화면)** 에서 몇 번째에 노출되는지 순위 추적

### 운영 정책
- **대상**: 전체 게시글이 아닌 **월간 단위**로 선별 (가장 최근 달 우선)
- **주기**: **주 1회** 실행 (초기 수동 트리거 → 추후 스케줄러 자동화)
- **순위 기준**: 20위 이내 노출 = 정상, **20위 밖 = "순위 누락"으로 표시 (빨강)**

### 데이터 소스

#### 2-1. 월간 검색량 — 네이버 검색광고 API

```
API: https://api.naver.com/keywordstool
인증: 네이버 검색광고 계정 (API 라이선스 키)
제공 데이터:
  - monthlyPcQcCnt (PC 월간 검색량)
  - monthlyMobileQcCnt (모바일 월간 검색량)
  - monthlyAvePcClkCnt (PC 평균 클릭수)
  - monthlyAveMobileClkCnt (모바일 평균 클릭수)
  - compIdx (경쟁 정도: 높음/중간/낮음)
```

**API 한도 vs 실제 사용량 분석**
```
하루 5,000건 제한

월간 작업량 추정:
  - 최근 1개월 게시글: ~300~400건
  - 키워드 중복 제거 시: ~150~250건 (추정)
  - 주 1회 실행 → 1회당 ~250건
  → 하루 5,000건 대비 5% 사용 → 충분

향후 확장 시 (3번 기능 포함):
  - 지점별 타겟 키워드 추가: ~200~500건
  - 합계: ~500~750건/회 → 여전히 충분
```

#### 2-2. 노출순위 — 네이버 통합검색 크롤링

```
타겟: 네이버 통합검색 첫 화면 (search.naver.com 기본 탭)
      ※ VIEW 탭이 아닌 통합검색 메인 = 사용자가 검색 시 처음 보는 화면
검색 URL: https://search.naver.com/search.naver?query={keyword}
매칭 기준: published_url과 검색결과 URL 일치 여부
순위 범위: 상위 20위까지 수집
```

**순위 상태 정의:**
```
1~10위   → 🟢 상위 노출
11~20위  → 🟡 노출 중
20위 밖  → 🔴 순위 누락
```

**주의사항**
- 네이버 크롤링 정책 준수 (과도한 요청 제한)
- IP 차단 방지: 요청 간격 조절 (2~3초 딜레이)
- 순위는 시간대/개인화에 따라 변동 → 고정 시간대에 측정

### 구현 범위

| 항목 | 설명 | 우선순위 |
|------|------|----------|
| 검색량 조회 API | 네이버 검색광고 API 연동 | P1 |
| 검색량 DB 저장 | keyword_stats 테이블, 월간 단위 갱신 | P1 |
| 순위 크롤러 | 통합검색 크롤링 → 상위 20위 수집 | P1 |
| 수동 트리거 | 대시보드에서 "순위 측정" 버튼 → 월 단위 선택 실행 | P1 |
| 블로그 목록 표시 | 키워드 옆에 검색량(PC/MB) + 순위 뱃지 표시 | P1 |
| 순위 누락 표시 | 20위 밖 게시글 목록 하이라이트 | P1 |
| 스케줄러 자동화 | 주 1회 자동 실행 (추후) | P2 |
| 순위 이력 | 주간 순위 변동 추적 (상승↑/하락↓) | P2 |

### 신규 테이블

```sql
-- 키워드 검색량 (월간 갱신)
CREATE TABLE keyword_stats (
    id              INTEGER PRIMARY KEY,
    keyword         TEXT NOT NULL,
    pc_search       INTEGER,          -- PC 월간 검색량
    mobile_search   INTEGER,          -- 모바일 월간 검색량
    pc_click        REAL,             -- PC 평균 클릭수
    mobile_click    REAL,             -- 모바일 평균 클릭수
    competition     TEXT,             -- 경쟁도 (높음/중간/낮음)
    measured_at     TEXT NOT NULL,     -- 측정일
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 키워드 순위 추적 (주 1회 측정)
CREATE TABLE keyword_rankings (
    id              INTEGER PRIMARY KEY,
    blog_post_id    INTEGER REFERENCES blog_posts(id),
    keyword         TEXT NOT NULL,
    rank_position   INTEGER,          -- 노출 순위 (NULL = 20위 밖)
    rank_status     TEXT,             -- 'top' (1~10) / 'mid' (11~20) / 'missing' (20+)
    search_type     TEXT DEFAULT 'integrated',  -- integrated(통합검색)
    target_month    TEXT,             -- 측정 대상 월 (2026-03)
    measured_at     TEXT NOT NULL,     -- 실제 측정일시
    created_at      TEXT DEFAULT (datetime('now'))
);
```

### 운영 플로우

```
[주 1회 작업 — 초기 수동 / 추후 스케줄러]

  1. 대상 월 선택 (기본: 이번 달)
  2. 해당 월 blog_posts에서 keyword 수집 (중복 제거)
  3. 네이버 검색광고 API → keyword_stats 갱신
  4. 각 keyword로 네이버 통합검색 크롤링 (상위 20위)
  5. 검색결과에서 published_url 매칭 → keyword_rankings 저장
  6. 20위 밖 게시글 → rank_status = 'missing' 기록

[프론트엔드 — 블로그 목록]
  키워드 셀:
    - 검색량 PC/MB 뱃지
    - 순위 뱃지 (🟢/🟡/🔴)
    - 클릭 시 순위 이력 팝업

[프론트엔드 — 대시보드]
  "순위 측정" 버튼 → 월 선택 → 실행
  측정 결과 요약: 총 N건 / 상위노출 n건 / 순위하락 n건
```

---

## 3. 지점별 키워드 선점 모니터링

### 목적
지점별로 타겟 키워드를 등록하고, 해당 키워드를 우리 블로그가 **몇 개나 선점하고 있는지**
(선점 개수) 추적한다. 미선점 키워드를 파악하여 **월간 키워드 전략 수립**에 활용.

### 접근 권한
- **ALL 페이지 전용** (유앤아이 계정에서는 비노출)
- 우리 내부 마케팅 성과 분석 + 전략 수립 용도

### 블로그 ID 유형 분류

```
블로그 유형:
  최적화블로그 (optimized) — 전 지점 공용, 지역 무관 통합 계정으로 운영
  브랜드블로그 (brand)     — 지점별 전용 계정 (1개 지점 = 1~N개 브블 가능)

분류 방법:
  blog_accounts 테이블의 기존 데이터 활용
  → blog_id + 발행 글 유형 매칭으로 자동 분류 가능
  → 한번 셋팅 시 변동 없음 (blog_accounts에 blog_type 컬럼 추가)

특이 케이스:
  - 1개 지점 → 복수 브랜드블로그 운영 가능 (예: 강남점 브블 2개)
  - 최적화블로그 → 특정 지점 소속이 아닌 전 지점 통합 계정
    → 키워드 순위 측정 시, 최적 글의 지점은 keyword/branch_name 기준으로 매칭
```

### 키워드 등록 범위

```
유형 1 — 기발행 키워드 (자동 수집)
  blog_posts에서 해당 지점 발행글의 keyword 추출
  → 2단계 검색량 데이터 연동
  → 순위 자동 추적

유형 2 — 미발행 타겟 키워드 (수동 등록)
  아직 글을 쓰지 않았지만 선점하고 싶은 키워드
  → 검색량만 조회 (순위는 발행 전이므로 없음)
  → 매월 원고 작성 전, 미선점 키워드를 파악하여 전략 수립

활용 플로우:
  월초 → 지점별 키워드 현황 확인
       → 선점 키워드 vs 미선점 키워드 파악
       → 미선점 키워드 중 검색량 높은 순으로 우선순위 결정
       → 해당 월 원고 키워드 선정
```

### UI 탭 구성 제안

```
방안 A — 블로그 하위 탭 (권장)
  블로그 탭
    ├─ 대시보드
    ├─ 글 목록
    ├─ 계정 관리
    └─ 🆕 키워드 전략    ← ALL 전용, 유앤아이 비노출

  장점: 블로그 데이터와 동일 맥락에서 확인 가능
  단점: 블로그 탭이 무거워질 수 있음

방안 B — 별도 세부탭
  메인 탭에 "키워드 관리" 독립 탭 신설

  장점: 독립적 관리, 확장 용이
  단점: 블로그 데이터 참조 시 탭 이동 필요

→ 방안 A 권장: 블로그 글과 키워드 전략이 밀접하게 연관되므로
  하위 탭으로 배치하되, ALL 전용으로 접근 제한
```

### 개념 설계

```
[키워드 전략 화면 — 지점 선택: 유앤아이 강남점]

┌─────────────────────────────────────────────────────┐
│ 타겟 키워드 현황                    [키워드 추가] [측정] │
├─────────────┬────────┬────────┬──────┬──────────────┤
│ 키워드       │ PC검색  │ MB검색  │ 선점  │ 상세          │
├─────────────┼────────┼────────┼──────┼──────────────┤
│ 강남 보톡스   │ 12,100 │ 33,500 │ 3개  │ 최적3위,브블7위,브블15위 │
│ 강남 필러     │ 8,200  │ 22,100 │ 2개  │ 최적5위,브블11위  │
│ 강남 리프팅   │ 5,400  │ 15,800 │ 0개  │ 🔴 미선점       │
│ 강남 피부과   │ 18,300 │ 45,200 │ 1개  │ 브블8위         │
└─────────────┴────────┴────────┴──────┴──────────────┘

선점 = 통합검색 20위 이내 우리 글 개수 (최적+브블 합산)
```

### 최적화블로그 매칭 로직

```
최적화블로그는 전 지점 통합 계정이므로 특별 처리 필요:

  "강남 보톡스" 키워드로 최적블에서 발행한 글이 있는가?
  → blog_posts에서:
    blog_id IN (최적화블로그 ID 목록)
    AND (keyword LIKE '%강남%보톡스%' OR branch_name LIKE '%강남%')
  → 매칭되면 해당 지점의 선점 카운트에 포함

  즉, 최적블 글은 keyword/branch_name 기준으로 지점에 귀속
  브블 글은 blog_id → 지점 직접 매핑
```

### 구현 범위

| 항목 | 설명 | 우선순위 |
|------|------|----------|
| blog_accounts 유형 분류 | blog_type 컬럼 추가 (optimized/brand) | P1 |
| 지점별 키워드 등록 UI | 기발행 자동수집 + 미발행 수동등록 CRUD | P1 |
| 키워드별 선점 개수 수집 | 2번 크롤러 확장, 복수 blog_id 매칭 | P1 |
| 키워드 전략 탭 | 지점별 키워드 현황 테이블 (ALL 전용) | P1 |
| 최적블 지점 귀속 로직 | keyword/branch 기반 지점 매칭 | P1 |
| 미선점 키워드 하이라이트 | 선점 0개 키워드 경고 표시 | P1 |
| 월간 전략 리포트 | 지점별 선점/미선점 요약 (추후) | P2 |

### 신규/수정 테이블

```sql
-- blog_accounts 수정: 블로그 유형 추가
ALTER TABLE blog_accounts ADD COLUMN blog_type TEXT DEFAULT 'brand';
-- 값: 'optimized' (최적화블) / 'brand' (브랜드블)

-- 지점-블로그 매핑 (1개 지점 = N개 브블 가능)
CREATE TABLE branch_blog_mapping (
    id              INTEGER PRIMARY KEY,
    branch_name     TEXT NOT NULL,
    blog_id         TEXT NOT NULL,
    blog_type       TEXT NOT NULL,     -- 'optimized' / 'brand'
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(branch_name, blog_id)
);

-- 지점별 타겟 키워드
CREATE TABLE branch_target_keywords (
    id              INTEGER PRIMARY KEY,
    branch_name     TEXT NOT NULL,
    keyword         TEXT NOT NULL,
    category        TEXT,              -- 시술 카테고리
    source          TEXT DEFAULT 'manual',  -- 'auto' (기발행 수집) / 'manual' (수동 등록)
    is_published    INTEGER DEFAULT 0, -- 해당 키워드로 글 발행 여부
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(branch_name, keyword)
);

-- 키워드 선점 현황 (2번 keyword_rankings 확장)
CREATE TABLE keyword_occupation (
    id              INTEGER PRIMARY KEY,
    branch_name     TEXT NOT NULL,
    keyword         TEXT NOT NULL,
    blog_id         TEXT NOT NULL,
    blog_type       TEXT NOT NULL,     -- 'optimized' / 'brand'
    rank_position   INTEGER,           -- 순위 (NULL = 20위 밖)
    occupation_count INTEGER,          -- 해당 키워드 총 선점 개수
    measured_at     TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now'))
);
```

---

## 기능 간 의존 관계

```
[1. 논문 연동]  ──────────────────  독립 구현 가능
                                    (기존 paper_blog_links 활용)

[2. 검색량+순위] ─────┐
                      ├──────────  2번 크롤러/API를 3번이 확장 사용
[3. 키워드 선점]  ────┘
                     (검색량 API + 순위 크롤러 공유)
```

## 구현 순서

```
Phase 1 — 논문 연동 (1~2주)
  ├─ P0: 샘플 매칭 테스트 (10~20건, 본문 크롤링 가능성 검증)
  ├─ 자동 매칭 엔진 구현 (테스트 결과에 따라 전략 확정)
  ├─ 매칭 관리 UI (N:M 연결 지원)
  ├─ 논문탭 역방향 조회
  └─ 미보유 논문 임시 저장 + 보강 시 자동 전환

Phase 2 — 검색량 + 순위 (2~3주)
  ├─ 네이버 검색광고 API 연동
  ├─ 통합검색 순위 크롤러 (상위 20위)
  ├─ keyword_stats / keyword_rankings 테이블
  ├─ 수동 트리거 UI (월 선택 → 실행)
  ├─ 블로그 목록 검색량/순위 뱃지
  └─ 20위 밖 순위 누락 표시

Phase 3 — 키워드 선점 모니터링 (2~3주)
  ├─ blog_accounts 유형 분류 (최적화/브랜드)
  ├─ 지점-블로그 매핑 테이블
  ├─ 키워드 전략 탭 (블로그 하위, ALL 전용)
  ├─ 기발행 키워드 자동 수집 + 미발행 키워드 수동 등록
  ├─ 선점 개수 측정 (최적블 지점 귀속 포함)
  └─ 미선점 키워드 하이라이트

Phase 2→3 전환 후 — 자동화
  └─ 주 1회 스케줄러 (검색량 + 순위 + 선점 일괄 측정)
```

## 사전 준비 필요 사항

| 항목 | 필요 시점 | 상태 |
|------|-----------|------|
| 논문글 샘플 10~20건 본문 매칭 테스트 | Phase 1 시작 시 | ⬜ 미진행 |
| 서버 논문 DB 보강 계획 | Phase 1 이후 | ⬜ 미확인 |
| 네이버 검색광고 API 키 발급 | Phase 2 시작 전 | ⬜ 미확인 |
| 검색광고 계정 보유 여부 확인 | Phase 2 시작 전 | ⬜ 미확인 |
| blog_accounts 유형 분류 (최적화/브랜드) | Phase 3 시작 전 | ⬜ 기존 데이터로 가능 추정 |
| 지점별 복수 브블 현황 파악 | Phase 3 시작 전 | ⬜ 미확인 |
| paper_blog_links 테이블 존재 | Phase 1 시작 전 | ✅ 존재 |
