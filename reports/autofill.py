"""주간 보고서 플레이스·웹사이트 섹션 자동 집계 모듈."""

from datetime import datetime, timedelta

from shared.db import get_conn, EQUIPMENT_DB
from shared.branch_resolver import resolve_evt_branch_id


def compute_autofill(week_start: str, week_end: str) -> dict:
    """Place + Website 섹션 자동 집계. week_start/week_end: YYYY-MM-DD."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        prev_start = (datetime.strptime(week_start, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
        prev_end = (datetime.strptime(week_end, "%Y-%m-%d") - timedelta(days=7)).strftime("%Y-%m-%d")
        now = datetime.now().isoformat(timespec="seconds")

        place = _compute_place(conn, week_start, week_end, prev_start, prev_end)
        website = _compute_website(conn, week_start, week_end, prev_start, prev_end)

        return {
            "place": {**place, "auto_updated_at": now},
            "website": {**website, "auto_updated_at": now},
        }
    finally:
        conn.close()


def _compute_place(conn, ws, we, ps, pe) -> dict:
    # total: 이번 주 추적 중인 고유 지점 수
    total = conn.execute(
        "SELECT COUNT(DISTINCT branch_name) FROM place_daily WHERE date BETWEEN ? AND ?",
        (ws, we),
    ).fetchone()[0]

    # occupied: 이번 주 is_exposed=1 이상인 지점
    occupied_rows = conn.execute(
        "SELECT DISTINCT branch_name FROM place_daily WHERE date BETWEEN ? AND ? AND is_exposed=1",
        (ws, we),
    ).fetchall()
    occupied_names = {r[0] for r in occupied_rows}

    # paused: evt_branches.is_paused=1 AND is_active=1 — resolver 기반 (가장 긴 short_name 우선 매칭)
    paused_rows = conn.execute(
        "SELECT id, name FROM evt_branches WHERE is_paused=1 AND is_active=1 ORDER BY name",
    ).fetchall()
    paused_ids = {r[0] for r in paused_rows}
    paused_names = [r[1] for r in paused_rows]  # 보고서 표시용 (예: '안양점')

    _resolve_cache: dict[str, int | None] = {}
    def _is_paused(bn: str) -> bool:
        if not bn:
            return False
        if bn not in _resolve_cache:
            _resolve_cache[bn] = resolve_evt_branch_id(conn, bn)
        return _resolve_cache[bn] in paused_ids

    # dropped: 직전 주 occupied → 이번 주 미노출, 단 이번 주 paused 제외
    prev_exposed = conn.execute(
        "SELECT DISTINCT branch_name FROM place_daily WHERE date BETWEEN ? AND ? AND is_exposed=1",
        (ps, pe),
    ).fetchall()
    prev_occupied = {r[0] for r in prev_exposed}
    dropped_names = sorted(
        b for b in (prev_occupied - occupied_names) if not _is_paused(b)
    )

    return {
        "total_auto": str(total),
        "occupied_auto": str(len(occupied_names)),
        "paused_auto": str(len(paused_names)),
        "pausedList_auto": "\n".join(paused_names),
        "dropped_auto": str(len(dropped_names)),
        "droppedList_auto": "\n".join(dropped_names),
    }


def _compute_website(conn, ws, we, ps, pe) -> dict:
    # total: 이번 주 고유 키워드 수
    total = conn.execute(
        "SELECT COUNT(DISTINCT keyword) FROM webpage_daily WHERE date BETWEEN ? AND ?",
        (ws, we),
    ).fetchone()[0]

    # visible: 이번 주 is_exposed=1인 고유 지점
    visible_rows = conn.execute(
        "SELECT DISTINCT branch_name FROM webpage_daily WHERE date BETWEEN ? AND ? AND is_exposed=1",
        (ws, we),
    ).fetchall()
    visible_names = {r[0] for r in visible_rows}

    # dropped: 직전 주 visible → 이번 주 미노출
    prev_visible = conn.execute(
        "SELECT DISTINCT branch_name FROM webpage_daily WHERE date BETWEEN ? AND ? AND is_exposed=1",
        (ps, pe),
    ).fetchall()
    prev_visible_names = {r[0] for r in prev_visible}
    dropped_names = sorted(prev_visible_names - visible_names)

    # missing: 이번 주 추적 중이지만 전체 기간 한 번도 is_exposed=1 없음
    missing_rows = conn.execute("""
        SELECT DISTINCT branch_name FROM webpage_daily
        WHERE date BETWEEN ? AND ?
          AND branch_name NOT IN (
              SELECT DISTINCT branch_name FROM webpage_daily WHERE is_exposed=1
          )
        ORDER BY branch_name
    """, (ws, we)).fetchall()
    missing_names = [r[0] for r in missing_rows]

    return {
        "total_auto": str(total),
        "visible_auto": str(len(visible_names)),
        "visibleList_auto": "\n".join(sorted(visible_names)),
        "dropped_auto": str(len(dropped_names)),
        "missing_auto": str(len(missing_names)),
    }
