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

### 페이지 너비
| 페이지 유형 | max-width | 이유 |
|---|---|---|
| 밀집 대시보드 (KPI + 차트) | `max-w-4xl` (896px) | 밀도 유지 |
| 기본 관리 페이지 | `max-w-5xl` (1024px) | 균형 |
| 데이터 테이블 | `max-w-6xl` (1152px) | 컬럼 여유 |
| 전체 화면 앱 | `w-full` | 좌측 사이드바 있음 |

### 그리드 규칙
- **2열 배치**: 좌우 비교 (플/웹 나란히)
- **3-4열**: KPI 카드 (반응형 필수)
- **5열+**: 사용 금지 (모바일에서 깨짐)

### 반응형 브레이크포인트
```
sm: 640px   (태블릿 세로)
md: 768px   (태블릿 가로)
lg: 1024px  (데스크톱 기본)
xl: 1280px  (와이드)
```
**원칙**: 관리 툴은 데스크톱 우선. 모바일은 "읽을 수만 있음" 수준.

### Flex 우선
- Grid: 카드 그리드, 테이블
- Flex: 나머지 전부

### Z-index 스케일
```
z-0:  기본
z-10: sticky 헤더
z-20: 드롭다운, 팝오버
z-30: 모달 오버레이
z-40: 토스트 알림
z-50: 드래그 중인 요소
```

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
