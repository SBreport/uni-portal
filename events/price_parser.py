"""가격 문자열을 정수로 변환하는 모듈."""

import re


def parse_price(value: str) -> int | None:
    """가격 문자열을 정수(원)로 변환.

    지원 형식: "600,000", "600000", "600,000원", "-", ""
    """
    if not value or not value.strip():
        return None

    cleaned = value.strip().replace(",", "").replace("원", "").replace(" ", "")

    if cleaned in ("-", "0", ""):
        return 0 if cleaned == "0" else None

    match = re.search(r"(\d+)", cleaned)
    if match:
        return int(match.group(1))

    return None


def calc_discount_rate(regular: int | None, event: int | None) -> float | None:
    """할인율 계산 (%).

    regular=500000, event=300000 → 40.0
    """
    if regular is None or event is None or regular <= 0:
        return None
    if event > regular:
        return None
    return round((1 - event / regular) * 100, 1)
