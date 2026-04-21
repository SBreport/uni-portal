"""웹페이지 노출 (Webpage Ranking) API 라우터."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from api.deps import get_current_user, require_role

router = APIRouter(prefix="/webpage", tags=["Webpage"])

# 회복 이벤트 집계 기준: 이 일수 이상 실패가 이어진 뒤 다시 성공해야 '회복'으로 본다.
# (실패 일수 기준 — gap_days = 실패 일수 + 1 이므로 gap >= RECOVERY_MIN_FAILURE_DAYS + 1 일 때 회복)
RECOVERY_MIN_FAILURE_DAYS = 3


@router.get("/daily")
async def get_daily(
    branch_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT * FROM webpage_daily WHERE 1=1"
        params = []
        if branch_id:
            sql += " AND branch_id = ?"
            params.append(branch_id)
        if date_from:
            sql += " AND date >= ?"
            params.append(date_from)
        if date_to:
            sql += " AND date <= ?"
            params.append(date_to)
        sql += " ORDER BY date DESC, branch_name"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@router.get("/trends")
async def get_trends(branch_id: int, keyword: Optional[str] = None):
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT date, is_exposed, rank, executor FROM webpage_daily WHERE branch_id = ?"
        params = [branch_id]
        if keyword:
            sql += " AND keyword = ?"
            params.append(keyword)
        sql += " ORDER BY date"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@router.get("/months")
def get_months(user: dict = Depends(get_current_user)):
    """사용 가능한 월별 시트 목록 반환."""
    try:
        from webpage.sheets import list_months
        return list_months()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"구글 시트 연결 실패: {e}")


@router.get("/ranking")
def get_ranking(
    month: str = Query(..., description="시트 이름 (예: '2026.3')"),
    user: dict = Depends(get_current_user),
):
    """특정 월의 웹페이지 노출 데이터 반환."""
    try:
        from webpage.sheets import get_ranking
        return get_ranking(month)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"구글 시트 연결 실패: {e}")


class SyncRequest(BaseModel):
    target_month: str | None = None


@router.post("/sync-to-db")
async def sync_webpage_to_db(
    body: SyncRequest = Body(default_factory=SyncRequest),
    user: dict = Depends(require_role("admin")),
):
    """구글시트 → DB 동기화 (admin 전용). target_month 없으면 이번 달만."""
    from webpage.sync_to_db import sync_all_to_db
    return sync_all_to_db(target_month=body.target_month)


@router.get("/last-sync")
async def get_last_sync(user: dict = Depends(get_current_user)):
    """웹페이지 마지막 동기화 시각."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT synced_at, added, detail FROM sync_log WHERE sync_type = 'webpage_sheets_to_db' ORDER BY synced_at DESC LIMIT 1"
        ).fetchone()
        if row:
            return {"synced_at": row["synced_at"], "records": row["added"], "detail": row["detail"]}
        return {"synced_at": None}
    finally:
        conn.close()


@router.get("/ranking-daily")
async def get_ranking_daily(
    date: str = Query(..., description="조회 날짜 (YYYY-MM-DD)"),
    user: dict = Depends(get_current_user),
):
    """특정 날짜 기준 전 지점 웹페이지 노출 데이터 (최근5일·연속일 포함)."""
    from datetime import datetime, timedelta
    from shared.db import get_conn, EQUIPMENT_DB

    target = datetime.strptime(date, "%Y-%m-%d").date()
    range_from = (target - timedelta(days=30)).isoformat()
    range_to = target.isoformat()

    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT date, branch_id, branch_name, keyword, is_exposed, rank, executor
            FROM webpage_daily
            WHERE date >= ? AND date <= ?
            ORDER BY branch_name, date
        """, (range_from, range_to)).fetchall()

        # short_name 맵 (evt_branches.id → short_name)
        short_name_map = {
            r[0]: r[1] for r in conn.execute(
                "SELECT id, short_name FROM evt_branches WHERE short_name IS NOT NULL AND short_name != ''"
            ).fetchall()
        }

        branches: dict = {}
        for r in rows:
            bname = r["branch_name"]
            if bname not in branches:
                branches[bname] = {
                    "branch": bname,
                    "branch_id": r["branch_id"],
                    "keyword": r["keyword"],
                    "history": {},
                }
            branches[bname]["history"][r["date"]] = {
                "is_exposed": r["is_exposed"],
                "rank": r["rank"],
                "executor": r["executor"] or "",
            }

        # AF열 노출일수 조회
        target_year = target.year
        target_month = target.month
        nosul_rows = conn.execute("""
            SELECT branch_name, nosul_count FROM webpage_branch_monthly
            WHERE year = ? AND month = ?
        """, (target_year, target_month)).fetchall()
        nosul_db = {r["branch_name"]: r["nosul_count"] for r in nosul_rows}

        # 마지막 성공 날짜 집계 (target 이전, is_exposed=1)
        last_success_rows = conn.execute("""
            SELECT branch_id, keyword, MAX(date) AS last_success_date
            FROM webpage_daily
            WHERE date < ? AND is_exposed = 1
            GROUP BY branch_id, keyword
        """, (range_to,)).fetchall()
        last_success_map = {
            (r["branch_id"], r["keyword"]): r["last_success_date"]
            for r in last_success_rows
        }

        # recovery 계산용: (branch_id, keyword)별 전체 이력 (target 이하) — 접근 B
        recovery_history_rows = conn.execute("""
            SELECT date, branch_id, keyword,
                   CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END AS ok
            FROM webpage_daily
            WHERE date <= ?
            ORDER BY branch_id, keyword, date
        """, (range_to,)).fetchall()

        from collections import defaultdict
        _rh: dict = defaultdict(list)
        for r in recovery_history_rows:
            _rh[(r["branch_id"], r["keyword"])].append((r["date"], r["ok"]))

        def _calc_recovery(history: list, target_str: str):
            if not history:
                return None, None
            last_date, last_ok = history[-1]
            if last_date != target_str or not last_ok:
                return None, None
            streak_start_idx = len(history) - 1
            for i in range(len(history) - 2, -1, -1):
                d, ok = history[i]
                if ok:
                    streak_start_idx = i
                else:
                    break
            recovery_date = history[streak_start_idx][0]
            if streak_start_idx == 0:
                return recovery_date, None
            prev_success_date = None
            for i in range(streak_start_idx - 1, -1, -1):
                d, ok = history[i]
                if ok:
                    prev_success_date = d
                    break
            if prev_success_date is None:
                return recovery_date, None
            from datetime import datetime as _dt
            gap = (_dt.strptime(recovery_date, "%Y-%m-%d") - _dt.strptime(prev_success_date, "%Y-%m-%d")).days
            if gap - 1 < RECOVERY_MIN_FAILURE_DAYS:
                return None, None
            return recovery_date, gap

        recovery_map: dict = {}
        for key, hist in _rh.items():
            recovery_map[key] = _calc_recovery(hist, range_to)

        # 전체 기간 통계
        alltime_rows = conn.execute("""
            SELECT branch_name,
                   COUNT(*) AS total_days,
                   SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS total_exposed
            FROM webpage_daily
            WHERE date <= ?
            GROUP BY branch_name
        """, (range_to,)).fetchall()
        work_days_total = {r["branch_name"]: r["total_days"] for r in alltime_rows}
        total_exposed_map = {r["branch_name"]: r["total_exposed"] for r in alltime_rows}

        result = []
        for bname, bdata in branches.items():
            hist = bdata["history"]
            today_data = hist.get(date)

            recent = []
            for i in range(5, 0, -1):
                d = (target - timedelta(days=i)).isoformat()
                h = hist.get(d)
                recent.append({
                    "day": int(d.split("-")[2]),
                    "exposed": h["is_exposed"] if h else None,
                })

            streak = 0
            for i in range(0, 31):
                d = (target - timedelta(days=i)).isoformat()
                h = hist.get(d)
                if h and h["is_exposed"]:
                    streak += 1
                else:
                    break

            month_prefix = date[:7]
            month_exposed = sum(1 for d, h in hist.items() if d.startswith(month_prefix) and h["is_exposed"])
            month_days = sum(1 for d in hist if d.startswith(month_prefix))

            today_exposed = bool(today_data["is_exposed"]) if today_data else False

            bid = bdata["branch_id"]
            kw = bdata["keyword"]
            last_success_date = last_success_map.get((bid, kw), None)
            _recovery_date, _recovery_gap = recovery_map.get((bid, kw), (None, None))

            result.append({
                "branch": bname,
                "branch_id": bid,
                "short_name": short_name_map.get(bid),
                "keyword": kw,
                "today_exposed": today_exposed,
                "streak": streak,
                "nosul_count": nosul_db.get(bname, month_exposed),
                "total_exposed": total_exposed_map.get(bname, 0),
                "work_days": work_days_total.get(bname, month_days),
                "status": "active" if today_exposed else ("fail" if today_data else "미달"),
                "daily": recent,
                "last_success_date": last_success_date,
                "recovery_date": _recovery_date,
                "recovery_gap": _recovery_gap,
            })

        return {
            "date": date,
            "branches": result,
            "summary": {
                "total": len(result),
                "success_today": sum(1 for b in result if b["today_exposed"]),
                "fail_today": sum(1 for b in result if b["status"] == "fail"),
                "midal": sum(1 for b in result if b["status"] == "미달"),
            },
            "source": "db",
        }
    finally:
        conn.close()


@router.get("/branch-detail")
async def get_branch_detail(
    branch_name: str = Query(...),
    keyword: str = Query(...),
    reference_date: str = Query(..., description="기준일 YYYY-MM-DD"),
    user: dict = Depends(get_current_user),
):
    """지점+키워드 상세 분석 패널 데이터 (성공률·연속기록·회복이력)."""
    from datetime import datetime
    from shared.db import get_conn, EQUIPMENT_DB

    ref = datetime.strptime(reference_date, "%Y-%m-%d").date()
    ref_year = ref.year
    ref_month = ref.month

    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT date, is_exposed
            FROM webpage_daily
            WHERE branch_name = ? AND keyword = ?
            ORDER BY date
        """, (branch_name, keyword)).fetchall()

        if not rows:
            return {
                "branch_name": branch_name,
                "keyword": keyword,
                "success_rate": {
                    "all":        {"success": 0, "total": 0, "pct": 0.0},
                    "this_month": {"success": 0, "total": 0, "pct": 0.0},
                    "last_month": {"success": 0, "total": 0, "pct": 0.0},
                },
                "longest": {
                    "success": {"days": 0, "from": None, "to": None},
                    "fail":    {"days": 0, "from": None, "to": None},
                },
                "current_success": {"days": 0, "from": None, "to": None},
                "recovery_history": [],
            }

        history = [(r["date"], bool(r["is_exposed"])) for r in rows if r["date"] <= reference_date]

        total_all = len(history)
        success_all = sum(1 for _, ok in history if ok)

        this_month_prefix = f"{ref_year}-{ref_month:02d}"
        if ref_month == 1:
            last_month_year, last_month_month = ref_year - 1, 12
        else:
            last_month_year, last_month_month = ref_year, ref_month - 1
        last_month_prefix = f"{last_month_year}-{last_month_month:02d}"

        this_month_hist = [(d, ok) for d, ok in history if d.startswith(this_month_prefix)]
        last_month_hist = [(d, ok) for d, ok in history if d.startswith(last_month_prefix)]

        def _rate(hist):
            t = len(hist)
            s = sum(1 for _, ok in hist if ok)
            return {"success": s, "total": t, "pct": round(s / t * 100, 1) if t else 0.0}

        def _longest_streak(history, target_ok: bool):
            best_days = 0
            best_from = None
            best_to = None
            cur_days = 0
            cur_from = None
            for d, ok in history:
                if ok == target_ok:
                    cur_days += 1
                    if cur_from is None:
                        cur_from = d
                    if cur_days > best_days:
                        best_days = cur_days
                        best_from = cur_from
                        best_to = d
                else:
                    cur_days = 0
                    cur_from = None
            return best_days, best_from, best_to

        suc_days, suc_from, suc_to = _longest_streak(history, True)
        fail_days, fail_from, fail_to = _longest_streak(history, False)

        if suc_to and suc_to == history[-1][0] and history[-1][1]:
            suc_to = None
        if fail_to and fail_to == history[-1][0] and not history[-1][1]:
            fail_to = None

        def _all_recovery_events(history):
            events = []
            n = len(history)
            i = 0
            while i < n:
                d, ok = history[i]
                if ok:
                    if i == 0 or not history[i - 1][1]:
                        prev_success_date = None
                        for j in range(i - 1, -1, -1):
                            if history[j][1]:
                                prev_success_date = history[j][0]
                                break
                        if prev_success_date is None:
                            events.append({
                                "recovery_date": d,
                                "gap_days": None,
                                "is_first_success": True,
                                "prev_success_date": None,
                            })
                        else:
                            from datetime import datetime as _dt
                            gap = (_dt.strptime(d, "%Y-%m-%d") - _dt.strptime(prev_success_date, "%Y-%m-%d")).days
                            if gap - 1 < RECOVERY_MIN_FAILURE_DAYS:
                                while i < n and history[i][1]:
                                    i += 1
                                continue
                            events.append({
                                "recovery_date": d,
                                "gap_days": gap,
                                "is_first_success": False,
                                "prev_success_date": prev_success_date,
                            })
                    while i < n and history[i][1]:
                        i += 1
                else:
                    i += 1
            return events

        recovery_events = _all_recovery_events(history)
        recovery_history = list(reversed(recovery_events[-10:]))

        # 현재 연속 성공 streak (reference_date 기준 역방향으로 카운트)
        cur_success_days = 0
        cur_success_from: str | None = None
        for d, ok in reversed(history):
            if ok:
                cur_success_days += 1
                cur_success_from = d
            else:
                break

        return {
            "branch_name": branch_name,
            "keyword": keyword,
            "success_rate": {
                "all":        {"success": success_all, "total": total_all, "pct": round(success_all / total_all * 100, 1) if total_all else 0.0},
                "this_month": _rate(this_month_hist),
                "last_month": _rate(last_month_hist),
            },
            "longest": {
                "success": {"days": suc_days,  "from": suc_from,  "to": suc_to},
                "fail":    {"days": fail_days, "from": fail_from, "to": fail_to},
            },
            "current_success": {
                "days": cur_success_days,
                "from": cur_success_from,
                "to": reference_date if cur_success_days > 0 else None,
            },
            "recovery_history": recovery_history,
        }
    finally:
        conn.close()


@router.get("/ranking-db")
async def get_ranking_from_db(
    year: int = Query(...),
    month: int = Query(...),
    user: dict = Depends(get_current_user),
):
    """DB에서 월별 웹페이지 노출 데이터 조회 (시트 대신)."""
    import calendar
    from datetime import date as _date
    from shared.db import get_conn, EQUIPMENT_DB

    conn = get_conn(EQUIPMENT_DB)
    try:
        date_from = f"{year}-{month:02d}-01"
        if month == 12:
            date_to = f"{year + 1}-01-01"
        else:
            date_to = f"{year}-{month + 1:02d}-01"

        rows = conn.execute("""
            SELECT date, branch_id, branch_name, keyword, is_exposed, rank, executor
            FROM webpage_daily
            WHERE date >= ? AND date < ?
            ORDER BY branch_name, date
        """, (date_from, date_to)).fetchall()

        # short_name 맵 (evt_branches.id → short_name)
        short_name_map_m = {
            r[0]: r[1] for r in conn.execute(
                "SELECT id, short_name FROM evt_branches WHERE short_name IS NOT NULL AND short_name != ''"
            ).fetchall()
        }

        # 지점별 그룹핑
        branches: dict = {}
        for r in rows:
            bname = r["branch_name"]
            if bname not in branches:
                bid_m = r["branch_id"]
                branches[bname] = {
                    "branch": bname,
                    "branch_id": bid_m,
                    "short_name": short_name_map_m.get(bid_m),
                    "keyword": r["keyword"],
                    "daily": [],
                }
            day = int(r["date"].split("-")[2])
            branches[bname]["daily"].append({
                "day": day,
                "exposed": r["is_exposed"],
                "mark": r["executor"] or "",
            })

        # 통계 계산
        result = []
        for bname, bdata in branches.items():
            daily = bdata["daily"]
            exposed = sum(1 for d in daily if d["exposed"])
            work_days = sum(1 for d in daily if d["mark"] in ("ㅇ", "x"))

            # streak (연속 노출일)
            streak = 0
            for d in reversed(daily):
                if d["exposed"]:
                    streak += 1
                else:
                    break

            bdata["nosul_count"] = exposed
            bdata["work_days"] = work_days
            bdata["streak"] = streak
            bdata["today_exposed"] = bool(daily[-1]["exposed"]) if daily else False
            bdata["status"] = "active" if (daily and daily[-1]["exposed"]) else ("fail" if daily else "미달")
            result.append(bdata)

        days_in_month = calendar.monthrange(year, month)[1]
        today = _date.today()
        today_index = today.day if today.year == year and today.month == month else days_in_month

        return {
            "year": year,
            "month": month,
            "days": days_in_month,
            "today_index": today_index,
            "branches": result,
            "summary": {
                "total": len(result),
                "success_today": sum(1 for b in result if b["today_exposed"]),
                "fail_today": sum(1 for b in result if b["status"] == "fail"),
                "midal": sum(1 for b in result if b["status"] == "미달"),
            },
            "source": "db",
        }
    finally:
        conn.close()
