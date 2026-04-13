"""플레이스 일별 스냅샷 — 실행사별 시트에서 빈 기간만 증분 갱신."""

import logging
from datetime import date, timedelta

from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)


def take_snapshot():
    """마지막 동기화 이후 빈 날짜만 실행사별 시트에서 읽어 DB에 저장."""
    try:
        from place.sheets import get_ranking_by_agency, list_months_from_agency, _parse_sheet_name
    except Exception as e:
        logger.error(f"[place_snapshot] sheets 모듈 임포트 실패: {e}")
        return {"ok": False, "error": str(e)}

    today = date.today()
    conn = get_conn(EQUIPMENT_DB)

    try:
        # 마지막 동기화 날짜 조회
        row = conn.execute(
            "SELECT MAX(date) AS last_date FROM place_daily WHERE source = 'sheets'"
        ).fetchone()
        last_date_str = row["last_date"] if row and row["last_date"] else None

        # 최근 3일은 항상 재갱신 (원본 시트 수정분 반영)
        REFRESH_DAYS = 3
        refresh_start = today - timedelta(days=REFRESH_DAYS - 1)

        if last_date_str:
            last_date = date.fromisoformat(last_date_str)
            # 마지막 날짜의 다음 날 vs 최근 3일 중 더 이른 날짜
            incremental_start = last_date + timedelta(days=1)
            start_date = min(incremental_start, refresh_start)
        else:
            # 데이터 없으면 이번 달 1일부터
            start_date = today.replace(day=1)

        # 갱신할 날짜 범위
        missing_days = []
        d = start_date
        while d <= today:
            missing_days.append(d)
            d += timedelta(days=1)

        logger.info(f"[place_snapshot] 갱신 대상: {start_date} ~ {today} ({len(missing_days)}일)")

        # 필요한 월별 시트 파악
        months_needed = set()
        for d in missing_days:
            months_needed.add((d.year, d.month))

        # 실행사별 시트에서 월 목록 조회
        available_months = list_months_from_agency()

        inserted = 0
        for year, month in sorted(months_needed):
            # 해당 월의 시트 찾기
            sheet_name = None
            for name in available_months:
                try:
                    sy, sm = _parse_sheet_name(name)
                    if sy == year and sm == month:
                        sheet_name = name
                        break
                except ValueError:
                    continue

            if not sheet_name:
                logger.warning(f"[place_snapshot] {year}년 {month}월 시트를 찾을 수 없음")
                continue

            # 실행사별 시트에서 데이터 읽기
            try:
                result = get_ranking_by_agency(sheet_name)
            except Exception as e:
                logger.warning(f"[place_snapshot] 시트 '{sheet_name}' 읽기 실패: {e}")
                continue

            ranking = result["ranking"]
            branches = ranking.get("branches", [])

            # 이 월에서 갱신할 날짜들
            days_in_month = [d for d in missing_days if d.year == year and d.month == month]

            for b in branches:
                branch_name = b.get("branch", "")
                keyword = b.get("keyword", "")
                daily = b.get("daily", [])

                row = conn.execute(
                    "SELECT id FROM evt_branches WHERE name = ?", (branch_name,)
                ).fetchone()
                branch_id = row["id"] if row else 0

                for target_date in days_in_month:
                    # daily 배열에서 해당 날짜 데이터 찾기
                    day_data = None
                    for dd in daily:
                        if dd.get("day") == target_date.day:
                            day_data = dd
                            break

                    is_exposed = 1 if (day_data and day_data.get("success")) else 0
                    rank = day_data.get("rank") if day_data else None

                    conn.execute(
                        """INSERT OR REPLACE INTO place_daily
                           (date, branch_id, branch_name, keyword, is_exposed, rank, source)
                           VALUES (?, ?, ?, ?, ?, ?, 'sheets')""",
                        (target_date.isoformat(), branch_id, branch_name, keyword, is_exposed, rank)
                    )
                    inserted += 1

        conn.commit()

        # 동기화 로그 기록
        from datetime import datetime
        conn.execute("""
            INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at)
            VALUES (?, ?, 0, 0, ?, ?)
        """, ("place_daily_snapshot", inserted,
              f"{len(missing_days)}일 증분 갱신 (실행사별)",
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()

        logger.info(f"[place_snapshot] {inserted}건 저장 완료 ({start_date} ~ {today})")
        return {
            "ok": True,
            "date_range": f"{start_date.isoformat()} ~ {today.isoformat()}",
            "days": len(missing_days),
            "count": inserted,
        }
    except Exception as e:
        logger.error(f"[place_snapshot] 저장 실패: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()
