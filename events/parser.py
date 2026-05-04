"""구글 시트 원시 데이터를 파싱하여 구조화된 이벤트 데이터로 변환하는 모듈.

각 지점 시트는 다음 구조를 가짐:
  - 상단: 제목 행 ("[지점명] 3-4월 이벤트")
  - ■ 카테고리 마커 행 (예: "■ 단독이벤트")
  - # 서브카테고리 마커 행 (예: "#레이저 리프팅") — 현재 DB 단일 카테고리이므로 덮어쓰기
  - 헤더 행: 이벤트명 | 정상가 | 최종 이벤트가 | 비고
  - 데이터 행들
  - (반복)
"""

import re
from dataclasses import dataclass, field

from events.price_parser import parse_price, calc_discount_rate


@dataclass
class ParsedEvent:
    """파싱된 이벤트 상품 한 건."""
    raw_event_name: str
    raw_category: str
    display_name: str
    regular_price: int | None
    event_price: int | None
    discount_rate: float | None
    notes: str
    session_count: int | None
    is_package: bool
    row_order: int
    components: list[str] = field(default_factory=list)


def extract_session_count(name: str) -> int | None:
    """이벤트명에서 회차 추출. 예: '모공잡기 3회' → 3"""
    match = re.search(r"(\d+)\s*회", name)
    if match:
        return int(match.group(1))
    return None


def detect_package(name: str) -> bool:
    """패키지(복합 시술) 상품인지 감지."""
    return "+" in name


def split_components(name: str) -> list[str]:
    """패키지 이벤트명을 개별 구성요소로 분리."""
    paren_match = re.search(r"\(([^)]+)\)", name)
    if paren_match:
        inner = paren_match.group(1)
        if "+" in inner:
            return [c.strip() for c in inner.split("+") if c.strip()]

    if ":" in name or "：" in name:
        after_colon = re.split(r"[:：]", name, maxsplit=1)[-1]
        if "+" in after_colon:
            return [c.strip() for c in after_colon.split("+") if c.strip()]

    if "+" in name:
        return [c.strip() for c in name.split("+") if c.strip()]

    return [name.strip()]


def _normalize_cell(cell: str) -> str:
    """멀티라인 헤더 셀 처리: 개행이 있으면 첫 줄만 반환."""
    return cell.split("\n")[0].strip()


def find_category_marker(row_text: str) -> str | None:
    """행 텍스트에서 ■ 또는 # 카테고리 마커를 찾아 카테고리명 반환.

    ■ 마커: 메인 카테고리
    # 마커: 서브카테고리 — 현재 DB 단일 카테고리라 그냥 덮어쓰기
    # 규칙: # 다음에 공백 또는 한글이 바로 오는 경우만 인정 (해시태그/URL의 # 제외)
    """
    if "■" in row_text:
        cleaned = row_text.replace("■", "").strip()
        return cleaned if cleaned else None

    # # 마커: 공백 또는 한글이 바로 뒤따르는 경우만 인정
    hash_match = re.match(r"#([ ㄱ-힣가-힣].*)$", row_text.strip())
    if hash_match:
        return hash_match.group(1).strip() or None

    return None


_NAME_KEYWORDS = {"이벤트명", "시술명", "상품명", "항목", "메뉴명"}
_REGULAR_KEYWORDS = {"정상"}    # "정상가", "정상 가격" etc.
_EVENT_PRICE_KEYWORDS = {"이벤트"}  # "이벤트가", "이벤트 제안가", "최종 이벤트가" etc.
_NOTES_KEYWORDS = {"비고", "참고", "메모", "설명", "특이사항", "관리 순서"}


def is_header_row(cells: list[str]) -> bool:
    """헤더 행 여부 판별 — 셀 단위로 이름 컬럼과 가격 컬럼을 각각 확인.

    멀티라인 셀은 첫 줄만 사용해서 키워드 매칭한다.
    """
    found_name = False
    found_price = False
    for cell in cells:
        ct = _normalize_cell(cell)
        if not ct:
            continue
        # 이름 컬럼 체크 (우선순위 높음)
        if any(kw in ct for kw in _NAME_KEYWORDS):
            found_name = True
        elif "정상" in ct:
            found_price = True
        elif "이벤트" in ct:
            # "이벤트"가 포함되지만 이름 키워드가 아닌 셀 → 가격 컬럼
            found_price = True
    return found_name and found_price


def _pick_best_name_col(rows: list[list[str]], candidates: list[int]) -> int:
    """이벤트명 후보 컬럼이 여럿일 때 데이터 샘플로 최적 컬럼을 선택.

    이후 최대 5개 행을 샘플링하여 비어있지 않은 비율이 높은 컬럼 반환.
    동률이면 가장 우측(인덱스가 큰) 컬럼 반환.
    """
    sample_rows = rows[:5]
    best_col = candidates[-1]  # 기본값: 가장 우측
    best_fill = -1.0
    for col in candidates:
        filled = sum(
            1 for r in sample_rows
            if col < len(r) and r[col].strip()
        )
        ratio = filled / len(sample_rows) if sample_rows else 0.0
        if ratio > best_fill:
            best_fill = ratio
            best_col = col
        elif ratio == best_fill:
            # 동률: 우측 우선
            best_col = max(best_col, col)
    return best_col


def infer_columns_from_data(row: list[str]) -> dict | None:
    """데이터 패턴으로 컬럼 위치를 추론하는 폴백 함수.

    텍스트 셀 뒤에 가격처럼 보이는 셀이 1~2개 나타나면
    첫 텍스트=이름, 첫 가격=정상가, 두 번째 가격=이벤트가로 추정한다.
    나머지 셀은 비고로 취급한다.

    반환: {"col_name": int, "col_regular": int, "col_event": int, "col_notes": int}
    또는 패턴 불일치 시 None.
    """
    def _is_price_like(val: str) -> bool:
        parsed = parse_price(val)
        return parsed is not None and parsed >= 10_000

    stripped = [cell.strip() for cell in row]

    # 첫 번째 비어있지 않은 텍스트 셀 탐색
    col_name: int | None = None
    for i, val in enumerate(stripped):
        if val and not _is_price_like(val):
            col_name = i
            break

    if col_name is None:
        return None

    # 이름 셀 이후 가격 셀들 수집
    price_cols: list[int] = []
    for i in range(col_name + 1, len(stripped)):
        if _is_price_like(stripped[i]):
            price_cols.append(i)
        elif stripped[i]:
            # 가격이 아닌 유의미한 셀이 끼어있으면 중단
            break

    if not price_cols:
        return None

    col_regular = price_cols[0]
    col_event = price_cols[1] if len(price_cols) >= 2 else price_cols[0]

    # 비고: 가격 컬럼들 이후 첫 번째 비어있지 않은 셀
    last_price_col = price_cols[-1]
    col_notes = last_price_col + 1  # 기본값 (비어있을 수 있음)
    for i in range(last_price_col + 1, len(stripped)):
        if stripped[i]:
            col_notes = i
            break

    return {
        "col_name": col_name,
        "col_regular": col_regular,
        "col_event": col_event,
        "col_notes": col_notes,
    }


def _collect_notes(row: list[str], col_notes: int) -> str:
    """col_notes부터 행 끝까지 비어있지 않은 셀을 ' / '로 합쳐 반환.

    빈 셀 제외, 중복 제거(순서 유지).
    """
    if col_notes >= len(row):
        return ""
    seen: list[str] = []
    seen_set: set[str] = set()
    for cell in row[col_notes:]:
        val = cell.strip()
        if val and val not in seen_set:
            seen.append(val)
            seen_set.add(val)
    return " / ".join(seen)


def parse_branch_sheet(
    rows: list[list[str]], branch_name: str
) -> list[ParsedEvent]:
    """지점 시트의 원시 데이터를 ParsedEvent 리스트로 변환."""
    events: list[ParsedEvent] = []
    current_category = "미분류"
    row_order = 0
    header_found = False

    col_name = 0
    col_regular = 1
    col_event = 2
    col_notes = 3

    for row_idx, row in enumerate(rows):
        if not any(cell.strip() for cell in row):
            continue

        full_text = " ".join(cell.strip() for cell in row)

        # --- 카테고리 마커 감지 (■ 또는 #) ---
        cat = None
        for cell in row:
            # 멀티라인 셀은 첫 줄만 사용
            first_line = cell.split("\n")[0].strip()
            cat = find_category_marker(first_line)
            if cat:
                break
        if cat is None:
            cat = find_category_marker(full_text.split("\n")[0])
        if cat:
            current_category = cat
            header_found = False
            continue

        # --- 헤더 행 감지 ---
        if is_header_row(row):
            name_col_candidates: list[int] = []
            col_regular_new = col_regular
            col_event_new = col_event
            col_notes_new = -1

            for i, cell in enumerate(row):
                # 멀티라인 셀은 첫 줄만 사용
                cell_text = _normalize_cell(cell)
                if any(kw in cell_text for kw in _NAME_KEYWORDS):
                    name_col_candidates.append(i)
                elif "정상" in cell_text:
                    col_regular_new = i
                elif "이벤트" in cell_text:
                    col_event_new = i
                elif any(kw in cell_text for kw in _NOTES_KEYWORDS):
                    col_notes_new = i

            # 이벤트명 컬럼 다중 매칭 처리 (광교 케이스)
            if len(name_col_candidates) >= 2:
                # 이후 데이터 행 5개 샘플로 최적 컬럼 선택
                remaining_rows = rows[row_idx + 1:]
                col_name = _pick_best_name_col(remaining_rows, name_col_candidates)
            elif name_col_candidates:
                col_name = name_col_candidates[0]

            col_regular = col_regular_new
            col_event = col_event_new

            # 비고 컬럼 미감지 시 마지막 가격 컬럼 다음으로 설정
            if col_notes_new >= 0:
                col_notes = col_notes_new
            elif col_notes <= max(col_name, col_regular, col_event):
                col_notes = max(col_name, col_regular, col_event) + 1

            header_found = True
            continue

        if not header_found:
            inferred = infer_columns_from_data(row)
            if inferred:
                col_name = inferred["col_name"]
                col_regular = inferred["col_regular"]
                col_event = inferred["col_event"]
                col_notes = inferred["col_notes"]
                header_found = True
            else:
                continue

        # 제목 행 건너뛰기 ("3-4월 이벤트" 형태, 이름 셀이 비어있는 경우만)
        name_cell = row[col_name].strip() if col_name < len(row) else ""
        if not name_cell and "이벤트" in full_text and "월" in full_text:
            continue
        if "목차로 돌아가기" in full_text:
            continue

        name = row[col_name].strip() if col_name < len(row) else ""
        if not name:
            continue

        regular_str = row[col_regular].strip() if col_regular < len(row) else ""
        event_str = row[col_event].strip() if col_event < len(row) else ""

        regular_price = parse_price(regular_str)
        event_price = parse_price(event_str)

        # --- 카테고리 행 안전망 (케이스 7) ---
        # 가격 둘 다 None이고 단 하나의 셀만 텍스트가 있는 행 → 카테고리 후보
        if regular_price is None and event_price is None:
            non_empty_cells = [c.strip() for c in row if c.strip()]
            if len(non_empty_cells) == 1 and non_empty_cells[0] == name:
                current_category = name
                continue

        discount_rate = calc_discount_rate(regular_price, event_price)

        # --- 비고: col_notes 이후 모든 셀 합산 (케이스 3) ---
        notes_str = _collect_notes(row, col_notes)

        is_pkg = detect_package(name)
        components = split_components(name) if is_pkg else [name]
        session_count = extract_session_count(name)

        row_order += 1
        events.append(ParsedEvent(
            raw_event_name=name,
            raw_category=current_category,
            display_name=name,
            regular_price=regular_price,
            event_price=event_price,
            discount_rate=discount_rate,
            notes=notes_str,
            session_count=session_count,
            is_package=is_pkg,
            row_order=row_order,
            components=components,
        ))

    return events


def validate_parsed_events(events: list[ParsedEvent]) -> list[dict]:
    """임포트 결과 검증. 이상치 목록을 반환."""
    issues = []
    for e in events:
        if e.regular_price and e.regular_price < 1000:
            issues.append({"event": e.display_name, "issue": f"정상가 이상 ({e.regular_price}원)"})
        if e.regular_price and e.event_price and e.event_price > e.regular_price:
            issues.append({"event": e.display_name, "issue": f"이벤트가({e.event_price}) > 정상가({e.regular_price})"})
        if e.event_price and e.event_price < 1000:
            issues.append({"event": e.display_name, "issue": f"이벤트가 이상 ({e.event_price}원)"})
        # 가격 정보 없음 — 카테고리 행으로 오분류됐을 수 있음 (케이스 8)
        if e.regular_price is None and e.event_price is None:
            issues.append({"event": e.display_name, "issue": "가격 정보 없음 (카테고리 행으로 의심)"})
    return issues
