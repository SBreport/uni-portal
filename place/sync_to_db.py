"""플레이스 구글시트 → DB 전체 동기화."""

import logging
import threading
from datetime import date

from shared.db import get_conn, EQUIPMENT_DB
from shared.branch_resolver import resolve_evt_branch_id

# 수동 매핑은 evt_branches.aliases 컬럼으로 이전됨 (resolver가 자동 처리).
# 신규 별칭이 필요하면: UPDATE evt_branches SET aliases = '["..."]' WHERE id = ?

logger = logging.getLogger(__name__)

_sync_lock = threading.Lock()


def sync_all_to_db(target_month: str | None = None, triggered_by: str = "manual") -> dict:
    """실행사별 시트에서 place_daily + agency_map 동기화.

    Args:
        target_month: YYYY-MM 형식. None이면 이번 달만.
        triggered_by: 'manual' 또는 'auto'.
    """
    if not _sync_lock.acquire(blocking=False):
        return {"ok": False, "skipped": True, "reason": "이미 동기화가 진행 중입니다"}

    try:
        return _sync_all_to_db_inner(target_month, triggered_by)
    finally:
        _sync_lock.release()


def _sync_all_to_db_inner(target_month: str | None, triggered_by: str) -> dict:
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

            # 시트에 등장한 지점별 최신 is_paused 집계 (루프 끝난 후 일괄 처리)
            paused_flags: dict[str, int] = {}

            for b in branches:
                branch_name = b.get("branch", "")
                # 오염 패턴 차단 — "(휴식)" 같은 시트 입력 오류 자동 skip
                if "(휴식)" in branch_name:
                    logger.warning(f"[place_sync] 오염 패턴 감지, 건너뜀: {branch_name}")
                    continue
                keyword = b.get("keyword", "")
                daily = b.get("daily", [])

                branch_id = resolve_evt_branch_id(conn, branch_name) or 0

                # is_paused: 시트 short_name 매칭으로 나중에 일괄 반영
                paused_flags[branch_name] = 1 if b.get("is_paused") else 0

                for d in daily:
                    day = d.get("day")
                    if not day:
                        continue
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    is_exposed = 1 if d.get("success") else 0
                    rank = d.get("rank")

                    conn.execute("""
                        INSERT OR REPLACE INTO place_daily
                        (date, branch_id, branch_name, keyword, is_exposed, rank, source, evt_branch_id)
                        VALUES (?, ?, ?, ?, ?, ?, 'sheets', ?)
                    """, (date_str, branch_id, branch_name, keyword, is_exposed, rank, branch_id))
                    total_inserted += 1

            sheets_processed += 1

            # 휴식 플래그 일괄 반영 — 시트 branch_name에 포함된 short_name으로 매칭
            # 예: 시트 '안양유앤아이' → evt_branches.short_name='안양' → is_paused 업데이트
            from place.pause_history import ensure_pause_history_table, record_pause_change
            ensure_pause_history_table(conn)

            # 변경 전 is_paused 값 미리 조회
            prev_paused_map = {
                r["id"]: r["is_paused"]
                for r in conn.execute("SELECT id, is_paused FROM evt_branches").fetchall()
            }

            today_str = date.today().isoformat()

            for sheet_branch, is_paused in paused_flags.items():
                if not sheet_branch:
                    continue
                row = conn.execute(
                    """SELECT id FROM evt_branches
                       WHERE short_name IS NOT NULL AND short_name != ''
                         AND INSTR(?, short_name) > 0
                       ORDER BY LENGTH(short_name) DESC LIMIT 1""",
                    (sheet_branch,)
                ).fetchone()
                if row:
                    bid = row["id"]
                    old_paused = prev_paused_map.get(bid, 0) or 0
                    record_pause_change(conn, bid, sheet_branch, old_paused, is_paused, today_str)
                    conn.execute(
                        "UPDATE evt_branches SET is_paused = ? WHERE id = ?",
                        (is_paused, bid)
                    )

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

        # ── SB체커 키워드 자동 연동 (Phase 1) ──
        try:
            _auto_sync_rank_keywords(conn)
        except Exception as e:
            logger.warning(f"[place_sync] 키워드 자동 연동 실패: {e}")

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
            INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at, triggered_by)
            VALUES (?, ?, 0, 0, ?, ?, ?)
        """, ("place_sheets_to_db", total_inserted, detail,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S"), triggered_by))
        conn.commit()

        logger.info(f"[place_sync] 완료: {result}")
        return result
    except Exception as e:
        logger.error(f"[place_sync] 실패: {e}", exc_info=True)
        try:
            from datetime import datetime
            conn.execute("""
                INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at, triggered_by)
                VALUES (?, 0, 0, 0, ?, ?, ?)
            """, ("place_sheets_to_db", f"실패: {e}",
                  datetime.now().strftime("%Y-%m-%d %H:%M:%S"), triggered_by))
            conn.commit()
        except Exception:
            pass
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def _auto_sync_rank_keywords(conn) -> dict:
    """place_daily의 (branch_id, keyword) 중 rank_check_keywords 미등록 항목을 자동 등록.

    - place_id는 evt_branches.default_place_id에서 자동 채움. 없으면 빈 문자열 + is_active=0.
    - 이미 origin='manual'로 단독 추가된 키워드를 외주사가 추적 시작하면 'auto_synced'로 승격.
    """
    # 외주사 키워드 distinct
    rows = conn.execute("""
        SELECT DISTINCT pd.branch_id, pd.branch_name, pd.keyword,
               COALESCE(eb.default_place_id, '') AS default_place_id
        FROM place_daily pd
        LEFT JOIN evt_branches eb ON eb.id = pd.branch_id
        WHERE pd.keyword != '' AND pd.branch_id > 0
    """).fetchall()

    inserted = 0
    promoted = 0
    for r in rows:
        bid = r["branch_id"]
        kw = r["keyword"]
        default_pid = r["default_place_id"] or ""

        existing = conn.execute(
            "SELECT id, origin, place_id FROM rank_check_keywords WHERE branch_id=? AND keyword=?",
            (bid, kw)
        ).fetchone()

        if existing is None:
            # 신규 자동 연동 — place_id 있으면 즉시 활성화, 없으면 대기
            is_active = 1 if default_pid else 0
            conn.execute("""
                INSERT INTO rank_check_keywords
                  (branch_id, branch_name, keyword, search_keyword, place_id, guaranteed_rank, is_active, memo, origin)
                VALUES (?, ?, ?, '', ?, 5, ?, '', 'auto_synced')
            """, (bid, r["branch_name"], kw, default_pid, is_active))
            inserted += 1
        elif existing["origin"] == "manual":
            # 단독 추적이었는데 외주사가 추적 시작 → 승격
            conn.execute(
                "UPDATE rank_check_keywords SET origin='auto_synced' WHERE id=?",
                (existing["id"],)
            )
            promoted += 1

    conn.commit()
    return {"inserted": inserted, "promoted": promoted}
