# uni-portal 프로젝트 규칙

이 파일은 모든 작업(Claude 본 + 서브에이전트)에 자동 적용되는 프로젝트 규칙이다. 글로벌 규칙(`~/.claude/CLAUDE.md`) 위에서 동작한다.

---

## 백엔드/프론트엔드 책임 분리 (MUST)

비즈니스 로직과 데이터 계산은 **백엔드가 단일 책임**으로 처리한다.
프론트엔드는 받은 데이터를 **표시·정렬·인터랙션**만 한다.

### 예외 (프론트엔드에서 처리 OK)
- 표시 포맷팅: 가격 `12000` → `12,000원`, 날짜 포맷
- 이미 받은 데이터의 정렬/필터/검색 (사용자가 컬럼 클릭, 검색창 입력)
- UI 상태: 모달 열림/닫힘, 호버, 탭 전환
- 로컬 입력 검증 보조 (단, **서버도 반드시 검증**)

### 판단 기준
> "이 기준이 바뀌면 백엔드만 고치면 충분한가?"
> YES → 백엔드. NO (프론트도 같이) → 룰 위반.

### 사례 (2026-04)
플레이스 회복 표시 `recovery_active` 단일 boolean으로 백엔드에서 결정.
이전에는 `recovery_date`/`recovery_gap`을 백엔드가 주고 프론트가 "오늘 성공 + 7일 이내" 조건을 추가 판정 → 기준 바꿀 때 양쪽 다 고쳐야 함 → 깨지기 쉬움.

---

## 시각 저장 규칙 (MUST)

DB에 시각 저장 시 다음 룰 준수:

- **항상 KST 명시**: `datetime.now().strftime("%Y-%m-%d %H:%M:%S")` 사용
- **SQLite DEFAULT CURRENT_TIMESTAMP 사용 금지**: SQLite는 timezone-aware하지 않고 항상 UTC를 반환. 컨테이너 TZ가 KST여도 무관.
- **sync_log 기록은 `shared.db.log_sync()` 헬퍼 사용**: 직접 INSERT 금지

### 사례 (2026-05-04)
equipment/events/cafe sync가 sync_log INSERT 시 synced_at 컬럼 미명시 → SQLite DEFAULT CURRENT_TIMESTAMP(UTC)가 들어가 KST보다 9시간 빠름. 같은 테이블에 KST(place/webpage/SB체커) + UTC(equipment/events/cafe)가 혼재되어 사용자가 "오전 9시"로 착각.

판단 기준:
> "이 시각을 사용자가 보거나 다른 시각과 비교하나?" YES → KST 명시 필수.
