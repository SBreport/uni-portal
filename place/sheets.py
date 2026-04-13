"""Google Sheets에서 상위노출 데이터를 가져와 파싱하는 모듈."""

import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

from shared.sheets_base import (
    get_cached, set_cached, get_client, safe_int,
    calc_today_index, calc_streak, calc_status, build_summary,
)

SPREADSHEET_ID = "1h-Zhxpzz8EVHcxoxO4Z72iHIx9EKwYKppni3CKpeal0"
SKIP_SHEETS = {"~30 템플릿", "~31 템플릿"}

# 실행사별 시트 ID
AGENCY_SHEETS = {
    "애드드림즈": "1j3NELKYDICyENCzAbEiW6g_NgvEs8bxdAfqP1URlhKA",
    "일프로": "1xBpyiUWvlSvvFqvirFKJwjHzk0vhlIcNHtYIyRUxzqk",
    "간달프": "14uGBHtMElW99o0V14J5MOsqeIf0mx8DGRBa-sYh7a0Y",
    "에이치": "1ZOsmK9pI2B8O92v2Mlsdc5AGje02ALBwwpir_ZsvThA",
}


def _get_agency_sheets_from_db() -> dict[str, str]:
    """DB에서 실행사별 시트 ID 조회. 없으면 하드코딩 폴백."""
    import json
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'agency_sheets_place'"
        ).fetchone()
        if row:
            return json.loads(row["value"])
        # Fallback to hardcoded
        return AGENCY_SHEETS
    finally:
        conn.close()


def list_months() -> list[str]:
    cached = get_cached("place__months__")
    if cached is not None:
        return cached

    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheets = [ws.title for ws in spreadsheet.worksheets() if ws.title not in SKIP_SHEETS]
    set_cached("place__months__", sheets)
    return sheets


def get_ranking(sheet_name: str) -> dict:
    cache_key = f"place_{sheet_name}"
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
        branch["month_success_count"] = stats.get("total_exposed", branch["month_success_count"])
        branch["work_days"] = stats.get("work_days", branch["work_days"])

    set_cached(cache_key, result)
    return result


def _get_cumulative_stats() -> dict[str, dict]:
    """모든 월별 시트에서 지점별 누적 통계 계산 (단일 배치 API 호출)."""
    cached = get_cached("place__cumulative__")
    if cached is not None:
        return cached

    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    all_sheets = [ws.title for ws in spreadsheet.worksheets() if ws.title not in SKIP_SHEETS]

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
        set_cached("place__cumulative__", {})
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
            success_row = values[i]
            rank_row = values[i + 1] if i + 1 < len(values) else []
            i += 2

            if not success_row or not success_row[0]:
                continue

            branch_name = success_row[0].strip()
            if branch_name not in stats:
                stats[branch_name] = {"total_exposed": 0, "work_days": 0}

            for d in range(day_limit):
                col_idx = d + 1
                success_val = safe_int(success_row[col_idx]) if col_idx < len(success_row) else 0
                rank_val = _parse_rank(rank_row[col_idx] if rank_row and col_idx < len(rank_row) else None)

                if rank_val is not None:
                    stats[branch_name]["work_days"] += 1
                if success_val == 1:
                    stats[branch_name]["total_exposed"] += 1

    set_cached("place__cumulative__", stats)
    return stats


def _parse_sheet_name(sheet_name: str) -> tuple[int, int]:
    """'3월(2026년)' → (2026, 3)"""
    m = re.match(r"(\d+)월\((\d+)년\)", sheet_name)
    if not m:
        raise ValueError(f"시트 이름 파싱 실패: {sheet_name}")
    return int(m.group(2)), int(m.group(1))


def _parse_rank(val: str | None) -> int | None:
    if not val or not str(val).strip():
        return None
    s = str(val).strip().replace("등", "")
    try:
        return int(s)
    except ValueError:
        return None


def _parse_sheet(values: list[list[str]], sheet_name: str) -> dict:
    year, month = _parse_sheet_name(sheet_name)

    header = values[0]

    # "노출일수" 헤더 위치를 직접 찾아서 일별 컬럼 수 계산
    nosul_header_idx = None
    for idx, h in enumerate(header):
        if "노출" in str(h).strip():
            nosul_header_idx = idx
            break

    if nosul_header_idx and nosul_header_idx > 1:
        num_day_cols = nosul_header_idx - 1
    else:
        num_day_cols = len(header) - 2

    if num_day_cols <= 0:
        logger.warning("_parse_sheet 헤더 컬럼 부족 (day_cols=%d): %s", num_day_cols, sheet_name)
        return {"year": year, "month": month, "days": 0, "today_index": 0,
                "branches": [], "summary": {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0}}

    today_index = calc_today_index(year, month, num_day_cols)

    branches = []
    i = 1
    while i < len(values):
        success_row = values[i]
        rank_row = values[i + 1] if i + 1 < len(values) else []
        i += 2

        if not success_row or not success_row[0]:
            continue

        branch_name = success_row[0].strip()
        keyword = rank_row[0].strip() if rank_row else ""

        # 노출일수: 헤더에서 찾은 위치 또는 일별 데이터 다음 열
        nosul_idx = nosul_header_idx if nosul_header_idx else (num_day_cols + 1)
        nosul_raw = success_row[nosul_idx] if len(success_row) > nosul_idx else "0"
        nosul_count = safe_int(nosul_raw, 0)

        # 일별 데이터 파싱
        daily = []
        for d in range(num_day_cols):
            col_idx = d + 1
            success_val = safe_int(success_row[col_idx]) if col_idx < len(success_row) else None
            rank_val = _parse_rank(rank_row[col_idx] if col_idx < len(rank_row) else None)
            daily.append({"day": d + 1, "success": success_val, "rank": rank_val})

        # 오늘 데이터
        today_data = daily[today_index - 1] if today_index > 0 else None
        today_success = bool(today_data and today_data["success"] == 1) if today_data else False
        today_rank = today_data["rank"] if today_data else None

        month_success_count = sum(1 for d in daily[:today_index] if d["success"] == 1)
        work_days = sum(1 for d in daily[:today_index] if d["rank"] is not None)
        streak = calc_streak(daily, today_index, key="success")
        status = calc_status(nosul_count, month_success_count, today_success)

        branches.append({
            "branch": branch_name,
            "keyword": keyword,
            "nosul_count": nosul_count,
            "today_rank": today_rank,
            "today_success": today_success,
            "today_active": today_success,        # 공통 필드
            "streak": streak,
            "status": status,
            "month_success_count": month_success_count,
            "month_count": month_success_count,    # 공통 필드
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


def get_ranking_by_agency(sheet_name: str) -> dict:
    """실행사별 시트에서 순위 데이터 + 실행사 매핑을 동시에 읽어온다."""
    import time
    client = get_client()
    agency_map = {}  # branch_name → agency_name
    all_branches = []  # merged list of all branch data

    agency_sheets = _get_agency_sheets_from_db()
    for idx, (agency_name, sheet_id) in enumerate(agency_sheets.items()):
        if idx > 0:
            time.sleep(1.5)  # API rate limit 회피 (분당 60회 제한)
        try:
            spreadsheet = client.open_by_key(sheet_id)
            ws = spreadsheet.worksheet(sheet_name)
            values = ws.get_all_values()
            parsed = _parse_sheet(values, sheet_name)

            # Extract branch→agency mapping from this sheet
            for b in parsed["branches"]:
                branch = b["branch"]
                if "유앤아이" in branch:
                    agency_map[branch] = agency_name

            all_branches.extend(parsed["branches"])
        except Exception as e:
            logger.warning(f"실행사 시트 읽기 실패 ({agency_name}/{sheet_name}): {e}")
            continue

    # Build merged result using same structure as _parse_sheet return value
    if not all_branches:
        return {
            "agency_map": agency_map,
            "ranking": {
                "year": 0,
                "month": 0,
                "days": 0,
                "today_index": 0,
                "branches": [],
                "summary": {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0},
            },
        }

    # Get year/month from sheet_name
    year, month = _parse_sheet_name(sheet_name)

    # Rebuild summary from all merged branches
    merged_result = {
        "year": year,
        "month": month,
        "days": len(all_branches[0].get("daily", [])) if all_branches else 0,
        "today_index": calc_today_index(year, month, len(all_branches[0].get("daily", [])) if all_branches else 30),
        "branches": all_branches,
        "summary": build_summary(all_branches),
    }

    return {"agency_map": agency_map, "ranking": merged_result}


def list_months_from_agency() -> list[str]:
    """실행사 시트에서 월 목록 조회."""
    cached = get_cached("place__agency_months__")
    if cached is not None:
        return cached

    client = get_client()
    # Use first agency sheet to get month list (all sheets have same tabs)
    agency_sheets = _get_agency_sheets_from_db()
    if not agency_sheets:
        return []
    first_id = next(iter(agency_sheets.values()))
    spreadsheet = client.open_by_key(first_id)
    sheets = [ws.title for ws in spreadsheet.worksheets() if ws.title not in SKIP_SHEETS]
    # Filter only parseable month tabs
    result = []
    for name in sheets:
        try:
            _parse_sheet_name(name)
            result.append(name)
        except ValueError:
            continue
    set_cached("place__agency_months__", result)
    return result
