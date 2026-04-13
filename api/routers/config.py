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

        # 연속일 조회 (최신 데이터 기준)
        streak_rows = conn.execute(f"""
            SELECT branch_name, date, is_exposed
            FROM {table}
            WHERE date >= ? AND date <= ?
            ORDER BY branch_name, date DESC
        """, ((today - timedelta(days=60)).isoformat(), today.isoformat())).fetchall()

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

        # 실행사별 집계
        agencies = {}
        for bname, bdata in branch_data.items():
            agency = agency_map.get(bname, "미배정").strip() or "미배정"
            if agency not in agencies:
                agencies[agency] = {"branches": [], "total_days": 0, "exposed_days": 0}

            rate = round(bdata["exposed_days"] / bdata["total_days"] * 100, 1) if bdata["total_days"] > 0 else 0
            all_m = sorted(bdata["monthly"].keys())
            monthly_ag = _get_monthly_agency(bname, agency, all_m)
            agencies[agency]["branches"].append({
                "branch": bname,
                "total_days": bdata["total_days"],
                "exposed_days": bdata["exposed_days"],
                "rate": rate,
                "streak": streaks.get(bname, 0),
                "monthly": bdata["monthly"],
                "monthly_agency": monthly_ag,
            })
            agencies[agency]["total_days"] += bdata["total_days"]
            agencies[agency]["exposed_days"] += bdata["exposed_days"]

        # 실행사 요약
        result = []
        for agency_name, adata in agencies.items():
            rate = round(adata["exposed_days"] / adata["total_days"] * 100, 1) if adata["total_days"] > 0 else 0
            avg_streak = round(sum(b["streak"] for b in adata["branches"]) / len(adata["branches"]), 1) if adata["branches"] else 0

            # 월별 추이
            all_months = sorted(set(m for b in adata["branches"] for m in b["monthly"]))
            monthly_rates = {}
            for m in all_months:
                m_total = sum(b["monthly"].get(m, {}).get("total", 0) for b in adata["branches"])
                m_exposed = sum(b["monthly"].get(m, {}).get("exposed", 0) for b in adata["branches"])
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
