# 시술사전 관리 가이드

## 1. 시스템 구조

```
장비 데이터 (equipment.db / equipment 테이블)
    └── 기기명 (예: "써마지FLX", "온다(바디)", "울쎄라")
           │
           ▼  매칭 엔진 (find_matching_devices)
           │
    시술사전 (equipment.db / device_info 테이블)  ← 여기를 관리
           │
    별칭 사전 (config.py / DEVICE_ALIASES)        ← 폴백 매칭용
```

### 매칭 흐름 (조회 버튼 클릭 시)

1. 괄호 부위 제거: `온다(바디)` → `온다`
2. `find_matching_devices(core_name)` 실행
   - 정확 매칭 (써마지FLX == 써마지FLX)
   - 포함 매칭 + 한글 경계 체크 (써마지FLX → 써마지 ✅, 울쎄라 → 울쎄라피 ✗)
   - aliases 매칭 (DB aliases 필드)
3. 실패 시 `DEVICE_ALIASES` 폴백 (config.py)
4. 정확 매칭 존재 시 부모 항목 숨김

### 한글 경계 규칙

부분 매칭 시 경계 다음 문자가 **한글**이면 다른 기기로 판단:
- `써마지` ⊂ `써마지FLX` → FLX는 영문 → **같은 계열** ✅
- `울쎄라` ⊂ `울쎄라피` → 피는 한글 → **다른 기기** ✗

---

## 2. 관리 대상 파일

### 파일 A: `equipment.db` → `device_info` 테이블

시술/장비의 **정보 본체**. 앱 관리자 UI(사용자 관리 → 📖 시술사전)에서 편집 가능.

| 컬럼 | 설명 | 예시 |
|------|------|------|
| `name` | 정식 시술명 (PK, 유니크) | `써마지FLX` |
| `category` | 카테고리 | `리프팅`, `색소`, `주사 시술` |
| `summary` | 한 줄 설명 | `고주파 열로 피부 콜라겐을 수축...` |
| `target` | 적용 부위/증상 | `피부 탄력 저하, 잔주름, 모공` |
| `mechanism` | 작용 원리 | `단극 고주파(RF)로 진피층...` |
| `note` | 참고사항 | `FLX는 4세대 모델` |
| `aliases` | 쉼표 구분 별칭 | `써마지FLX, 써마지 FLX, 미니 써마지` |
| `usage_count` | 보유 지점 수 (자동 계산) | `35` |
| `is_verified` | 검증 완료 여부 (0/1) | `1` |

### 파일 B: `config.py` → `DEVICE_ALIASES`

매칭 **폴백용** 별칭 사전. `find_matching_devices`가 실패했을 때 사용.

```python
DEVICE_ALIASES = {
    "정식명": ["변형1", "변형2", ...],
    "온다리프팅": ["온다리프팅", "온다 리프팅"],  # "온다"는 별칭에 없어도 폴백으로 매칭됨
}
```

---

## 3. 새 시술 추가 체크리스트

### Step 1: device_info에 추가

관리자 UI 또는 Python으로:

```python
from equipment.db import upsert_device_info

upsert_device_info(
    name="아쿠아필",           # 정식명
    category="스킨케어",       # 카테고리
    summary="...",            # 한 줄 설명
    target="...",             # 적용 부위
    mechanism="...",          # 작용 원리
    note="...",               # 참고
    aliases="아쿠아필, aquapeel",  # 변형 이름들
    is_verified=1,
)
```

### Step 2: DEVICE_ALIASES 추가 (필요 시)

약어/축약형이 한글 경계 규칙에 걸리는 경우만 추가:
- `온다` → `온다리프팅`: "온다" 뒤에 "리"(한글)가 오므로 자동매칭 안 됨 → DEVICE_ALIASES 필요
- `써마지` → `써마지FLX`: "써마지" 뒤에 "F"(영문)가 오므로 자동매칭 됨 → 불필요

```python
# config.py에 추가
"온다리프팅": ["온다리프팅", "온다 리프팅", "온다"],  # "온다" 추가
```

### Step 3: 검증

```python
from equipment.db import find_matching_devices
find_matching_devices("아쿠아필")  # 매칭 확인
```

---

## 4. 현황 (2026-03-13 기준)

### 등록 완료: 54개 시술

| 카테고리 | 시술 목록 |
|---------|----------|
| 리프팅 | 울쎄라피 프라임, 울쎄라, 써마지FLX, 써마지, 슈링크 유니버스, 인모드, 볼뉴머, 온다리프팅, 올리지오X, 브이로, 버츄, 실리프팅, 아쎄라, 올리디아, 울트라콜, 덴서티, 티타늄, 포텐자 |
| 색소/토닝 | 피코슈어, 피코플러스, 클라리티2, 클라리티 롱펄, 루카스, 리투오, 엑셀브이 |
| 제모 | 젠틀맥스, 아포지 |
| 주사 시술 | 보톡스, 필러, 리쥬란, 쥬베룩, 스킨바이브, 벨로테로, 물광주사, 더마샤인, 에토좀, 엑소좀, 미라젯, 쥬브아셀, 콜라움 |
| 바디 | 바디인모드, 셀르디엠, 노블쉐이프, 악센토 |
| 스킨케어 | 헐리우드, 리바이브, 라셈드, 레티젠 |
| 여드름 | 아그네스, 네오빔, 플래티넘PTT |
| 피부외과 | CO2 레이저 |

### 미등록 (빈도 5건 이상, 우선 등록 권장)

| 빈도 | 기기명 | 추정 카테고리 |
|------|--------|-------------|
| 40 | 아쿠아필 | 스킨케어 |
| 23 | 크라이오 | 관리기기 |
| 21 | 이온자임 | 관리기기 |
| 20 | LDM | 스킨케어/재생 |
| 17 | 더마브이 | 색소 |
| 11 | 라라필 | 스킨케어 |
| 11 | 트리플바디 | 바디 |
| 9 | 브이레이저 | 색소/혈관 |
| 8 | 티타늄리프팅 | 리프팅 (→ 티타늄 별칭?) |
| 7 | 디스포트 | 주사 시술 (보톡스 계열) |
| 7 | 루비레이저 | 색소 |
| 7 | 소노케어 | 관리기기 |
| 6 | 클라리티 프로 | 색소/제모 (→ 클라리티 계열) |
| 6 | 에어녹스 | 관리기기 |
| 6 | 리즈네 | 주사 시술 |
| 6 | 하이쿡스 | 바디 |
| 5 | 실펌X | 스킨/흉터 |
| 5 | 골드PTT | 여드름 |
| 5 | 쥬비덤 | 필러 |
| 5 | 카복시 | 관리 시술 |
| 5 | 피코하이 | 색소 |
| 5 | 에어샤인 | 주사/스킨케어 |
| 5 | 이브시너지 | 스킨케어 |

---

## 5. 주의사항

### 동명이기 구분

같은 이름이지만 다른 시술인 경우 괄호 부위로 구분됨:
- `인모드` = 얼굴 리프팅
- `인모드(바디)` = 바디 시술 → 매칭 시 `바디인모드`로 연결

시스템은 괄호 안 내용을 **부위 수식어**로 제거 후 매칭하므로, `바디인모드`는 별도 device_info 항목으로 존재해야 합니다.

### 계열 기기 등록 원칙

| 관계 | 예시 | 등록 방법 |
|------|------|----------|
| 세대 차이 (영문 접미) | 써마지 / 써마지FLX | 각각 별도 항목. 자동매칭됨 |
| 세대 차이 (한글 접미) | 울쎄라 / 울쎄라피 프라임 | 각각 별도 항목. DEVICE_ALIASES도 별도 |
| 모델 변형 | 올리지오 / 올리지오X | 하위 모델(X)만 등록, aliases에 상위명 포함 |
| 축약형 | 온다 = 온다리프팅 | DEVICE_ALIASES에 축약형 추가 |
| 부위 구분 | 인모드 / 바디인모드 | 각각 별도 항목 |

### DB 스키마 (참고)

```sql
CREATE TABLE device_info (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,    -- 정식 시술명
    category    TEXT DEFAULT '',         -- 카테고리
    summary     TEXT DEFAULT '',         -- 한 줄 설명
    target      TEXT DEFAULT '',         -- 적용 부위/증상
    mechanism   TEXT DEFAULT '',         -- 작용 원리
    note        TEXT DEFAULT '',         -- 참고사항
    aliases     TEXT DEFAULT '',         -- 쉼표 구분 별칭
    usage_count INTEGER DEFAULT 0,      -- 보유 지점 수
    is_verified INTEGER DEFAULT 0,      -- 검증 여부
    created_at  TIMESTAMP,
    updated_at  TIMESTAMP
);
```

### 관련 함수 (equipment/db.py)

| 함수 | 용도 |
|------|------|
| `upsert_device_info(name, ...)` | 추가/수정 |
| `delete_device_info(name)` | 삭제 |
| `get_all_device_info()` | 전체 목록 |
| `search_device_info(keyword)` | 키워드 검색 |
| `find_matching_devices(equip_name)` | 양방향 매칭 (조회 다이얼로그용) |
| `update_device_usage_counts()` | 보유수 일괄 갱신 |
| `seed_device_info_from_config()` | config.py → DB 시딩 |
