# Uni-Portal 디자인 시스템

> 이 문서는 uni-portal 프로젝트의 디자인 규칙을 정리한 **단일 진실 공급원**입니다.
> 새 기능/페이지를 만들거나 리팩토링할 때 **항상 먼저 이 문서를 읽고 시작**하세요.

**최초 작성**: 2026-04-14
**기준 페이지**: 관리자 모드 > 실행사 매핑 > 대시보드 (현재 유일하게 정제된 페이지)
**적용 전략**: 참조 + 점진적 리팩토링

---

## 1. 디자인 철학

### Core Values
- **Information density first** — 의료 마케팅 관리 툴. 화면당 의사결정 정보량이 곧 가치.
- **No crosseyed layouts** — 사시 모드 금지. 정보가 좌우로 벌어져 눈을 굴려야 하면 실패. **섹션 2.5 참조.**
- **Utility over decoration** — 장식 요소 제로. 모든 시각 요소는 기능을 함.
- **Neutral foundation + semantic color** — 회색 바탕에 의미 있는 색만 포인트.
- **Opinionated over flexible** — 규칙이 많고 예외가 적을수록 일관성 올라감.

### Personality (무드 단어)
- **compact**, **professional**, **calm**, **data-forward**
- NOT: playful, trendy, decorative, marketing-style

### One-sentence test
> "이 화면을 20초 봤을 때, 사용자가 다음 행동을 결정할 수 있는가?"

---

## 2. 색상 시스템

### Neutral Scale (Slate)
모든 UI의 **90%는 slate**. 이걸 바탕으로 깔고 포인트 색만 얹는다.

| 용도 | 클래스 |
|---|---|
| 최상단 텍스트 (제목) | `text-slate-800` |
| 본문/중요 텍스트 | `text-slate-700` |
| 보조 텍스트 (라벨) | `text-slate-500` |
| 희미한 메타 (날짜 등) | `text-slate-400` |
| 비활성/빈 상태 | `text-slate-300` |
| 카드 배경 | `bg-white` |
| 페이지 배경 | `bg-slate-50` |
| 섹션 배경 (강조) | `bg-slate-50` |
| 기본 테두리 | `border-slate-200` |
| 진한 테두리 | `border-slate-300` |
| Hover 배경 | `bg-slate-50` |

### Primary Color (Blue) — Action
**블루는 "클릭할 수 있는 것"**에만.

| 용도 | 클래스 |
|---|---|
| 주요 버튼 | `bg-blue-600 hover:bg-blue-700 text-white` |
| 주요 링크 | `text-blue-600 hover:text-blue-700` |
| 활성 탭 | `border-blue-600 text-blue-600` |
| 포커스 링 | `focus:border-blue-400` |
| 강조 수치 | `text-blue-600` |

### Semantic Colors
**의미 있을 때만** 사용. 장식용 X.

| 의미 | 클래스 | 사용처 |
|---|---|---|
| 성공/긍정 | `text-emerald-600` `bg-emerald-100` | 성공, 노출 OK |
| 실패/부정 | `text-red-500` `bg-red-100` | 실패, 미노출, 삭제 |
| 경고 | `text-amber-600` `bg-amber-100` | 미갱신, 주의 |
| 정보 | `text-sky-600` `bg-sky-100` | 플레이스 도메인 |
| 보조 | `text-indigo-600` `bg-indigo-100` | 웹페이지 도메인 |
| 중립 | `text-slate-500` `bg-slate-100` | 미측정, 없음 |

### Domain Colors (4개 실행사 구분)
| 실행사 | 색상 |
|---|---|
| 애드드림즈 | `bg-blue-50 border-l-blue-400 text-blue-600` |
| 일프로 | `bg-violet-50 border-l-violet-400 text-violet-600` |
| 간달프 | `bg-emerald-50 border-l-emerald-400 text-emerald-600` |
| 에이치 | `bg-amber-50 border-l-amber-400 text-amber-600` |

### ❌ 금지 색상
- **purple-500 이상의 진한 보라/바이올렛** (장식용) — indigo로 대체
- **그라데이션 배경** (`bg-gradient-*`) — 플랫 컬러만
- **6자리 hex 코드** (`#FF6B6B`) — Tailwind 팔레트만 사용

---

## ⚠️ 2.5 사시 모드 금지 (Anti-Crosseyed Layout)

**이 프로젝트에서 가장 자주 발생한 문제이자, 가장 중요한 규칙.**

### 사시 모드란?
화면 좌우/상하로 정보가 과도하게 멀리 떨어져 있어, **사용자가 눈을 좌우로 굴려야 정보를 연결**할 수 있는 레이아웃.

```
❌ 사시 모드 예시:
┌─────────────────────────────────────────────────┐
│ 지점명                           오늘 성공률      │
│ 강남                             100%            │
│ (100px 간격을 사이에 두고 정보가 떨어져 있음)      │
└─────────────────────────────────────────────────┘

✅ 개선된 배치:
┌───────────────────────┐
│ 지점명      오늘       │
│ 강남        100%      │
│ (밀집 배치, 한눈에 파악)│
└───────────────────────┘
```

### 발생 원인
1. **과한 max-width** — `max-w-7xl` 같은 넓은 폭에 적은 정보 → 양 끝 비어짐
2. **`justify-between` 남용** — 두 요소만 있는데 전체 폭으로 벌림
3. **`grid-cols-2` / `grid-cols-3` 남용** — 정보가 적은데 열을 많이 만듦
4. **`space-y-*` 과다** — 섹션 간 여백을 공허하게 키움

### 규칙

#### 규칙 1: 정보량에 맞는 폭 제한
| 정보 밀도 | 권장 max-width |
|---|---|
| KPI 2-4개 + 차트 | `max-w-4xl` (896px) |
| 폼 1열 | `max-w-2xl` ~ `max-w-3xl` |
| 읽기용 텍스트 | `max-w-2xl` (700px) |
| 밀집 테이블 | `max-w-6xl` 또는 `w-full` |

#### 규칙 2: 다열 배치는 목적이 있을 때만
**1열이 무조건 좋은 게 아님.** 다열 배치 자체는 중립이고, **공허한 다열만 문제**.

| 상황 | 권장 | 이유 |
|---|---|---|
| 병렬 비교 (A vs B) | **다열 OK** | ✅ 대시보드 플레이스/웹페이지 나란히 |
| 밀집 데이터 (테이블, KPI 2×2) | **다열 OK** | ✅ 정보가 꽉 차면 밀도 유지됨 |
| 단일 콘텐츠 덩어리 | **1열** | 쪼개면 오히려 파편화 |
| 적은 정보 (2-3 항목)에 3열 | **1열로** | ❌ 각 열이 공허해짐 |
| 단순 리스트 | **1열** | ❌ 다열로 만들면 scan 방향 혼란 |

**핵심**: 열의 개수가 문제가 아니라 **각 열이 정보로 꽉 차있는가**가 기준.

#### 규칙 3: 밀집을 기본값으로, 여백은 목적이 있을 때
기본 여백은 **정보가 붙어 보이도록** 좁게 잡는다. 여백을 키우려면 이유가 있어야 한다.

- 카드 내부: 기본 `p-3` ~ `p-4`. 넉넉한 느낌이 필요하면 `p-5`까지 OK.
- 섹션 간격: 기본 `space-y-3` ~ `space-y-4`. 큰 시각적 구분이 필요할 때만 `space-y-6`.
- flex/grid gap: 기본 `gap-2` ~ `gap-3`.

**주의**: 같은 화면 안에서 여백 값이 **여러 단위가 섞이면 혼란**스럽다.
한 페이지 안에서는 사용하는 spacing 단위 수를 2-3개로 제한.

**자문**: "이 여백을 반으로 줄여도 정보 전달이 약해지는가?" → 아니라면 줄여라.

#### 규칙 4: `justify-between` 남용 금지
- 2개 요소에 `justify-between` → 공간 벌어짐
- 대신 `flex items-center gap-3` + 필요 시 `ml-auto` 하나만

### 셀프 체크 질문
화면을 봤을 때:
1. **"눈이 좌우로 많이 움직이는가?"** → 사시 모드 의심
2. **"정보 사이에 빈 공간이 정보만큼 넓은가?"** → 폭 줄이기
3. **"이 화면을 반으로 접어도 정보가 일정하게 남는가?"** → OK

### 관련 메모리 (사용자 피드백)
- `feedback_no_crosseyed_layout.md`: "multi-column 그리드 지양, max-w-3xl 1열 배치 선호"

---

## 3. 타이포그래피

### 크기 스케일
**커스텀 사이즈는 data-dense UI에서만** 허용.

| 역할 | 클래스 | px |
|---|---|---|
| 페이지 제목 | `text-xl font-bold` | 20 |
| 섹션 헤더 | `text-sm font-bold` | 14 |
| 본문 | `text-sm` | 14 |
| 캡션/기본 라벨 | `text-xs` | 12 |
| 작은 라벨 (KPI 카드) | `text-[11px]` | 11 |
| 메타데이터 (날짜 등) | `text-[10px]` | 10 |
| KPI 대형 수치 | `text-2xl font-bold` | 24 |

### ❌ 금지 사이즈
- `text-[9px]` 이하 — 가독성 0, 사용 금지
- `text-[13px]`, `text-[17px]` 등 비표준 사이즈

### 웨이트
- `font-medium` (500) — 버튼, 중요 라벨
- `font-semibold` (600) — 섹션 제목
- `font-bold` (700) — 페이지 제목, KPI 수치
- **400(normal), 800(extrabold)은 쓰지 않음**

### 숫자 렌더링
- 모든 수치 컬럼은 `tabular-nums` 클래스 필수 (정렬 맞춤)
- 수치 강조: `font-bold` + 색상 (`text-blue-600` 등)

---

## 4. 공간 시스템

### 스케일 (4px 기반)
Tailwind 기본 스케일만 사용. 커스텀 값 금지.

| 크기 | 용도 |
|---|---|
| `1` (4px) | 아이콘-텍스트 간격 |
| `2` (8px) | 인라인 요소 간격 |
| `3` (12px) | 카드 내부 기본 여백 |
| `4` (16px) | 카드 외부 간격, 섹션 내부 |
| `5` (20px) | 페이지 외곽 여백 |
| `6` (24px) | 큰 섹션 구분 |

### 카드 내부 구조
```
카드: p-3 (작은 카드) / p-4 (기본) / p-5 (큰 카드)
카드 사이: gap-2 (밀집) / gap-3 (기본) / gap-4 (넓게)
섹션 내부: space-y-3 (기본) / space-y-4 (여유)
```

### ❌ 금지
- `p-7`, `p-9`, `px-5` 등 비표준 spacing (Tailwind 기본 값만)
- `mt-10` 이상 큰 margin (`py-10` 등은 레이아웃 재검토)

---

## 5. 컴포넌트 패턴

### Card (기본)
```html
<div class="bg-white border border-slate-200 rounded-lg p-4">
  <!-- 내용 -->
</div>
```
**변형:**
- 색상 강조 카드: `border-l-4 border-l-{color}-400`
- 밀집 카드: `p-3 rounded-md`
- 대형 카드: `p-5 rounded-lg`

### Section Header (카드 상단 헤더)
```html
<div class="flex items-center gap-2 px-3 py-2 bg-sky-50 border-b border-sky-100">
  <span class="w-1 h-4 bg-sky-500 rounded-full"></span>
  <h3 class="text-sm font-bold text-sky-700">섹션 제목</h3>
  <span class="text-[11px] text-slate-500 ml-auto">메타데이터</span>
</div>
```

### Button
```html
<!-- Primary -->
<button class="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50">
  저장
</button>

<!-- Secondary -->
<button class="px-3 py-1.5 border border-slate-300 text-slate-700 text-sm rounded hover:bg-slate-50">
  취소
</button>

<!-- Ghost -->
<button class="px-2 py-1 text-slate-500 text-xs hover:text-slate-700">
  더보기
</button>

<!-- Toggle (active/inactive) -->
<button :class="isActive ? 'bg-blue-600 text-white' : 'bg-white text-slate-600'"
  class="px-3 py-1 text-xs rounded border">플레이스</button>
```

### Badge
```html
<!-- 작은 배지 -->
<span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-100 text-blue-700">
  NEW
</span>

<!-- 기본 배지 -->
<span class="inline-block px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-700">
  성공
</span>

<!-- Chip (클릭 가능) -->
<button class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 text-xs">
  강남유앤아이 ×
</button>
```

### Input
```html
<input class="px-2.5 py-1 border border-slate-300 rounded text-xs focus:border-blue-400 focus:outline-none" />
```

### Table (데이터 테이블)
```html
<div class="bg-white border border-slate-200 rounded-lg overflow-auto max-h-[600px]">
  <table class="text-xs whitespace-nowrap">
    <thead>
      <tr class="bg-slate-50 border-b sticky top-0 z-10">
        <th class="text-left pl-3 py-2 font-medium text-slate-500 cursor-pointer hover:text-slate-700 sticky left-0 bg-slate-50 z-20">
          지점
        </th>
        <!-- ... -->
      </tr>
    </thead>
    <tbody>
      <tr class="border-b border-slate-100 hover:bg-blue-50/30">
        <td class="pl-3 py-1.5 text-slate-700 font-medium sticky left-0 bg-white">강남</td>
      </tr>
    </tbody>
  </table>
</div>
```
**필수 조건:**
- `max-h-[600px]` + `overflow-auto` — 높이 제한
- 헤더 `sticky top-0` — 스크롤 시 고정
- 지점/ID 컬럼 `sticky left-0` — 가로 스크롤 시 고정
- 본문 hover: `hover:bg-blue-50/30`
- `whitespace-nowrap` + min-width로 긴 컨텐츠 대응

### Tab Bar
```html
<div class="flex gap-1 mb-4 border-b border-slate-200">
  <button
    :class="activeTab === 'A' ? 'border-slate-700 text-slate-800' : 'border-transparent text-slate-400 hover:text-slate-600'"
    class="px-3 py-2 text-sm font-medium transition border-b-2 -mb-px">
    탭 이름
  </button>
</div>
```

### Loading State
```html
<div class="flex items-center justify-center py-8">
  <div class="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
</div>
```

### Empty State
```html
<div class="text-center py-8">
  <p class="text-sm text-slate-400">데이터가 없습니다</p>
  <button class="mt-2 text-xs text-blue-600 hover:text-blue-700">추가하기</button>
</div>
```

### Error / Warning Overlay
```html
<div class="flex flex-col items-center justify-center flex-1">
  <p class="text-lg font-semibold text-slate-600 mb-1">금일 데이터는 아직 갱신되지 않았습니다</p>
  <p class="text-sm text-slate-400">다른 날짜를 선택하여 이전 데이터를 확인할 수 있습니다</p>
</div>
```

### Dropdown (클릭 팝업)
```html
<div class="relative" data-dropdown>
  <button @click="toggle">트리거 ▾</button>
  <div v-if="open" class="absolute top-full left-0 mt-1 z-20 bg-white border border-slate-200 rounded shadow-md py-1 min-w-max">
    <!-- 하단 공간 부족 시 bottom-full mb-1 사용 -->
    <button class="block w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-blue-50">옵션 1</button>
  </div>
</div>
```

---

## 6. 레이아웃 원칙

### 6.0 디자인 우선순위 (운영 도구 컨텍스트)

uni-portal은 데이터 운영 도구다. 마케팅·브랜드 사이트가 아니다. 디자인 결정 충돌 시 우선순위:

1. **정렬 (Alignment)** — 행열 격자, 컬럼 폭 통일, `tabular-nums`
2. **사시 모드 회피** — 컬럼 사이 거대 공백 X, 빈 영역 X
3. **정보 식별** — 채널 색, 카테고리 라벨 (즉시 구분)
4. **시각 계층** — 핵심 vs 보조 (1-3을 해친다면 후순위)
5. **alert 강조 / 아이콘** — 정말 필요할 때만. 평소엔 노이즈

> **핵심 통찰 — 정렬이 시각 계층보다 우선이다.**
> 디자이너 본능으로 ⚠ 아이콘·KPI 사이즈 강조를 추가하기 전에, 행열이 정확히 격자로 정렬되었는지 먼저 확인.

---

### 6.1 페이지 컨테이너 — 12 컬럼 그리드 시스템

**페이지의 모든 섹션은 같은 12 컬럼 그리드 시스템 위에 놓인다.**
이게 "각 섹션의 우측 끝이 일치"하는 시각 일관성의 본질.

#### 표준 패턴

```html
<div class="p-5 max-w-7xl">  <!-- 페이지 wrapper -->
  <!-- 헤더 -->
  <div class="mb-6">...</div>

  <!-- 섹션 1: 카드 3개 -->
  <h3>섹션 헤더</h3>
  <div class="grid grid-cols-12 gap-4 mb-10">
    <div class="col-span-12 sm:col-span-4">카드 1</div>
    <div class="col-span-12 sm:col-span-4">카드 2</div>
    <div class="col-span-12 sm:col-span-4">카드 3</div>
  </div>

  <!-- 섹션 2: 카드 4개 -->
  <h3>섹션 헤더</h3>
  <div class="grid grid-cols-12 gap-3 mb-10">
    <div class="col-span-6 sm:col-span-3">카드 1</div>
    <div class="col-span-6 sm:col-span-3">카드 2</div>
    <div class="col-span-6 sm:col-span-3">카드 3</div>
    <div class="col-span-6 sm:col-span-3">카드 4</div>
  </div>

  <!-- 섹션 3: 카드 2개 -->
  <h3>섹션 헤더</h3>
  <div class="grid grid-cols-12 gap-4">
    <div class="col-span-12 sm:col-span-6">카드 1</div>
    <div class="col-span-12 sm:col-span-6">카드 2</div>
  </div>
</div>
```

#### 섹션 안 카드 분할 표준

| 카드 개수 | col-span | 합계 |
|---|---|---|
| 2개 | `col-span-6` × 2 | 12 |
| 3개 | `col-span-4` × 3 | 12 |
| 4개 | `col-span-3` × 4 | 12 |
| 6개 | `col-span-2` × 6 | 12 |
| 비균등 | `col-span-8` + `col-span-4` 등 | 12 (콘텐츠 양 비례) |

**작은 화면(sm 미만) 대응**: `col-span-12` 또는 `col-span-6`로 wrap 자연 발생.

#### 페이지 컨테이너 max-width

`max-w-7xl` (1280px) 권장. 이유:
- 1500px+ 모니터에서 콘텐츠가 좌측에 모임 (우측 자연 공백, 사이드바 옆 자연스러움)
- 1024~1280px 모니터에선 자연 신축 (반응형)
- Linear/Notion/Stripe 같은 잘 만든 웹앱의 표준 폭

`max-w-screen-2xl` (1536px)는 4K 모니터에서, `max-w-5xl` (1024px)는 좁은 페이지(설정·폼 등)에 사용.

---

### 6.2 4가지 레이아웃 모드

페이지 컨테이너 + 12 컬럼 grid 위에서, 콘텐츠 본성에 맞는 모드를 선택한다.

#### Reading mode — 텍스트·폼·1열 리스트
- **콘텐츠 본성**: 한 줄에 너무 많은 글자가 들어가면 가독성이 떨어지는 콘텐츠
- **클래스 패턴**: `max-w-2xl mx-auto` 또는 `max-w-prose mx-auto`
- **이유**: 한 줄 60~75자가 가독성 최적
- **적용**: 사용자 프로필, 설정 폼, 블로그 본문
- **컴포넌트**: `<PageLayout mode="reading">`

#### Table mode — 데이터 테이블
- **콘텐츠 본성**: 컬럼 자연 너비의 합이 적정 폭
- **표준 패턴**:
  ```html
  <PageLayout mode="table">
    <div class="bg-white border border-slate-200 rounded-lg">
      <table class="text-xs">  <!-- ⚠ w-full 절대 금지 -->
        ...
      </table>
    </div>
  </PageLayout>
  ```
  - `PageLayout mode="table"`이 자동 적용: `overflow-x-auto w-fit max-w-full`
  - `<table>`에 `w-full` 금지 — 테이블이 콘텐츠 폭으로 응축
- **적용**: 키워드 관리, 측정 이력, 동기화 로그, 사용자 목록
- **검증**: 테이블 우측 끝 컬럼이 컬럼 사이 거대 공백을 두고 화면 우측에 붙어있다면 `w-full`이 들어간 것

#### Detail mode — 마스터 + 사이드
- **콘텐츠 본성**: 메인 콘텐츠 + 우측 보조 패널
- **클래스 패턴**: `flex flex-col lg:flex-row gap-6`
  - 메인: `flex-1 min-w-0` 또는 `min-w-0` (콘텐츠 자연 폭)
  - 사이드: `w-full lg:w-80 flex-shrink-0` (고정)
- **사이드는 inline (overlay X)** — 본 콘텐츠 가리지 않음
- **적용**: SB체커 체크 이력, 메일 인박스
- **컴포넌트**: `<PageLayout mode="detail">`

#### Dashboard mode — 12 컬럼 그리드 카드
- **콘텐츠 본성**: 여러 KPI/위젯 카드 한 화면
- **표준 패턴**: `grid grid-cols-12 gap-4` + 카드별 `col-span-N`
- **이유**: 모든 카드가 같은 12 컬럼 시스템에서 분할 → 섹션 간 우측 끝 일치
- **적용**: 홈 대시보드, 관리자 통계 패널

---

### 6.3 같은 섹션 카드 폭 통일 (필수 룰)

**같은 섹션 안 카드는 모두 같은 `col-span`을 사용한다.**

```html
<!-- ✓ OK -->
<div class="grid grid-cols-12 gap-4">
  <div class="col-span-4">카드 A</div>
  <div class="col-span-4">카드 B</div>
  <div class="col-span-4">카드 C</div>
</div>

<!-- ✗ 사용자가 정렬 깨짐으로 인식 -->
<div class="grid grid-cols-12 gap-4">
  <div class="col-span-5">카드 A (콘텐츠 많아서)</div>
  <div class="col-span-3">카드 B</div>
  <div class="col-span-4">카드 C</div>
</div>
```

**예외**: 콘텐츠 양이 명확히 다른 의미일 때 (예: 메인 vs 사이드). 이 경우 `col-span-8 + col-span-4` 비율 사용.

---

### 6.4 카드 안 정보 분할

카드 폭이 정해진 후, **카드 안 콘텐츠가 카드 폭의 절반 이상을 차지하도록** 한다.

```html
<!-- ✓ 카드 폭 50/50 분할로 콘텐츠가 카드를 채움 -->
<div class="grid grid-cols-2 gap-3">
  <span>라벨</span>
  <span>값</span>
</div>

<!-- ✗ 콘텐츠가 카드 폭의 1/3만 차지하고 우측 빈 공간 -->
<div class="flex gap-4">
  <span>라벨</span>
  <span>값</span>
</div>
```

**카드 폭이 콘텐츠보다 훨씬 크면** (콘텐츠가 카드의 50% 이하):
- 카드 안 grid를 카드 폭에 맞춰 N분할
- 또는 카드 폭을 줄이는 게 적합한지 재검토 (col-span을 작게)

---

### 6.5 row 정렬 — grid > flex

라벨 폭이 다양하면 (예: "SB체커" vs "플레이스 (오후)" vs "일별 스냅샷"):

```html
<!-- ✗ flex gap-4 — 라벨 다음 정보 시작점이 row마다 다름 -->
<div class="flex gap-4">
  <span>라벨</span>
  <span>시각</span>
</div>

<!-- ✓ grid-cols-2 또는 grid-cols-[Npx_auto] — 시작점 일관 -->
<div class="grid grid-cols-2 gap-3">
  <span>라벨</span>
  <span>시각</span>
</div>
```

**검증 룰**: 같은 카드 안 row들의 두 번째 정보(시각/숫자/뱃지)가 정확히 같은 가로 위치에 있어야 한다.

---

### 6.6 반응형 브레이크포인트

```
sm: 640px   (태블릿 세로) — Dashboard 카드 col-span 분할 시작점
md: 768px   (태블릿 가로)
lg: 1024px  (데스크톱 기본) — Detail mode가 stack→side 전환
xl: 1280px  (와이드) — max-w-7xl 도달
```

**원칙**: 관리 툴은 데스크톱 우선. sm 미만에서는 모든 카드 `col-span-12` (1열 stack), sm 이상에서 `sm:col-span-N`로 분할.

---

### 6.7 ❌ 금지 패턴

- **페이지 wrapper에 너무 좁은 max-w** (예: `max-w-3xl`=768px 이하) — 1500px 모니터에서 좌우 광활한 공백, 사시 모드. `max-w-7xl`(1280px) 권장
- **페이지 안 섹션마다 다른 grid 시스템** — 섹션 간 우측 끝 안 맞음. 12 컬럼 통일 필수
- **`justify-between`으로 좌·우 끝에만 정보 배치** — 사시 모드의 주범
- **빈 컬럼 / 빈 영역** — 조건부 렌더링으로 제거
- **사이드 overlay** — 본 콘텐츠 가림. inline aside로
- **테이블에 `w-full`** — 사시 모드의 주범 (Table mode 참고)
- **flex gap-N으로 라벨 폭 가변 row** — row마다 정보 위치 다름. grid로

---

### 6.8 Flex vs Grid

- **Grid**: Dashboard mode (12 컬럼), 카드 안 정보 분할, row 정렬
- **Flex**: Detail mode (메인+사이드), 단일 라인 정렬, 자연 폭 조합

---

### 6.9 Z-index 스케일

```
z-0:  기본
z-10: sticky 헤더
z-20: 드롭다운, 팝오버
z-30: 모달 오버레이
z-40: 토스트 알림
z-50: 드래그 중인 요소
```

### 마이그레이션 우선순위

| 페이지 | 현재 | 권고 모드 | 우선순위 |
|---|---|---|---|
| SB체커 체크 이력 | max-w-4xl 하드코딩 + overlay aside | Detail (inline aside) | 높음 (이번 작업) |
| SB체커 키워드 관리 | 화면 전체 | Table | 높음 |
| 홈 대시보드 | 화면 전체 + grid | Dashboard | 중간 |
| 플레이스/웹페이지 탭 | max-w-3xl | Reading or Table 재검토 | 낮음 |
| 사용자 관리/설정 | 미상 | Reading | 낮음 |
| 관리자 모드 탭들 | 화면 전체 | 탭별 모드 (Table or Reading) | 중간 |

신규 페이지는 **무조건 PageLayout 컴포넌트 사용**.

---

## 7. 상태 표현 (필수)

모든 데이터 뷰는 다음 4가지 상태를 명시적으로 처리:

### Loading
```html
<LoadingSpinner />  <!-- 공통 컴포넌트 -->
<!-- 또는 인라인 -->
<div class="text-center py-8 text-sm text-slate-400">로딩 중...</div>
```

### Empty (데이터 없음)
```html
<EmptyState message="데이터가 없습니다" />
<!-- 또는 -->
<div class="text-center py-8">
  <p class="text-sm text-slate-400">아직 등록된 항목이 없습니다</p>
  <button class="mt-2 text-xs text-blue-600">추가하기</button>
</div>
```

### Error
```html
<div class="px-3 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
  {{ errorMessage }}
</div>
```

### Success (일시적 알림)
```html
<div class="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-700">
  {{ successMessage }}
</div>
```
자동 사라짐: `setTimeout(() => message = '', 3000)`

---

## 8. AI Slop 블랙리스트

**아래 패턴이 보이면 AI 생성된 느낌이 나므로 반드시 피할 것:**

| ❌ 금지 패턴 | ✅ 대안 |
|---|---|
| **사시 모드 레이아웃** (정보가 좌우로 멀리 떨어짐) | **섹션 2.5 참조** — 폭 줄이기, 1열 우선 |
| 그라데이션 배경 (`bg-gradient-to-r`) | 플랫 컬러 (`bg-slate-50`) |
| 보라/바이올렛 강조 (`purple-500`) | indigo 또는 blue |
| 아이콘 원형 배경 (`rounded-full bg-blue-100 p-3 + 아이콘`) | 텍스트 라벨 또는 얇은 아이콘만 |
| 모든 요소 `rounded-xl` (과한 둥글기) | `rounded` (4px) 또는 `rounded-lg` (8px) |
| 이모지 장식 (🎉, 🚀 등) | 단어만 사용 |
| 장식용 블롭/곡선 SVG | 삭제 |
| "모든 것을 한 곳에서" 같은 포괄적 카피 | 구체적 동사 ("지점 추가", "데이터 동기화") |
| 3열 feature grid (icon + 제목 + 설명) | 실제 데이터 또는 기능 버튼 |
| `text-center` 남발 (카드 내부 전부 가운데) | 좌측 정렬 기본, 수치만 가운데 |
| 콜로어 레프트 보더 없는 색상 카드 | `border-l-4 border-l-{color}-400` |
| `justify-between` + 2개 요소 (공허하게 벌어짐) | `flex gap-3` + `ml-auto` |
| `p-8`+ 큰 패딩의 작은 카드 | `p-3` ~ `p-4` |
| `space-y-6`+ 큰 수직 여백 | `space-y-3` ~ `space-y-4` |

### 셀프 체크 질문
새 화면을 만들고 나서 다음 질문에 답해보세요:
1. 이 화면을 Linear / Notion / Airtable에 갖다 놓아도 튀지 않는가?
2. "어디 SaaS 템플릿에서 본 것 같다"는 느낌이 드는가? → 재작업
3. 장식을 다 지워도 기능이 유지되는가? → 장식 삭제

---

## 9. 리팩토링 체크리스트

기존 페이지를 DESIGN.md 기준으로 맞출 때 순서:

```
□ 1. 페이지 너비 (max-w-*) 검토
□ 2. 색상 → 섹션 2의 palette로 통일
□ 3. 폰트 사이즈 스케일 정리 (text-[9px] 금지 등)
□ 4. 카드/버튼/배지 → 섹션 5 패턴 적용
□ 5. 테이블에 sticky 헤더 + sticky 좌측 컬럼
□ 6. 상태(Loading/Empty/Error) 명시적 처리
□ 7. AI Slop 블랙리스트 검증
□ 8. Before/After 스크린샷 비교 → 커밋
```

---

## 10. 예외 처리 원칙

이 문서와 다른 디자인이 필요할 때:
1. **먼저 "왜 다른 규칙이 필요한지" 생각** — 같은 문제를 기존 규칙으로 해결 가능한가?
2. 꼭 필요하면 **DESIGN.md에 규칙 추가** — 예외는 문서화해야 규칙이 된다
3. 문서 수정 없이 만든 예외는 나중에 일관성 무너뜨림

---

## 변경 이력
- 2026-04-14: 최초 작성 (기준: 관리자 대시보드)
