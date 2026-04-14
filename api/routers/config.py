"""앱 설정 라우터 — GET/POST /config/agency-map."""

import json
from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user, require_role
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/agency-map")
async def get_agency_map(
    user: Annotated[dict, Depends(get_current_user)],
    type: Literal["place", "webpage"] = Query(..., description="매핑 유형: place 또는 webpage"),
):
    """실행사 매핑 조회.

    Returns: {branch_name: agency_name, ...}
    """
    key = f"agency_map_{type}"
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"agency_map_{type} 설정이 없습니다.")
        return json.loads(row["value"])
    finally:
        conn.close()


@router.post("/agency-map")
def update_agency_map(
    body: dict,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    """실행사 매핑 저장 (admin 전용).

    Body: {"type": "place"|"webpage", "data": {branch: agency, ...}}
    """
    map_type = body.get("type")
    if map_type not in ("place", "webpage"):
        raise HTTPException(status_code=400, detail="type은 'place' 또는 'webpage'여야 합니다.")
    data = body.get("data", {})
    key = f"agency_map_{map_type}"
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings(key, value, updated_at) VALUES(?, ?, datetime('now'))",
            (key, json.dumps(data, ensure_ascii=False)),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/agency-sheets")
async def get_agency_sheets(
    user: Annotated[dict, Depends(get_current_user)],
    type: Literal["place", "webpage"] = Query("place", description="시트 유형"),
):
    """실행사별 구글시트 설정 조회."""
    key = f"agency_sheets_{type}"
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return {}
        return json.loads(row["value"])
    finally:
        conn.close()


@router.post("/agency-sheets")
def update_agency_sheets(
    body: dict,
    user: Annotated[dict, Depends(require_role("admin"))],
):
    """실행사별 구글시트 설정 저장 (admin 전용)."""
    import re
    map_type = body.get("type", "place")
    if map_type not in ("place", "webpage"):
        raise HTTPException(status_code=400, detail="type은 'place' 또는 'webpage'여야 합니다.")
    data = body.get("data", {})
    # URL에서 시트 ID 추출
    cleaned = {}
    for name, val in data.items():
        name = name.strip()
        val = val.strip()
        if not name or not val:
            continue
        m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", val)
        if m:
            cleaned[name] = m.group(1)
        else:
            cleaned[name] = val

    key = f"agency_sheets_{map_type}"
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_settings(key, value, updated_at) VALUES(?, ?, datetime('now'))",
            (key, json.dumps(cleaned, ensure_ascii=False)),
        )
        conn.commit()
        return {"ok": True, "saved": cleaned}
    finally:
        conn.close()


@router.get("/agency-stats")
async def get_agency_stats(
    user: Annotated[dict, Depends(get_current_user)],
    type: Literal["place", "webpage"] = Query("place"),
    months: int = Query(6, description="최근 N개월 (date_from 미지정 시 사용)"),
    date_from: str = Query(None, description="시작일 (YYYY-MM-DD)"),
    date_to: str = Query(None, description="종료일 (YYYY-MM-DD)"),
):
    """실행사별 성과 통계 — 기간별 성공률, 지점별 상세."""
    from datetime import date as date_cls, timedelta

    today = date_cls.today()
    if date_from and date_to:
        start_date = date_cls.fromisoformat(date_from)
        today = date_cls.fromisoformat(date_to)
    else:
        start_date = (today.replace(day=1) - timedelta(days=30 * (months - 1))).replace(day=1)

    table = "place_daily" if type == "place" else "webpage_daily"
    agency_key = f"agency_map_{type}"

    conn = get_conn(EQUIPMENT_DB)
    try:
        # 실행사 매핑 로드
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (agency_key,)).fetchone()
        agency_map = json.loads(row["value"]) if row else {}

        # 기간 내 전체 데이터 집계 (지점별, 월별)
        # 미작업일/미래 날짜 제외:
        #   place: rank가 NULL이고 미노출인 행 제외
        #   webpage: executor가 빈값이고 미노출인 행 제외 (rank 컬럼 항상 NULL)
        if type == "place":
            work_filter = "AND NOT (is_exposed = 0 AND (rank IS NULL OR rank = 0))"
        else:
            work_filter = "AND NOT (is_exposed = 0 AND (executor IS NULL OR executor = ''))"

        rows = conn.execute(f"""
            SELECT branch_name,
                   strftime('%Y-%m', date) AS month,
                   COUNT(*) AS total_days,
                   SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS exposed_days
            FROM {table}
            WHERE date >= ? AND date <= ?
              {work_filter}
            GROUP BY branch_name, strftime('%Y-%m', date)
            ORDER BY branch_name, month
        """, (start_date.isoformat(), today.isoformat())).fetchall()

        # 지점별 데이터 구조화
        branch_data = {}
        for r in rows:
            bname = r["branch_name"]
            if bname not in branch_data:
                branch_data[bname] = {"monthly": {}, "total_days": 0, "exposed_days": 0}
            branch_data[bname]["monthly"][r["month"]] = {
                "total": r["total_days"],
                "exposed": r["exposed_days"],
                "rate": round(r["exposed_days"] / r["total_days"] * 100, 1) if r["total_days"] > 0 else 0,
            }
            branch_data[bname]["total_days"] += r["total_days"]
            branch_data[bname]["exposed_days"] += r["exposed_days"]

        # 연속일 조회 — 전체 기간, 미작업일 건너뛰고 실제 작업일만 카운트
        streak_rows = conn.execute(f"""
            SELECT branch_name, date, is_exposed
            FROM {table}
            WHERE date <= ?
              AND NOT (is_exposed = 0 AND {"(rank IS NULL OR rank = 0)" if type == "place" else "(executor IS NULL OR executor = '')"})
            ORDER BY branch_name, date DESC
        """, (today.isoformat(),)).fetchall()

        # 총노출/총진행 — 전체 기간
        alltime_rows = conn.execute(f"""
            SELECT branch_name,
                   COUNT(*) AS total_days,
                   SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS exposed_days
            FROM {table}
            WHERE date <= ?
              {work_filter}
            GROUP BY branch_name
        """, (today.isoformat(),)).fetchall()
        alltime_total = {r["branch_name"]: r["total_days"] for r in alltime_rows}
        alltime_exposed = {r["branch_name"]: r["exposed_days"] for r in alltime_rows}

        streaks = {}
        current_branch = None
        current_streak = 0
        for r in streak_rows:
            if r["branch_name"] != current_branch:
                if current_branch:
                    streaks[current_branch] = current_streak
                current_branch = r["branch_name"]
                current_streak = 0
                counting = True
            if counting:
                if r["is_exposed"] == 1:
                    current_streak += 1
                else:
                    counting = False
        if current_branch:
            streaks[current_branch] = current_streak

        # 변경 이력 로드 → 월별 담당 실행사 역추적
        history_rows = conn.execute(
            "SELECT branch_name, from_agency, to_agency, changed_at FROM agency_map_history WHERE map_type = ? ORDER BY changed_at",
            (type,)
        ).fetchall()
        history_by_branch: dict[str, list] = {}
        for hr in history_rows:
            history_by_branch.setdefault(hr["branch_name"], []).append(dict(hr))

        def _get_monthly_agency(bname: str, current_ag: str, months: list[str]) -> dict[str, str]:
            """변경 이력으로 월별 담당 실행사 역추적."""
            changes = history_by_branch.get(bname, [])
            if not changes:
                return {m: current_ag for m in months}
            # 변경 이력을 날짜순 정렬 (이미 정렬됨)
            result = {}
            for m in months:
                month_end = f"{m}-28"
                # 이 월 이전의 마지막 변경 찾기
                agency = current_ag
                for c in reversed(changes):
                    if c["changed_at"] <= month_end:
                        agency = c["to_agency"]
                        break
                else:
                    # 모든 변경이 이 월 이후 → 첫 변경의 from_agency
                    if changes and changes[0]["changed_at"] > month_end:
                        agency = changes[0]["from_agency"]
                result[m] = agency
            return result

        # 실행사별 집계 — 월별 담당 실행사 기준으로 분배
        agencies = {}
        for bname, bdata in branch_data.items():
            current_agency = agency_map.get(bname, "미배정").strip() or "미배정"
            all_m = sorted(bdata["monthly"].keys())
            monthly_ag = _get_monthly_agency(bname, current_agency, all_m)

            # 현재 실행사 기준으로 branches 목록에는 추가
            if current_agency not in agencies:
                agencies[current_agency] = {"branches": [], "total_days": 0, "exposed_days": 0}

            at_total = alltime_total.get(bname, bdata["total_days"])
            at_exposed = alltime_exposed.get(bname, bdata["exposed_days"])
            rate = round(at_exposed / at_total * 100, 1) if at_total > 0 else 0
            agencies[current_agency]["branches"].append({
                "branch": bname,
                "total_days": at_total,       # 전체 기간
                "exposed_days": at_exposed,   # 전체 기간
                "rate": rate,                 # 전체 기간 성공률
                "streak": streaks.get(bname, 0),                                   # 전체 기간
                "monthly": bdata["monthly"],
                "monthly_agency": monthly_ag,
            })

            # 실행사 합산은 월별 담당 기준으로 분배
            for m, mdata in bdata["monthly"].items():
                responsible = monthly_ag.get(m, current_agency)
                if responsible not in agencies:
                    agencies[responsible] = {"branches": [], "total_days": 0, "exposed_days": 0}
                agencies[responsible]["total_days"] += mdata["total"]
                agencies[responsible]["exposed_days"] += mdata["exposed"]

        # 실행사 요약
        result = []
        for agency_name, adata in agencies.items():
            # 전체 기간 성공률: 소속 지점의 alltime 합산
            ag_total = sum(b["total_days"] for b in adata["branches"])
            ag_exposed = sum(b["exposed_days"] for b in adata["branches"])
            rate = round(ag_exposed / ag_total * 100, 1) if ag_total > 0 else 0
            avg_streak = round(sum(b["streak"] for b in adata["branches"]) / len(adata["branches"]), 1) if adata["branches"] else 0

            # 월별 추이 — 해당 월에 이 실행사가 담당한 지점만 집계
            all_months = sorted(set(m for b in adata["branches"] for m in b["monthly"]))
            monthly_rates = {}
            for m in all_months:
                m_total = 0
                m_exposed = 0
                for b in adata["branches"]:
                    if b.get("monthly_agency", {}).get(m) == agency_name and m in b["monthly"]:
                        m_total += b["monthly"][m]["total"]
                        m_exposed += b["monthly"][m]["exposed"]
                monthly_rates[m] = round(m_exposed / m_total * 100, 1) if m_total > 0 else 0

            # 추세 (최근 2개월 비교)
            trend = "→"
            if len(all_months) >= 2:
                prev = monthly_rates.get(all_months[-2], 0)
                curr = monthly_rates.get(all_months[-1], 0)
                if curr > prev + 5:
                    trend = "↑"
                elif curr < prev - 5:
                    trend = "↓"

            result.append({
                "agency": agency_name,
                "branch_count": len(adata["branches"]),
                "total_days": adata["total_days"],
                "exposed_days": adata["exposed_days"],
                "rate": rate,
                "avg_streak": avg_streak,
                "trend": trend,
                "monthly": monthly_rates,
                "branches": sorted(adata["branches"], key=lambda b: b["rate"], reverse=True),
            })

        result.sort(key=lambda a: a["rate"], reverse=True)

        return {
            "type": type,
            "period": f"{start_date.isoformat()} ~ {today.isoformat()}",
            "agencies": result,
        }
    finally:
        conn.close()


@router.get("/dashboard-stats")
async def get_dashboard_stats(
    user: Annotated[dict, Depends(get_current_user)],
    type: Literal["place", "webpage"] = Query("place"),
    months: int = Query(6, description="최근 N개월"),
):
    """전체 지점 성과 대시보드 통계."""
    from datetime import date as date_cls, timedelta

    today = date_cls.today()
    start_date = (today.replace(day=1) - timedelta(days=30 * (months - 1))).replace(day=1)
    yesterday = (today - timedelta(days=1)).isoformat()

    table = "place_daily" if type == "place" else "webpage_daily"

    if type == "place":
        work_filter = "AND NOT (is_exposed = 0 AND (rank IS NULL OR rank = 0))"
    else:
        work_filter = "AND NOT (is_exposed = 0 AND (executor IS NULL OR executor = ''))"

    conn = get_conn(EQUIPMENT_DB)
    try:
        # 1. 전체 지점 목록
        all_branches_rows = conn.execute(f"""
            SELECT DISTINCT branch_name FROM {table}
            WHERE date >= ? AND date <= ?
              {work_filter}
        """, (start_date.isoformat(), today.isoformat())).fetchall()
        all_branches = [r["branch_name"] for r in all_branches_rows]
        total_branches = len(all_branches)

        # 2. 전체 성공률 + 총노출/총진행 (선택 기간 내)
        overall_row = conn.execute(f"""
            SELECT COUNT(*) AS total_days,
                   SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS exposed_days
            FROM {table}
            WHERE date >= ? AND date <= ?
              {work_filter}
        """, (start_date.isoformat(), today.isoformat())).fetchone()
        total_days = overall_row["total_days"] or 0
        exposed_days = overall_row["exposed_days"] or 0
        overall_rate = round(exposed_days / total_days * 100, 1) if total_days > 0 else 0

        # 3. 오늘/어제 노출 지점 수
        today_row = conn.execute(f"""
            SELECT COUNT(DISTINCT branch_name) AS c FROM {table}
            WHERE date = ? AND is_exposed = 1
        """, (today.isoformat(),)).fetchone()
        today_exposed = today_row["c"] or 0

        yesterday_row = conn.execute(f"""
            SELECT COUNT(DISTINCT branch_name) AS c FROM {table}
            WHERE date = ? AND is_exposed = 1
        """, (yesterday,)).fetchone()
        yesterday_exposed = yesterday_row["c"] or 0

        # 4. 월별 전체 성공률
        monthly_rows = conn.execute(f"""
            SELECT strftime('%Y-%m', date) AS month,
                   COUNT(*) AS total_days,
                   SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS exposed_days
            FROM {table}
            WHERE date >= ? AND date <= ?
              {work_filter}
            GROUP BY month
            ORDER BY month
        """, (start_date.isoformat(), today.isoformat())).fetchall()
        monthly_rates = {}
        for r in monthly_rows:
            t = r["total_days"] or 0
            e = r["exposed_days"] or 0
            monthly_rates[r["month"]] = round(e / t * 100, 1) if t > 0 else 0

        # 5. 지점별 성공률 (분포용)
        branch_rates_rows = conn.execute(f"""
            SELECT branch_name,
                   COUNT(*) AS total_days,
                   SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS exposed_days
            FROM {table}
            WHERE date >= ? AND date <= ?
              {work_filter}
            GROUP BY branch_name
        """, (start_date.isoformat(), today.isoformat())).fetchall()

        distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}  # 90+/70-89/50-69/<50
        perfect_count = 0
        rates = []
        for r in branch_rates_rows:
            t = r["total_days"] or 0
            e = r["exposed_days"] or 0
            rate = round(e / t * 100, 1) if t > 0 else 0
            rates.append({"branch": r["branch_name"], "rate": rate})
            if rate >= 90:
                distribution["excellent"] += 1
                if rate == 100:
                    perfect_count += 1
            elif rate >= 70:
                distribution["good"] += 1
            elif rate >= 50:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1

        # 6. 평균 연속일 (전체 기간에서 계산, 미작업일 건너뛰고)
        streak_rows = conn.execute(f"""
            SELECT branch_name, date, is_exposed
            FROM {table}
            WHERE date <= ?
              {work_filter}
            ORDER BY branch_name, date DESC
        """, (today.isoformat(),)).fetchall()
        streaks = {}
        current_branch = None
        current_streak = 0
        counting = True
        for r in streak_rows:
            if r["branch_name"] != current_branch:
                if current_branch:
                    streaks[current_branch] = current_streak
                current_branch = r["branch_name"]
                current_streak = 0
                counting = True
            if counting:
                if r["is_exposed"] == 1:
                    current_streak += 1
                else:
                    counting = False
        if current_branch:
            streaks[current_branch] = current_streak

        avg_streak = round(sum(streaks.values()) / len(streaks), 1) if streaks else 0

        # 7. 변동 TOP (전월 대비 성공률 급변)
        month_list = sorted(monthly_rates.keys())
        top_changes = []
        if len(month_list) >= 2:
            prev_m = month_list[-2]
            curr_m = month_list[-1]
            # 지점별 전월 대비 변화
            branch_prev = {r["branch_name"]: r for r in conn.execute(f"""
                SELECT branch_name, COUNT(*) AS t, SUM(CASE WHEN is_exposed=1 THEN 1 ELSE 0 END) AS e
                FROM {table}
                WHERE strftime('%Y-%m', date) = ?
                  {work_filter}
                GROUP BY branch_name
            """, (prev_m,)).fetchall()}
            branch_curr = {r["branch_name"]: r for r in conn.execute(f"""
                SELECT branch_name, COUNT(*) AS t, SUM(CASE WHEN is_exposed=1 THEN 1 ELSE 0 END) AS e
                FROM {table}
                WHERE strftime('%Y-%m', date) = ?
                  {work_filter}
                GROUP BY branch_name
            """, (curr_m,)).fetchall()}
            changes = []
            for bname in set(branch_prev.keys()) & set(branch_curr.keys()):
                prev_r = round(branch_prev[bname]["e"] / branch_prev[bname]["t"] * 100, 1) if branch_prev[bname]["t"] > 0 else 0
                curr_r = round(branch_curr[bname]["e"] / branch_curr[bname]["t"] * 100, 1) if branch_curr[bname]["t"] > 0 else 0
                if prev_r > 0 and abs(curr_r - prev_r) >= 15:
                    changes.append({"branch": bname, "prev_rate": prev_r, "curr_rate": curr_r, "diff": round(curr_r - prev_r, 1)})
            top_changes = sorted(changes, key=lambda x: abs(x["diff"]), reverse=True)[:5]

        return {
            "type": type,
            "period": f"{start_date.isoformat()} ~ {today.isoformat()}",
            "total_branches": total_branches,
            "overall_rate": overall_rate,
            "total_days": total_days,
            "exposed_days": exposed_days,
            "today_exposed": today_exposed,
            "yesterday_exposed": yesterday_exposed,
            "avg_streak": avg_streak,
            "perfect_count": perfect_count,
            "monthly_rates": monthly_rates,
            "distribution": distribution,
            "top_changes": top_changes,
        }
    finally:
        conn.close()


@router.get("/agency-history")
async def get_agency_history(
    user: Annotated[dict, Depends(get_current_user)],
    type: Literal["place", "webpage"] = Query("place"),
    branch_name: str = Query(None),
):
    """실행사 변경 이력 조회."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        query = "SELECT * FROM agency_map_history WHERE map_type = ?"
        params = [type]
        if branch_name:
            query += " AND branch_name = ?"
            params.append(branch_name)
        query += " ORDER BY changed_at DESC, branch_name"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
