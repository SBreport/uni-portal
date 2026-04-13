"""웹페이지 구글시트 → DB 전체 동기화."""

import logging
from datetime import date

from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)


def sync_all_to_db_legacy() -> dict:
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
        from datetime import datetime
        conn.execute("""
            INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at)
            VALUES (?, ?, 0, 0, ?, ?)
        """, ("webpage_sheets_to_db", total_inserted, f"{sheets_processed}개 시트",
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        logger.info(f"[webpage_sync] 완료: {result}")
        return result
    except Exception as e:
        logger.error(f"[webpage_sync] 실패: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def sync_all_to_db(max_months: int = 3) -> dict:
    """실행사별 시트에서 webpage_daily + agency_map 동기화."""
    from webpage.sheets import list_months_from_agency, get_ranking_by_agency, _parse_sheet_name
    import json

    conn = get_conn(EQUIPMENT_DB)
    total_inserted = 0
    sheets_processed = 0
    agency_changes = []

    try:
        months = list_months_from_agency()
        months = months[:max_months]

        latest_agency_map = {}
        latest_fetched = False

        for sheet_name in months:
            try:
                year, month = _parse_sheet_name(sheet_name)
            except ValueError:
                continue

            try:
                result = get_ranking_by_agency(sheet_name)
            except Exception as e:
                logger.warning(f"웹페이지 실행사 시트 '{sheet_name}' 읽기 실패: {e}")
                continue

            ranking = result["ranking"]

            if not latest_fetched and result["agency_map"]:
                latest_agency_map = result["agency_map"]
                latest_fetched = True

            # Save nosul_map to webpage_branch_monthly
            nosul_map = result.get("nosul_map", {})
            for branch_name, nosul_val in nosul_map.items():
                conn.execute("""
                    INSERT OR REPLACE INTO webpage_branch_monthly
                    (year, month, branch_name, nosul_count, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (year, month, branch_name, nosul_val))

            branches = ranking.get("branches", [])

            for b in branches:
                branch_name = b.get("branch", "")
                keyword = b.get("keyword", "")
                daily = b.get("daily", [])

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

                    conn.execute("""
                        INSERT OR REPLACE INTO webpage_daily
                        (date, branch_id, branch_name, keyword, is_exposed, executor, source)
                        VALUES (?, ?, ?, ?, ?, ?, 'sheets')
                    """, (date_str, branch_id, branch_name, keyword, is_exposed, executor))
                    total_inserted += 1

            sheets_processed += 1

        # Update agency_map_webpage
        if latest_agency_map:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'agency_map_webpage'"
            ).fetchone()
            old_map = json.loads(row["value"]) if row else {}

            for branch, new_agency in latest_agency_map.items():
                old_agency = old_map.get(branch, "").strip()
                if old_agency and old_agency != new_agency:
                    agency_changes.append({"branch": branch, "from": old_agency, "to": new_agency})

            merged_map = {**old_map, **latest_agency_map}
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                ("agency_map_webpage", json.dumps(merged_map, ensure_ascii=False)),
            )

        conn.commit()

        result = {
            "ok": True,
            "sheets_processed": sheets_processed,
            "records_saved": total_inserted,
            "agency_changes": agency_changes,
        }

        from datetime import datetime
        detail = f"{sheets_processed}개 시트 (실행사별)"
        if agency_changes:
            detail += f", 실행사 변경 {len(agency_changes)}건"
        conn.execute("""
            INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at)
            VALUES (?, ?, 0, 0, ?, ?)
        """, ("webpage_sheets_to_db", total_inserted, detail,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

        logger.info(f"[webpage_sync] 완료: {result}")
        return result
    except Exception as e:
        logger.error(f"[webpage_sync] 실패: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
