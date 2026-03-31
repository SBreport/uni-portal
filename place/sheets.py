"""Google Sheets에서 상위노출 데이터를 가져와 파싱하는 모듈."""

import os
import re
import time
from datetime import datetime, date

SPREADSHEET_ID = "1h-Zhxpzz8EVHcxoxO4Z72iHIx9EKwYKppni3CKpeal0"
SKIP_SHEETS = {"~30 템플릿", "~31 템플릿"}

_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5분


def _get_client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        raise RuntimeError("gspread/google-auth 패키지가 설치되지 않았습니다.")

    creds_file = os.environ.get(
        "GOOGLE_CREDENTIALS_FILE",
        os.path.join(os.path.dirname(__file__), "..", "credentials.json"),
    )
    if not os.path.exists(creds_file):
        raise RuntimeError(f"credentials.json 파일을 찾을 수 없습니다: {creds_file}")

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    return gspread.authorize(creds)


def _get_cached(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None


def _set_cached(key: str, data):
    _cache[key] = (time.time(), data)


def list_months() -> list[str]:
    cached = _get_cached("__months__")
    if cached is not None:
        return cached

    client = _get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheets = [ws.title for ws in spreadsheet.worksheets() if ws.title not in SKIP_SHEETS]
    _set_cached("__months__", sheets)
    return sheets


def get_ranking(sheet_name: str) -> dict:
    cached = _get_cached(sheet_name)
    if cached is not None:
        return cached

    client = _get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    ws = spreadsheet.worksheet(sheet_name)
    values = ws.get_all_values()
    result = _parse_sheet(values, sheet_name)
    _set_cached(sheet_name, result)
    return result


def _parse_sheet_name(sheet_name: str) -> tuple[int, int]:
    """'3월(2026년)' → (2026, 3)"""
    m = re.match(r"(\d+)월\((\d+)년\)", sheet_name)
    if not m:
        raise ValueError(f"시트 이름 파싱 실패: {sheet_name}")
    return int(m.group(2)), int(m.group(1))


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


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
    # 날짜 컬럼: header[1] ~ header[-2], 마지막은 "노출일수"
    num_day_cols = len(header) - 2
    if num_day_cols <= 0:
        return {"year": year, "month": month, "days": 0, "today_index": 0,
                "branches": [], "summary": {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0}}

    # 오늘 인덱스 결정
    today = date.today()
    if year == today.year and month == today.month:
        today_index = min(today.day, num_day_cols)
    else:
        today_index = num_day_cols

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

        # 노출일수: success_row의 마지막 컬럼 (인덱스 = num_day_cols + 1)
        nosul_idx = num_day_cols + 1
        nosul_raw = success_row[nosul_idx] if len(success_row) > nosul_idx else "0"
        nosul_count = _safe_int(nosul_raw, 0)

        # 일별 데이터 파싱
        daily = []
        for d in range(num_day_cols):
            col_idx = d + 1
            success_val = _safe_int(success_row[col_idx]) if col_idx < len(success_row) else None
            rank_val = _parse_rank(rank_row[col_idx] if col_idx < len(rank_row) else None)
            daily.append({"day": d + 1, "success": success_val, "rank": rank_val})

        # 오늘 데이터
        today_data = daily[today_index - 1] if today_index > 0 else None
        today_success = bool(today_data and today_data["success"] == 1) if today_data else False
        today_rank = today_data["rank"] if today_data else None

        # 월간 성공 횟수 (오늘까지)
        month_success_count = sum(1 for d in daily[:today_index] if d["success"] == 1)

        # 연속 성공일 (오늘부터 역방향)
        streak = 0
        for d in reversed(daily[:today_index]):
            if d["success"] == 1:
                streak += 1
            else:
                break

        # 상태 판정
        if nosul_count <= 0 and month_success_count == 0:
            status = "미달"
        elif today_success:
            status = "active"
        else:
            status = "fail"

        branches.append({
            "branch": branch_name,
            "keyword": keyword,
            "nosul_count": nosul_count,
            "today_rank": today_rank,
            "today_success": today_success,
            "streak": streak,
            "status": status,
            "month_success_count": month_success_count,
            "daily": daily,
        })

    # 요약
    total = len(branches)
    success_today = sum(1 for b in branches if b["status"] == "active")
    midal = sum(1 for b in branches if b["status"] == "미달")
    fail_today = total - success_today - midal

    return {
        "year": year,
        "month": month,
        "days": num_day_cols,
        "today_index": today_index,
        "branches": branches,
        "summary": {
            "total": total,
            "success_today": success_today,
            "fail_today": fail_today,
            "midal": midal,
        },
    }
