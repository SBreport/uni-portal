"""웹페이지 노출 (Webpage Ranking) API 라우터."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user, require_role

router = APIRouter(prefix="/webpage", tags=["Webpage"])


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


@router.post("/sync-to-db")
async def sync_webpage_to_db(user: dict = Depends(require_role("admin"))):
    """구글시트 → DB 전체 동기화 (admin 전용)."""
    from webpage.sync_to_db import sync_all_to_db
    return sync_all_to_db()


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

            result.append({
                "branch": bname,
                "branch_id": bdata["branch_id"],
                "keyword": bdata["keyword"],
                "today_exposed": today_exposed,
                "streak": streak,
                "nosul_count": month_exposed,
                "work_days": month_days,
                "status": "active" if today_exposed else ("fail" if today_data else "미달"),
                "daily": recent,
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

        # 지점별 그룹핑
        branches: dict = {}
        for r in rows:
            bname = r["branch_name"]
            if bname not in branches:
                branches[bname] = {
                    "branch": bname,
                    "branch_id": r["branch_id"],
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
