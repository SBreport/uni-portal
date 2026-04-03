"""플레이스 일별 스냅샷 — 구글시트 오늘 데이터를 place_daily 테이블에 저장."""

import logging
from datetime import date

from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)


def take_snapshot():
    """오늘의 플레이스 데이터를 구글시트에서 읽어 DB에 저장."""
    try:
        from place.sheets import get_ranking, list_months
    except Exception as e:
        logger.error(f"[place_snapshot] sheets 모듈 임포트 실패: {e}")
        return {"ok": False, "error": str(e)}

    today = date.today()
    today_str = today.isoformat()

    # 현재 월의 시트 찾기
    months = list_months()
    current_sheet = None
    for name in months:
        if f"{today.month}월" in name and str(today.year) in name:
            current_sheet = name
            break

    if not current_sheet:
        logger.warning(f"[place_snapshot] {today.year}년 {today.month}월 시트를 찾을 수 없음")
        return {"ok": False, "error": "sheet not found"}

    ranking = get_ranking(current_sheet)
    branches = ranking.get("branches", [])
    today_idx = ranking.get("today_index", 0)

    conn = get_conn(EQUIPMENT_DB)
    inserted = 0
    try:
        for b in branches:
            branch_name = b.get("branch", "")
            keyword = b.get("keyword", "")
            # 오늘의 일별 데이터에서 노출 여부와 순위 추출
            daily = b.get("daily", [])
            is_exposed = 0
            rank = None
            for d in daily:
                if d.get("day") == today.day:
                    is_exposed = 1 if d.get("success") else 0
                    rank = d.get("rank")
                    break

            # branch_id 조회 (evt_branches에서)
            row = conn.execute(
                "SELECT id FROM evt_branches WHERE name = ?", (branch_name,)
            ).fetchone()
            branch_id = row["id"] if row else 0

            conn.execute(
                """INSERT OR REPLACE INTO place_daily
                   (date, branch_id, branch_name, keyword, is_exposed, rank, source)
                   VALUES (?, ?, ?, ?, ?, ?, 'sheets')""",
                (today_str, branch_id, branch_name, keyword, is_exposed, rank)
            )
            inserted += 1

        conn.commit()
        logger.info(f"[place_snapshot] {inserted}건 저장 완료 ({today_str})")
        return {"ok": True, "date": today_str, "count": inserted}
    except Exception as e:
        logger.error(f"[place_snapshot] 저장 실패: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
