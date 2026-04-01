"""Google Sheets에서 웹페이지 노출 데이터를 가져와 파싱하는 모듈."""

import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

from shared.sheets_base import (
    get_cached, set_cached, get_client, safe_int,
    calc_today_index, calc_streak, calc_status, build_summary,
)

SPREADSHEET_ID = "1tkJqI64R6Ohjj1tDMvCw5oGvrmxuE7lYr5AdTkFMEh4"


def list_months() -> list[str]:
    """월별 시트 목록 반환 (최신순)."""
    cached = get_cached("webpage__months__")
    if cached is not None:
        return cached

    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheets = [ws.title for ws in spreadsheet.worksheets()]
    set_cached("webpage__months__", sheets)
    return sheets


def get_ranking(sheet_name: str) -> dict:
    """특정 월의 웹페이지 노출 데이터 반환 (누적 통계 포함)."""
    cache_key = f"webpage_{sheet_name}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    ws = spreadsheet.worksheet(sheet_name)
    values = ws.get_all_values()
    result = _parse_sheet(values, sheet_name)

    # 누적 통계 병합 (총노출, 진행일)
    cumulative = _get_cumulative_stats()
    for branch in result["branches"]:
        stats = cumulative.get(branch["branch"], {})
        branch["month_exposed_count"] = stats.get("total_exposed", branch["month_exposed_count"])
        branch["work_days"] = stats.get("work_days", branch["work_days"])

    set_cached(cache_key, result)
    return result


def _get_cumulative_stats() -> dict[str, dict]:
    """모든 월별 시트에서 지점별 누적 통계 계산 (단일 배치 API 호출)."""
    cached = get_cached("webpage__cumulative__")
    if cached is not None:
        return cached

    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    all_sheets = [ws.title for ws in spreadsheet.worksheets()]

    # 파싱 가능한 시트만 필터 → 오래된 순 정렬
    parseable = []
    for name in all_sheets:
        try:
            _parse_sheet_name(name)
            parseable.append(name)
        except ValueError:
            logger.warning("시트 이름 파싱 불가, 건너뜀: %s", name)
            continue
    all_sheets_sorted = sorted(parseable, key=lambda s: _parse_sheet_name(s))

    if not all_sheets_sorted:
        set_cached("webpage__cumulative__", {})
        return {}

    # 모든 시트를 1번의 API 호출로 읽기
    ranges = [f"'{name}'" for name in all_sheets_sorted]
    batch_result = spreadsheet.values_batch_get(ranges)

    today = date.today()
    stats: dict[str, dict] = {}

    for idx, sheet_name in enumerate(all_sheets_sorted):
        year, month = _parse_sheet_name(sheet_name)
        values = batch_result["valueRanges"][idx].get("values", [])
        if not values:
            logger.warning("시트 데이터 비어있음: %s", sheet_name)
            continue

        header = values[0]
        num_day_cols = len(header) - 2
        if num_day_cols <= 0:
            logger.warning("헤더 컬럼 부족 (day_cols=%d): %s", num_day_cols, sheet_name)
            continue

        day_limit = calc_today_index(year, month, num_day_cols)

        i = 1
        while i < len(values):
            branch_row = values[i]
            keyword_row = values[i + 1] if i + 1 < len(values) else []
            i += 2

            if not branch_row or not branch_row[0]:
                continue

            branch_name = branch_row[0].strip()
            if branch_name not in stats:
                stats[branch_name] = {"total_exposed": 0, "work_days": 0}

            for d in range(day_limit):
                col_idx = d + 1
                exposed = safe_int(branch_row[col_idx]) if col_idx < len(branch_row) else 0
                mark = ""
                if keyword_row and col_idx < len(keyword_row):
                    mark = str(keyword_row[col_idx]).strip()

                if mark in ("ㅇ", "x"):
                    stats[branch_name]["work_days"] += 1
                if exposed == 1:
                    stats[branch_name]["total_exposed"] += 1

    set_cached("webpage__cumulative__", stats)
    return stats


def _parse_sheet_name(sheet_name: str) -> tuple[int, int]:
    """'2026.3' → (2026, 3)"""
    m = re.match(r"(\d{4})\.(\d{1,2})", sheet_name)
    if not m:
        raise ValueError(f"시트 이름 파싱 실패: {sheet_name}")
    return int(m.group(1)), int(m.group(2))


def _parse_sheet(values: list[list[str]], sheet_name: str) -> dict:
    year, month = _parse_sheet_name(sheet_name)

    header = values[0]
    num_day_cols = len(header) - 2
    if num_day_cols <= 0:
        logger.warning("_parse_sheet 헤더 컬럼 부족 (day_cols=%d): %s", num_day_cols, sheet_name)
        return {
            "year": year, "month": month, "days": 0, "today_index": 0,
            "branches": [],
            "summary": {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0},
        }

    today_index = calc_today_index(year, month, num_day_cols)

    branches = []
    i = 1
    while i < len(values):
        branch_row = values[i]
        keyword_row = values[i + 1] if i + 1 < len(values) else []
        i += 2

        if not branch_row or not branch_row[0]:
            continue

        branch_name = branch_row[0].strip()
        keyword = keyword_row[0].strip() if keyword_row else ""

        # 노출일수: branch_row 마지막 컬럼
        nosul_idx = num_day_cols + 1
        nosul_raw = branch_row[nosul_idx] if len(branch_row) > nosul_idx else "0"
        nosul_count = safe_int(nosul_raw, 0)

        # 일별 데이터: 1=노출, 0=미노출
        daily = []
        for d in range(num_day_cols):
            col_idx = d + 1
            exposed_val = safe_int(branch_row[col_idx]) if col_idx < len(branch_row) else 0
            mark = ""
            if keyword_row and col_idx < len(keyword_row):
                mark = str(keyword_row[col_idx]).strip()
            daily.append({
                "day": d + 1,
                "exposed": exposed_val,
                "mark": mark,
            })

        # 오늘 데이터
        today_data = daily[today_index - 1] if today_index > 0 else None
        today_exposed = bool(today_data and today_data["exposed"] == 1) if today_data else False

        month_exposed_count = sum(1 for d in daily[:today_index] if d["exposed"] == 1)
        work_days = sum(1 for d in daily[:today_index] if d["mark"] in ("ㅇ", "x"))
        streak = calc_streak(daily, today_index, key="exposed")
        status = calc_status(nosul_count, month_exposed_count, today_exposed)

        branches.append({
            "branch": branch_name,
            "keyword": keyword,
            "nosul_count": nosul_count,
            "today_exposed": today_exposed,
            "today_active": today_exposed,          # 공통 필드
            "streak": streak,
            "status": status,
            "month_exposed_count": month_exposed_count,
            "month_count": month_exposed_count,      # 공통 필드
            "work_days": work_days,
            "daily": daily,
        })

    return {
        "year": year,
        "month": month,
        "days": num_day_cols,
        "today_index": today_index,
        "branches": branches,
        "summary": build_summary(branches),
    }
