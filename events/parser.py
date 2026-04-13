"""구글 시트 원시 데이터를 파싱하여 구조화된 이벤트 데이터로 변환하는 모듈.

각 지점 시트는 다음 구조를 가짐:
  - 상단: 제목 행 ("[지점명] 3-4월 이벤트")
  - ■ 카테고리 마커 행 (예: "■ 단독이벤트")
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


def find_category_marker(row_text: str) -> str | None:
    """행 텍스트에서 ■ 카테고리 마커를 찾아 카테고리명 반환."""
    if "■" in row_text:
        cleaned = row_text.replace("■", "").strip()
        return cleaned if cleaned else None
    return None


_NAME_KEYWORDS = {"이벤트명", "시술명", "상품명", "항목", "메뉴명"}
_REGULAR_KEYWORDS = {"정상가", "원가", "기본가", "정가"}
_EVENT_KEYWORDS = {"이벤트가", "할인가", "프로모션가", "특가", "최종가"}
_NOTES_KEYWORDS = {"비고", "참고", "메모", "설명"}


def is_header_row(cells: list[str]) -> bool:
    """헤더 행 여부 판별.

    이벤트/시술명 계열 컬럼과 가격 계열 컬럼(정상가 또는 이벤트가)이
    모두 존재하는 행을 헤더로 인식한다.
    """
    text = " ".join(cells)
    has_name_col = any(kw in text for kw in _NAME_KEYWORDS)
    has_regular_col = any(kw in text for kw in _REGULAR_KEYWORDS)
    has_event_col = any(kw in text for kw in _EVENT_KEYWORDS)
    return has_name_col and (has_regular_col or has_event_col)


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

    for row in rows:
        if not any(cell.strip() for cell in row):
            continue

        full_text = " ".join(cell.strip() for cell in row)

        cat = None
        for cell in row:
            cat = find_category_marker(cell.strip())
            if cat:
                break
        if cat is None:
            cat = find_category_marker(full_text)
        if cat:
            current_category = cat
            header_found = False
            continue

        if is_header_row(row):
            for i, cell in enumerate(row):
                cell_text = cell.strip()
                if any(kw in cell_text for kw in _NAME_KEYWORDS):
                    col_name = i
                elif any(kw in cell_text for kw in _REGULAR_KEYWORDS):
                    col_regular = i
                elif any(kw in cell_text for kw in _EVENT_KEYWORDS):
                    col_event = i
                elif any(kw in cell_text for kw in _NOTES_KEYWORDS):
                    col_notes = i
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

        if "이벤트" in full_text and "월" in full_text and len(row[0].strip()) <= 3:
            continue
        if "목차로 돌아가기" in full_text:
            continue

        name = row[col_name].strip() if col_name < len(row) else ""
        if not name:
            continue

        regular_str = row[col_regular].strip() if col_regular < len(row) else ""
        event_str = row[col_event].strip() if col_event < len(row) else ""
        notes_str = row[col_notes].strip() if col_notes < len(row) else ""

        regular_price = parse_price(regular_str)
        event_price = parse_price(event_str)
        discount_rate = calc_discount_rate(regular_price, event_price)

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
    return issues
