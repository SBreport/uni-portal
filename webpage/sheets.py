"""Google Sheets에서 웹페이지 노출 데이터를 가져와 파싱하는 모듈."""

import os
import re
import time
from datetime import date

SPREADSHEET_ID = "1tkJqI64R6Ohjj1tDMvCw5oGvrmxuE7lYr5AdTkFMEh4"

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
    """월별 시트 목록 반환 (최신순)."""
    cached = _get_cached("__months__")
    if cached is not None:
        return cached

    client = _get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    sheets = [ws.title for ws in spreadsheet.worksheets()]
    _set_cached("__months__", sheets)
    return sheets


def get_ranking(sheet_name: str) -> dict:
    """특정 월의 웹페이지 노출 데이터 반환."""
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
    """'2026.3' → (2026, 3)"""
    m = re.match(r"(\d{4})\.(\d{1,2})", sheet_name)
    if not m:
        raise ValueError(f"시트 이름 파싱 실패: {sheet_name}")
    return int(m.group(1)), int(m.group(2))


def _safe_int(val: str, default: int = 0) -> int:
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


def _parse_sheet(values: list[list[str]], sheet_name: str) -> dict:
    year, month = _parse_sheet_name(sheet_name)

    header = values[0]
    # 날짜 컬럼: header[1] ~ header[-2], 마지막은 "노출일수"
    num_day_cols = len(header) - 2
    if num_day_cols <= 0:
        return {
            "year": year, "month": month, "days": 0, "today_index": 0,
            "branches": [],
            "summary": {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0},
        }

    # 오늘 인덱스
    today = date.today()
    if year == today.year and month == today.month:
        today_index = min(today.day, num_day_cols)
    else:
        today_index = num_day_cols

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
        nosul_count = _safe_int(nosul_raw, 0)

        # 일별 데이터: 1=노출, 0=미노출
        daily = []
        for d in range(num_day_cols):
            col_idx = d + 1
            exposed_val = _safe_int(branch_row[col_idx]) if col_idx < len(branch_row) else 0
            # keyword_row: ㅇ=노출, x=미노출, 빈값=데이터없음
            mark = ""
            if keyword_row and col_idx < len(keyword_row):
                mark = str(keyword_row[col_idx]).strip()
            daily.append({
                "day": d + 1,
                "exposed": exposed_val,
                "mark": mark,  # ㅇ, x, 빈값
            })

        # 오늘 데이터
        today_data = daily[today_index - 1] if today_index > 0 else None
        today_exposed = bool(today_data and today_data["exposed"] == 1) if today_data else False

        # 월간 노출 횟수 (오늘까지)
        month_exposed_count = sum(1 for d in daily[:today_index] if d["exposed"] == 1)

        # 작업 진행일 (모니터링 데이터가 있는 일수: ㅇ 또는 x)
        work_days = sum(1 for d in daily[:today_index] if d["mark"] in ("ㅇ", "x"))

        # 연속 노출일 (오늘부터 역방향)
        streak = 0
        for d in reversed(daily[:today_index]):
            if d["exposed"] == 1:
                streak += 1
            else:
                break

        # 상태 판정
        if nosul_count <= 0 and month_exposed_count == 0:
            status = "미달"
        elif today_exposed:
            status = "active"
        else:
            status = "fail"

        branches.append({
            "branch": branch_name,
            "keyword": keyword,
            "nosul_count": nosul_count,
            "today_exposed": today_exposed,
            "streak": streak,
            "status": status,
            "month_exposed_count": month_exposed_count,
            "work_days": work_days,
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
