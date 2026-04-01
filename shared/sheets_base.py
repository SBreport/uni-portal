"""Google Sheets 공통 유틸리티 — place/webpage 양쪽에서 공유."""

import os
import time
from datetime import date


# ── 캐시 (모듈별 독립) ──────────────────────────────────────────
_cache: dict[str, tuple[float, object]] = {}
_CACHE_TTL = 300  # 5분


def get_cached(key: str):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None


def set_cached(key: str, data):
    _cache[key] = (time.time(), data)


# ── Google Sheets 클라이언트 ─────────────────────────────────────
def get_client():
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


# ── 공통 파싱 헬퍼 ───────────────────────────────────────────────
def safe_int(val: str, default: int = 0) -> int:
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


def calc_today_index(year: int, month: int, num_day_cols: int) -> int:
    """오늘 날짜 기준으로 시트에서 유효한 마지막 일 인덱스 계산."""
    today = date.today()
    if year == today.year and month == today.month:
        return min(today.day, num_day_cols)
    return num_day_cols


def calc_streak(daily: list[dict], today_index: int, key: str = "success") -> int:
    """오늘부터 역방향으로 연속 성공/노출 일수 계산."""
    streak = 0
    for d in reversed(daily[:today_index]):
        if d[key] == 1:
            streak += 1
        else:
            break
    return streak


def calc_status(nosul_count: int, month_count: int, today_active: bool) -> str:
    """미달 / active / fail 상태 판정."""
    if nosul_count <= 0 and month_count == 0:
        return "미달"
    elif today_active:
        return "active"
    return "fail"


def build_summary(branches: list[dict]) -> dict:
    """branches 리스트에서 요약 통계 생성."""
    total = len(branches)
    success_today = sum(1 for b in branches if b["status"] == "active")
    midal = sum(1 for b in branches if b["status"] == "미달")
    fail_today = total - success_today - midal
    return {
        "total": total,
        "success_today": success_today,
        "fail_today": fail_today,
        "midal": midal,
    }
