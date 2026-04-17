"""플레이스 구글시트 → DB 전체 동기화."""

import logging
from datetime import date

from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)


def sync_all_to_db_legacy() -> dict:
    """모든 월별 시트 데이터를 place_daily 테이블에 동기화. (통합시트 방식 — 레거시)"""
    from place.sheets import list_months, get_ranking, _parse_sheet_name

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
                    is_exposed = 1 if d.get("success") else 0
                    rank = d.get("rank")

                    # UPSERT
                    conn.execute("""
                        INSERT OR REPLACE INTO place_daily
                        (date, branch_id, branch_name, keyword, is_exposed, rank, source)
                        VALUES (?, ?, ?, ?, ?, ?, 'sheets')
                    """, (date_str, branch_id, branch_name, keyword, is_exposed, rank))
                    total_inserted += 1

            sheets_processed += 1

        conn.commit()
        result = {
            "ok": True,
            "sheets_processed": sheets_processed,
            "records_saved": total_inserted,
        }
        # 동기화 이력 기록
        from datetime import datetime
        conn.execute("""
            INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at)
            VALUES (?, ?, 0, 0, ?, ?)
        """, ("place_sheets_to_db", total_inserted, f"{sheets_processed}개 시트",
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        logger.info(f"[place_sync] 완료: {result}")
        return result
    except Exception as e:
        logger.error(f"[place_sync] 실패: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def sync_all_to_db(target_month: str | None = None) -> dict:
    """실행사별 시트에서 place_daily + agency_map 동기화.

    Args:
        target_month: YYYY-MM 형식. None이면 이번 달만.
    """
    from place.sheets import list_months_from_agency, get_ranking_by_agency, _parse_sheet_name
    import json

    conn = get_conn(EQUIPMENT_DB)
    total_inserted = 0
    sheets_processed = 0
    agency_changes = []  # Track agency mapping changes

    try:
        months = list_months_from_agency()
        if target_month:
            try:
                t_year, t_month = map(int, target_month.split("-"))
                months = [m for m in months if _parse_sheet_name(m) == (t_year, t_month)]
            except Exception:
                months = []
        else:
            months = months[:1]  # 기본: 이번 달만

        latest_agency_map = {}  # 최신 월의 실행사 매핑
        latest_fetched = False   # 최신 월만 agency_map 추출

        for sheet_name in months:
            try:
                year, month = _parse_sheet_name(sheet_name)
            except ValueError:
                logger.warning(f"시트 이름 파싱 불가, 건너뜀: {sheet_name}")
                continue

            try:
                result = get_ranking_by_agency(sheet_name)
            except Exception as e:
                logger.warning(f"실행사 시트 '{sheet_name}' 읽기 실패: {e}")
                continue

            ranking = result["ranking"]

            # 최신 월에서만 agency_map 추출 (months[0]이 최신)
            if not latest_fetched and result["agency_map"]:
                latest_agency_map = result["agency_map"]
                latest_fetched = True

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
                    is_exposed = 1 if d.get("success") else 0
                    rank = d.get("rank")

                    conn.execute("""
                        INSERT OR REPLACE INTO place_daily
                        (date, branch_id, branch_name, keyword, is_exposed, rank, source)
                        VALUES (?, ?, ?, ?, ?, ?, 'sheets')
                    """, (date_str, branch_id, branch_name, keyword, is_exposed, rank))
                    total_inserted += 1

            sheets_processed += 1

            # nosul_map 저장 (AF열 노출일수)
            nosul_map = result.get("nosul_map", {})
            for branch_name, nosul_val in nosul_map.items():
                conn.execute("""
                    INSERT OR REPLACE INTO place_branch_monthly
                    (year, month, branch_name, nosul_count, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                """, (year, month, branch_name, nosul_val))

        # Update agency_map_place in DB
        if latest_agency_map:
            # Load current map from DB
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = 'agency_map_place'"
            ).fetchone()
            old_map = json.loads(row["value"]) if row else {}

            # Detect changes
            for branch, new_agency in latest_agency_map.items():
                old_agency = old_map.get(branch, "").strip()
                if old_agency and old_agency != new_agency:
                    agency_changes.append({
                        "branch": branch,
                        "from": old_agency,
                        "to": new_agency,
                    })

            # Save agency changes to history table
            for change in agency_changes:
                conn.execute("""
                    INSERT OR IGNORE INTO agency_map_history
                    (branch_name, map_type, from_agency, to_agency, changed_at, detected_at)
                    VALUES (?, 'place', ?, ?, date('now','localtime'), datetime('now','localtime'))
                """, (change["branch"], change["from"], change["to"]))

            # Merge: preserve branches already in DB that aren't in any agency sheet
            merged_map = {**old_map, **latest_agency_map}

            # Save updated map
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                ("agency_map_place", json.dumps(merged_map, ensure_ascii=False)),
            )

        conn.commit()

        result = {
            "ok": True,
            "sheets_processed": sheets_processed,
            "records_saved": total_inserted,
            "agency_changes": agency_changes,
        }

        # Log sync
        from datetime import datetime
        detail = f"{sheets_processed}개 시트 (실행사별)"
        if agency_changes:
            detail += f", 실행사 변경 {len(agency_changes)}건"
        conn.execute("""
            INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at)
            VALUES (?, ?, 0, 0, ?, ?)
        """, ("place_sheets_to_db", total_inserted, detail,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

        logger.info(f"[place_sync] 완료: {result}")
        return result
    except Exception as e:
        logger.error(f"[place_sync] 실패: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
