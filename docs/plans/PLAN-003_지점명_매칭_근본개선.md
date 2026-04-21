# PLAN-003 · 지점명 매칭 근본 개선

> 작성일: 2026-04-21
> 선행: Phase 1 — `shared/branch_resolver.py` 신설 + 주요 라우터 resolver 교체 완료
> 목적: 문자열 퍼지 매칭에 의존하는 지점명 해석 로직을 **FK 기반 구조**로 전환하여 정확도·성능·확장성을 확보

---

## 1. 개요

### 왜 Phase 2가 필요한가

Phase 1에서 `shared/branch_resolver.py`를 신설해 퍼지 매칭의 오판(광주점 vs 경기광주점 혼용 등)을 억제했다. 그러나 resolver는 어디까지나 **런타임 문자열 해석 레이어**다. 근본 문제는 DB 레벨에 남아 있다.

현재 구조의 한계:

- `place_daily`, `webpage_daily`의 `evt_branch_id` FK가 비어있어 **모든 조회가 `branch_name` 문자열에 의존**한다.
- resolver가 매번 전체 `evt_branches`를 읽어 이름을 비교하므로 **O(N) 반복**이 발생한다.
- 프론트엔드는 `branch_name`에서 브랜드 접두어를 직접 제거하는 **하드코딩 로직**을 갖고 있어, 브랜드명이 바뀌면 즉시 깨진다.
- `events/db.py`는 여전히 `LIKE` 퍼지 매칭을 사용해 이벤트 지점 매핑 정확도가 불확실하다.

Phase 2는 이 빈틈을 DB 스키마 + API 계층에서 닫는 작업이다.

---

## 2. Phase 1 완료 요약

| 파일 | 변경 내용 |
|---|---|
| `shared/branch_resolver.py` | 신설. `resolve_evt_branch_id()`, `list_branch_names_for()` 공용 유틸 제공 |
| `api/routers/explorer.py` | 3차 폴백을 resolver 기반으로 교체 → 광주/경기광주 분리 정확 |
| `api/routers/place.py` | 휴식 판정에 resolver 사용 |
| `reports/autofill.py` | 휴식·이탈 계산에 resolver 사용 |

Phase 1은 **런타임 정확도 확보**에 집중했고, 스키마·프론트 하드코딩·`LIKE` 잔재는 Phase 2 대상으로 남겼다.

---

## 3. Phase 2 작업 범위

### 작업 A — `place_daily.evt_branch_id` FK 채우기

#### 문제 상황
구글 시트 동기화 시 `branch_name`('광주유앤아이' 등 시트 원본값)만 저장하고 `evt_branch_id`는 채우지 않는다. 결과적으로 `evt_branch_id`가 전 레코드 0/NULL이고, 조회마다 resolver가 재해석한다.

#### 해결 방안
동기화 스크립트(`sync/place_sync.py` 등)에서 행 삽입·갱신 시 resolver를 호출해 FK를 즉시 확정한다.

```python
branch_id = resolve_evt_branch_id(conn, row["branch_name"])
# INSERT or UPDATE 시 evt_branch_id = branch_id
```

기존 레코드는 일회성 마이그레이션 스크립트로 일괄 보정한다.

```sql
UPDATE place_daily
SET evt_branch_id = (
    SELECT id FROM evt_branches
    WHERE place_daily.branch_name LIKE '%' || short_name || '%'
    LIMIT 1
)
WHERE evt_branch_id IS NULL OR evt_branch_id = 0;
```

> 마이그레이션 후 resolver 불일치 케이스는 별도 확인 필요 (→ 리스크 참조).

#### 예상 난이도
🟡 중 — 동기화 코드 수정 자체는 쉽지만, 기존 레코드 마이그레이션 후 FK 0이 남는 케이스를 검증해야 함

#### 의존성
없음 (독립 시작 가능)

#### 영향받는 파일
- `sync/place_sync.py` (또는 해당 동기화 모듈)
- `shared/branch_resolver.py` (재사용)
- `equipment.db` — `place_daily` 테이블 마이그레이션

---

### 작업 B — `webpage_daily.evt_branch_id` FK 채우기

#### 문제 상황
작업 A와 동일한 구조. `webpage_daily`도 `branch_name` 문자열만 있고 FK가 비어있다.

#### 해결 방안
작업 A와 동일한 패턴을 `webpage_daily` / `sync/webpage_sync.py`에 적용한다.

#### 예상 난이도
🟢 하 — 작업 A 완료 후 동일 패턴 반복 적용

#### 의존성
작업 A 완료 후 진행 권장 (패턴 검증 후)

#### 영향받는 파일
- `sync/webpage_sync.py` (또는 해당 동기화 모듈)
- `equipment.db` — `webpage_daily` 테이블 마이그레이션

---

### 작업 C — `events/db.py` LIKE 퍼지 매칭 교체

#### 문제 상황
이벤트 지점 조회에서 `WHERE name LIKE ? OR short_name LIKE ?` 퍼지 매칭을 사용한다. 지점명이 비슷한 경우(광주/경기광주) 오매칭 위험이 있고, resolver의 정확도 개선이 이벤트 쪽에는 반영되지 않은 상태다.

#### 해결 방안
`evt_branches` 조회 시 정확 매칭 우선, 폴백 시에도 resolver를 통해 일관된 로직을 사용한다.

```python
# 변경 전
WHERE name LIKE ? OR short_name LIKE ?

# 변경 후 — resolver 경유
branch_id = resolve_evt_branch_id(conn, input_name)
WHERE id = ?  -- branch_id 사용
```

#### 예상 난이도
🟡 중 — `events/db.py` 내 매칭 호출 지점이 여러 곳일 수 있어 영향 범위 사전 확인 필요

#### 의존성
`shared/branch_resolver.py` (Phase 1 완료, 즉시 재사용 가능)

#### 영향받는 파일
- `events/db.py`
- `api/routers/events.py` (반환값 변화 여부 확인)

---

### 작업 D — 블로그 `LIKE '%유앤%'` 매칭 정비

#### 문제 상황
`blog/post_queries.py`와 `api/routers/blog.py`에서 `LIKE '%유앤%'` 또는 `LIKE '%유앤아이%'` 형태로 브랜드 필터링을 한다. 현재는 단일 브랜드라 오매칭이 거의 없지만, 향후 브랜드명이 추가되거나 타 브랜드 데이터가 유입되면 필터가 무너진다.

#### 해결 방안
브랜드 필터를 하드코딩 문자열이 아닌 `evt_branches` 테이블 기반 화이트리스트로 교체한다. 단기적으로는 설정값(config)으로 분리하는 것도 허용.

```python
# 단기: 상수 분리
BRAND_PATTERNS = ["유앤아이", "유앤"]  # config로 이동

# 이상적: evt_branches에서 동적 로드
brand_names = [r["name"] for r in conn.execute("SELECT name FROM evt_brands")]
```

> `evt_brands` 테이블이 없으면 신설 검토.

#### 예상 난이도
🟡 중 — 당장 오류는 없지만 구조 설계 결정(상수 분리 vs 테이블화)이 필요

#### 의존성
없음 (독립 진행 가능, 단 작업 F의 aliases 검토와 함께 논의 권장)

#### 영향받는 파일
- `blog/post_queries.py`
- `api/routers/blog.py`

---

### 작업 E — 프론트엔드 `shortName()` 하드코딩 제거

#### 문제 상황
`PlaceView`, `WebpageView` 등에서 지점 표시명을 만들 때 아래와 같은 하드코딩이 있다.

```js
branch.replace('유앤아이', '').replace('유앤', '').trim()
```

브랜드명이 바뀌거나 복수 브랜드가 생기면 즉시 깨진다.

#### 해결 방안
`/api/branches` 엔드포인트(또는 기존 지점 목록 API)에서 `short_name`을 함께 내려주고, 프론트는 이 값을 표시에 사용한다.

```ts
// API 응답 예시
{ id: 3, name: "광주유앤아이", short_name: "광주" }

// 프론트
const label = branch.short_name ?? branch.name;
```

#### 예상 난이도
🟡 중 — API 변경은 단순하나, 프론트 컴포넌트 사용처 전수 확인 필요

#### 의존성
작업 A 또는 B 이후 `evt_branch_id`가 채워져야 조회가 정확해짐 (선행 권장이나 독립 진행도 가능)

#### 영향받는 파일
- `frontend/src/views/PlaceView.vue` (또는 해당 컴포넌트)
- `frontend/src/views/WebpageView.vue`
- `api/routers/branches.py` (또는 지점 목록 라우터)

---

### 작업 F — `evt_branch_aliases` 테이블 도입 검토

#### 문제 상황
현재 `evt_branches`는 `name`('광주점')과 `short_name`('광주') 두 가지만 보유한다. 실제 시트에는 같은 지점이 '광주유앤아이', '광주유앤아이의원', '광주피부과' 등 여러 이름으로 기록될 수 있다. 이 다양성을 모두 resolver 코드에 if/elif로 때우면 유지보수가 어려워진다.

#### 해결 방안
```sql
CREATE TABLE evt_branch_aliases (
    id          INTEGER PRIMARY KEY,
    branch_id   INTEGER NOT NULL REFERENCES evt_branches(id),
    alias       TEXT NOT NULL UNIQUE,   -- 시트에 등장하는 원본 문자열
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

`resolve_evt_branch_id()`가 1차로 이 테이블을 정확 매칭하고, 없을 때만 기존 폴백 로직을 실행한다.

```python
row = conn.execute(
    "SELECT branch_id FROM evt_branch_aliases WHERE alias = ?", (raw_name,)
).fetchone()
if row:
    return row["branch_id"]
# 폴백: 기존 short_name 포함 매칭
```

신규 별칭은 관리자 UI 또는 마이그레이션 스크립트로 추가한다.

#### 예상 난이도
🔴 상 — 스키마 신설 + resolver 수정 + 관리 UI 또는 스크립트 필요. 분량이 가장 많음

#### 의존성
작업 A·B 이후 진행 권장. alias 정의가 먼저 안정화되어야 마이그레이션 정확도가 높아짐

#### 영향받는 파일
- `equipment.db` — `evt_branch_aliases` 테이블 신설
- `shared/branch_resolver.py` — alias 우선 조회 로직 추가
- 관리 스크립트 또는 어드민 API (신규)

---

## 4. 작업 순서 권장

의존성과 리스크를 고려한 단계별 순서다.

```
[1단계] 작업 A — place_daily FK 채우기
    └─ 가장 임팩트 크고 독립 시작 가능

[2단계] 작업 B — webpage_daily FK 채우기
    └─ 작업 A 패턴 확인 후 반복 적용

[3단계] 작업 C + D — events/db.py + blog LIKE 정비
    └─ 두 작업은 독립적이므로 병렬 진행 가능

[4단계] 작업 E — 프론트 shortName() 교체
    └─ 1~2단계 완료 후 API short_name 포함하여 진행

[5단계] 작업 F — aliases 테이블 (옵션)
    └─ 1~4단계 안정화 후 결정. 긴급하지 않으면 다음 Phase로 미룰 수 있음
```

| 단계 | 작업 | 예상 소요 | 선행 조건 |
|---|---|---|---|
| 1 | A — place FK | 1~2시간 | 없음 |
| 2 | B — webpage FK | 30분~1시간 | 작업 A |
| 3a | C — events LIKE | 1~2시간 | 없음 |
| 3b | D — blog LIKE | 30분~1시간 | 없음 |
| 4 | E — 프론트 shortName | 1~2시간 | 작업 A·B 권장 |
| 5 | F — aliases 테이블 | 3~5시간 | 작업 A·B·E |

---

## 5. 리스크

| 리스크 | 심각도 | 대응 |
|---|---|---|
| 마이그레이션 후 FK 0 잔존 (resolver가 해석 못한 지점명) | 🔴 높음 | 마이그레이션 후 `SELECT COUNT(*) WHERE evt_branch_id = 0` 확인. 수동 보정 목록 작성 |
| 작업 C에서 events LIKE 교체 시 기존 이벤트 누락 | 🔴 높음 | 교체 전 테스트 데이터로 반환값 동일성 검증 필수 |
| 작업 E 프론트 short_name이 NULL인 지점 존재 | 🟡 중간 | `short_name ?? name` 폴백 처리 + `evt_branches` 데이터 점검 |
| 작업 F aliases 초기 데이터 누락 | 🟡 중간 | 시트 `branch_name` 전수 추출 후 매핑 작업 (사람이 한 번 확인 필요) |
| 작업 D 브랜드 필터 교체 중 블로그 데이터 누락 | 🟢 낮음 | 단일 브랜드 환경에서 영향 제한적. 단, 교체 전후 카운트 비교 |

---

## 6. 다음 세션 체크리스트

### 시작 시 확인

- [ ] 본 문서 숙지
- [ ] `equipment.db` 현재 `place_daily`, `webpage_daily` 스키마 재확인
  ```sql
  PRAGMA table_info(place_daily);
  PRAGMA table_info(webpage_daily);
  ```
- [ ] `evt_branches` 현재 레코드 수 및 `short_name` 채움 여부 확인
  ```sql
  SELECT id, name, short_name FROM evt_branches;
  ```
- [ ] `place_daily.evt_branch_id = 0` 인 레코드 비율 파악
  ```sql
  SELECT COUNT(*) FROM place_daily WHERE evt_branch_id IS NULL OR evt_branch_id = 0;
  ```
- [ ] `sync/` 디렉토리에서 동기화 진입점 파일 확인 (place, webpage 각각)
- [ ] `events/db.py` LIKE 사용 지점 전수 확인 (`grep -n "LIKE"`)
- [ ] 프론트 `shortName` 또는 `replace('유앤')` 사용처 전수 확인

### 작업 중 주의사항

- [ ] 마이그레이션 스크립트는 **백업 후 실행** (`.db` 파일 복사본 보관)
- [ ] FK 채우기 완료 후 기존 API 응답값이 바뀌지 않는지 place/webpage 조회 smoke test
- [ ] 작업 E 진행 시 프론트 `shortName()` 제거 전 API에 `short_name` 포함 여부 먼저 확인
- [ ] 작업 F 결정 전 실제 시트 `branch_name` 변형 케이스를 사용자와 확인 (자동화 vs 수동 aliases 관리 방향 합의)

---

> 본 문서는 Phase 1 완료 직후 작성된 Phase 2 킥오프 근거입니다.
> 작업 A → B 순서로 시작하되, 마이그레이션 결과 검증 단계를 건너뛰지 마십시오.
