"""데이터 품질 검증 모듈."""

from dataclasses import dataclass, field
from events.parser import ParsedEvent


@dataclass
class ValidationResult:
    total: int = 0
    valid: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_ok(self) -> bool:
        return len(self.errors) == 0


def validate_events(
    events: list[ParsedEvent], branch_name: str
) -> ValidationResult:
    """이벤트 목록의 데이터 품질을 검증."""
    result = ValidationResult(total=len(events))

    for i, ev in enumerate(events, 1):
        prefix = f"[{branch_name}] 행 {i}"

        if not ev.raw_event_name:
            result.errors.append(f"{prefix}: 이벤트명 비어있음")
            continue

        if ev.regular_price is not None and ev.event_price is not None:
            if ev.event_price > ev.regular_price:
                result.warnings.append(
                    f"{prefix}: 이벤트가({ev.event_price:,}) > 정상가({ev.regular_price:,}) - {ev.raw_event_name}"
                )

        if ev.regular_price is None and ev.event_price is None:
            result.warnings.append(
                f"{prefix}: 가격 정보 없음 - {ev.raw_event_name}"
            )

        has_warning = False
        if ev.raw_category == "미분류":
            result.warnings.append(
                f"{prefix}: 카테고리 미분류 - {ev.raw_event_name}"
            )
            has_warning = True

        if not has_warning:
            result.valid += 1

    return result
