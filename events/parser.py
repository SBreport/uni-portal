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


def is_header_row(cells: list[str]) -> bool:
    """헤더 행 여부 판별 (이벤트명/정상가/최종 이벤트가 포함)."""
    text = " ".join(cells)
    return "이벤트명" in text and ("정상가" in text or "이벤트가" in text)


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
                if "이벤트명" in cell_text:
                    col_name = i
                elif "정상가" in cell_text:
                    col_regular = i
                elif "이벤트가" in cell_text:
                    col_event = i
                elif "비고" in cell_text:
                    col_notes = i
            header_found = True
            continue

        if not header_found:
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
