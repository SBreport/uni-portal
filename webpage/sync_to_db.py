"""웹페이지 구글시트 → DB 전체 동기화."""

import logging
from datetime import date

from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)


def sync_all_to_db() -> dict:
    """모든 월별 시트 데이터를 webpage_daily 테이블에 동기화."""
    from webpage.sheets import list_months, get_ranking, _parse_sheet_name

    conn = get_conn(EQUIPMENT_DB)
    total_inserted = 0
    sheets_processed = 0

    try:
        months = list_months()

        for sheet_name in months:
            try:
                year, month = _parse_sheet_name(sheet_name)
            except ValueError:
                logger.warning(f"시트 이름 파싱 불가, 건너뜀: {sheet_name}")
                continue

            try:
                ranking = get_ranking(sheet_name)
            except Exception as e:
                logger.warning(f"시트 '{sheet_name}' 읽기 실패: {e}")
                continue

            branches = ranking.get("branches", [])

            for b in branches:
                branch_name = b.get("branch", "")
                keyword = b.get("keyword", "")
                daily = b.get("daily", [])

                # branch_id 조회
                row = conn.execute(
                    "SELECT id FROM evt_branches WHERE name = ?", (branch_name,)
                ).fetchone()
                branch_id = row["id"] if row else 0

                for d in daily:
                    day = d.get("day")
                    if not day:
                        continue
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    is_exposed = 1 if d.get("exposed") else 0
                    executor = d.get("mark", "")

                    # UPSERT
                    conn.execute("""
                        INSERT OR REPLACE INTO webpage_daily
                        (date, branch_id, branch_name, keyword, is_exposed, executor, source)
                        VALUES (?, ?, ?, ?, ?, ?, 'sheets')
                    """, (date_str, branch_id, branch_name, keyword, is_exposed, executor))
                    total_inserted += 1

            sheets_processed += 1

        conn.commit()
        result = {
            "ok": True,
            "sheets_processed": sheets_processed,
            "records_saved": total_inserted,
        }
        logger.info(f"[webpage_sync] 완료: {result}")
        return result
    except Exception as e:
        logger.error(f"[webpage_sync] 실패: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
