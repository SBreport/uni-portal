"""지점 정보 라우터 — 지점별 보유장비+이벤트+민원 통합 조회."""

from typing import Annotated, Optional
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from api.deps import get_current_user

router = APIRouter(prefix="/branch-info", tags=["Branch Info"])

# 장비 카테고리 → 이벤트 카테고리 매핑
# equipment.categories.id → evt_categories.id 목록
# 이벤트 카테고리는 세분화되어 있어 여러 개가 장비 카테고리 하나에 대응
EQUIP_CAT_TO_EVT_CATS: dict[int, list[int]] = {
    1: [2, 3],        # 리프팅 → 레이저리프팅, 실리프팅
    2: [6],           # 색소 → 색소/기미/잡티
    3: [4, 5, 8, 12, 13],  # 주사시술 → 보톡스, 필러, 스킨부스터, 활력주사, 윤곽
    4: [9],           # 여드름치료 → 여드름/모공
    5: [9],           # 여드름흉터 → 여드름/모공
    6: [11],          # 비만 → 비만/체형
    7: [7, 14, 15, 16],  # 기타 → 스킨케어, 첫방문이벤트, 요일이벤트, 기타
    8: [10],          # 제모 → 제모
}

# 카테고리별 색상 (pastel 톤)
CATEGORY_COLORS: dict[int, str] = {
    1: "#6366f1",  # 리프팅 - indigo
    2: "#f59e0b",  # 색소 - amber
    3: "#10b981",  # 주사시술 - emerald
    4: "#f87171",  # 여드름치료 - red
    5: "#fb923c",  # 여드름흉터 - orange
    6: "#8b5cf6",  # 비만 - violet
    7: "#94a3b8",  # 기타 - slate
    8: "#06b6d4",  # 제모 - cyan
}


@router.get("/branches")
async def list_branches(user: Annotated[dict, Depends(get_current_user)]):
    """지점 목록 (evt_branches 기반)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("SELECT id, name FROM evt_branches ORDER BY name").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/all/summary")
async def get_all_branches_summary(user: Annotated[dict, Depends(get_current_user)]):
    """전 지점 요약 (지점 선택 화면용)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        branches = conn.execute("SELECT id, name FROM evt_branches ORDER BY name").fetchall()

        result = []
        for b in branches:
            bid, bname = b["id"], b["name"]

            eq_count = conn.execute("""
                SELECT COUNT(*) FROM equipment e
                LEFT JOIN branches br ON e.branch_id = br.id
                WHERE br.name = ?
            """, (bname,)).fetchone()[0]

            ev_count = conn.execute(
                "SELECT COUNT(*) FROM evt_items WHERE branch_id = ?", (bid,)
            ).fetchone()[0]

            comp_open = conn.execute(
                "SELECT COUNT(*) FROM complaints WHERE branch_id = ? AND status != 'closed'", (bid,)
            ).fetchone()[0]

            result.append({
                "branch_id": bid,
                "branch_name": bname,
                "equipment_count": eq_count,
                "event_count": ev_count,
                "open_complaints": comp_open,
            })

        return result
    finally:
        conn.close()


@router.get("/{branch_id}/dashboard")
async def get_branch_dashboard(
    branch_id: int,
    user: Annotated[dict, Depends(get_current_user)],
    period_id: Optional[int] = Query(None, description="이벤트 기간 ID (없으면 현재 기간)"),
):
    """지점 카테고리 대시보드 — 4×2 카드 그리드용 데이터.

    응답 구조:
    {
      branch: {id, name},
      period: {id, label, year, start_month, end_month},
      summary: {equipment_total, events_total, complaints_active},
      categories: [
        {
          id, name, color,
          equipment_count,
          equipment_groups: [{device_info_id, device_info_name, total_qty, rows, can_merge}],
          event_count,
          event_avg_price,
          top_devices,
          events: [{id, display_name, event_price, raw_event_name}]
        }
      ]
    }
    """
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        # ── 지점 기본 정보 ──────────────────────────────────────────
        branch = conn.execute(
            "SELECT id, name FROM evt_branches WHERE id = ?", (branch_id,)
        ).fetchone()
        if not branch:
            raise HTTPException(404, "지점을 찾을 수 없습니다.")
        branch_name = branch["name"]

        # ── 기간 결정 ───────────────────────────────────────────────
        if period_id is not None:
            period = conn.execute(
                "SELECT id, label, year, start_month, end_month FROM evt_periods WHERE id = ?",
                (period_id,)
            ).fetchone()
            if not period:
                raise HTTPException(404, "기간을 찾을 수 없습니다.")
        else:
            # 현재 기간 = 해당 지점에서 가장 최신 period
            period = conn.execute("""
                SELECT ep.id, ep.label, ep.year, ep.start_month, ep.end_month
                FROM evt_periods ep
                JOIN evt_items ei ON ei.event_period_id = ep.id
                WHERE ei.branch_id = ?
                ORDER BY ep.year DESC, ep.start_month DESC
                LIMIT 1
            """, (branch_id,)).fetchone()
            if not period:
                period = conn.execute(
                    "SELECT id, label, year, start_month, end_month FROM evt_periods ORDER BY year DESC, start_month DESC LIMIT 1"
                ).fetchone()

        period_dict = dict(period) if period else None
        resolved_period_id = period_dict["id"] if period_dict else None

        # ── 보유장비 조회 (기간 무관) ───────────────────────────────
        equips = conn.execute("""
            SELECT e.id, e.name, e.quantity, e.device_info_id,
                   e.category_id,
                   c.name as category_name,
                   d.name as device_info_name
            FROM equipment e
            LEFT JOIN branches b ON e.branch_id = b.id
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN device_info d ON e.device_info_id = d.id
            WHERE b.name = ?
            ORDER BY e.category_id, e.device_info_id, e.id
        """, (branch_name,)).fetchall()

        # ── 이벤트 조회 (선택 기간) ─────────────────────────────────
        if resolved_period_id is not None:
            events = conn.execute("""
                SELECT ei.id, ei.raw_event_name, ei.display_name,
                       ei.event_price, ei.category_id
                FROM evt_items ei
                WHERE ei.branch_id = ? AND ei.event_period_id = ?
                ORDER BY ei.category_id, ei.event_price
            """, (branch_id, resolved_period_id)).fetchall()
        else:
            events = []

        # ── 민원 (활성) ─────────────────────────────────────────────
        complaints_active = conn.execute(
            "SELECT COUNT(*) FROM complaints WHERE branch_id = ? AND status NOT IN ('closed', 'resolved')",
            (branch_id,)
        ).fetchone()[0]

        # ── 카테고리 목록 ─────────────────────────────────────────
        cats = conn.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()

        # ── 이벤트를 장비 카테고리 기준으로 재그룹 ─────────────────
        # evt_categories → equipment categories 역매핑
        evt_to_equip: dict[int, int] = {}
        for equip_cid, evt_cids in EQUIP_CAT_TO_EVT_CATS.items():
            for ecid in evt_cids:
                evt_to_equip[ecid] = equip_cid
        # 단독이벤트(1)는 기타(7)에 할당
        evt_to_equip[1] = 7

        # 장비 카테고리 → 이벤트 목록
        cat_events: dict[int, list] = defaultdict(list)
        for ev in events:
            ev = dict(ev)
            equip_cid = evt_to_equip.get(ev["category_id"], 7)  # 미매핑 → 기타
            cat_events[equip_cid].append(ev)

        # 장비 카테고리 → 장비 그룹
        cat_equips: dict[int, list] = defaultdict(list)
        for eq in equips:
            eq = dict(eq)
            cat_equips[eq["category_id"]].append(eq)

        # ── 카테고리별 집계 ──────────────────────────────────────
        categories_result = []
        for cat in cats:
            cid = cat["id"]
            cname = cat["name"]
            color = CATEGORY_COLORS.get(cid, "#94a3b8")

            # 보유장비 그룹화 (device_info_id 기준)
            eq_list = cat_equips.get(cid, [])
            di_groups: dict = defaultdict(list)
            for eq in eq_list:
                key = eq["device_info_id"]  # None 가능 (미연결)
                di_groups[key].append(eq)

            equipment_groups = []
            for did, rows in di_groups.items():
                total_qty = sum(r.get("quantity") or 1 for r in rows)
                # 같은 device_info_id가 2개 이상이고 이름이 다르면 통합 가능
                names = [r["name"] for r in rows]
                can_merge = len(rows) > 1 and len(set(names)) > 1
                equipment_groups.append({
                    "device_info_id": did,
                    "device_info_name": rows[0]["device_info_name"] if did else None,
                    "total_qty": total_qty,
                    "rows": [{"id": r["id"], "name": r["name"], "quantity": r.get("quantity") or 1} for r in rows],
                    "can_merge": can_merge,
                })

            # 정렬: device_info_name 있는 것 먼저, 미연결 마지막
            equipment_groups.sort(key=lambda g: (g["device_info_id"] is None, g["device_info_name"] or ""))

            equipment_count = len(eq_list)

            # 이벤트 집계
            ev_list = cat_events.get(cid, [])
            event_count = len(ev_list)
            prices = [e["event_price"] for e in ev_list if e.get("event_price")]
            event_avg_price = round(sum(prices) / len(prices) / 10000) * 10000 if prices else None

            # 대표 장비 (device_info_name 기준 usage 많은 순)
            di_usage: dict[str, int] = defaultdict(int)
            for eq in eq_list:
                if eq["device_info_name"]:
                    di_usage[eq["device_info_name"]] += eq.get("quantity") or 1
            top_devices = sorted(di_usage.items(), key=lambda x: -x[1])
            top_devices = [name for name, _ in top_devices[:2]]

            # 이벤트 목록 (사이드패널용, 가격 오름차순)
            ev_sorted = sorted(ev_list, key=lambda e: (e.get("event_price") or 0))

            categories_result.append({
                "id": cid,
                "name": cname,
                "color": color,
                "equipment_count": equipment_count,
                "equipment_groups": equipment_groups,
                "event_count": event_count,
                "event_avg_price": event_avg_price,
                "top_devices": top_devices,
                "events": [
                    {
                        "id": e["id"],
                        "display_name": e["display_name"] or e["raw_event_name"],
                        "raw_event_name": e["raw_event_name"],
                        "event_price": e["event_price"],
                    }
                    for e in ev_sorted
                ],
            })

        return {
            "branch": {"id": branch_id, "name": branch_name},
            "period": period_dict,
            "summary": {
                "equipment_total": len(equips),
                "events_total": len(events),
                "complaints_active": complaints_active,
            },
            "categories": categories_result,
        }
    finally:
        conn.close()


@router.get("/{branch_id}")
async def get_branch_info(branch_id: int, user: Annotated[dict, Depends(get_current_user)]):
    """지점별 통합 정보 (보유장비 + 이벤트 + 민원)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 지점 기본 정보
        branch = conn.execute("SELECT id, name FROM evt_branches WHERE id = ?", (branch_id,)).fetchone()
        if not branch:
            raise HTTPException(404, "지점을 찾을 수 없습니다.")
        branch_name = branch["name"]

        result = {
            "branch_id": branch_id,
            "branch_name": branch_name,
            "equipment": [],
            "events": [],
            "complaints": [],
        }

        # 1. 보유장비 (equipment + branches 테이블)
        equips = conn.execute("""
            SELECT e.id, e.name, e.quantity, e.photo_status, e.note,
                   c.name as category
            FROM equipment e
            LEFT JOIN branches b ON e.branch_id = b.id
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE b.name = ?
            ORDER BY c.name, e.name
        """, (branch_name,)).fetchall()
        result["equipment"] = [dict(r) for r in equips]

        # 2. 이벤트 (evt_items + 관련 테이블)
        events = conn.execute("""
            SELECT ei.id, ei.raw_event_name, ei.display_name,
                   ei.event_price, ei.regular_price, ei.is_package,
                   ec.name as category,
                   ep.year, ep.start_month, ep.end_month
            FROM evt_items ei
            LEFT JOIN evt_categories ec ON ei.category_id = ec.id
            LEFT JOIN evt_periods ep ON ei.event_period_id = ep.id
            WHERE ei.branch_id = ?
            ORDER BY ec.name, ei.display_name
        """, (branch_id,)).fetchall()
        result["events"] = [dict(r) for r in events]

        # 3. 민원
        complaints = conn.execute("""
            SELECT id, title, status, severity, category,
                   reported_by, assigned_to, created_at
            FROM complaints
            WHERE branch_id = ?
            ORDER BY created_at DESC
            LIMIT 20
        """, (branch_id,)).fetchall()
        result["complaints"] = [dict(r) for r in complaints]

        # 4. 요약 통계
        result["summary"] = {
            "equipment_count": len(result["equipment"]),
            "equipment_with_photo": sum(1 for e in result["equipment"] if e.get("photo_status") in ("있음", "O", "1", 1)),
            "event_count": len(result["events"]),
            "complaint_total": len(result["complaints"]),
            "complaint_open": sum(1 for c in result["complaints"] if c["status"] not in ("closed",)),
        }

        return result
    finally:
        conn.close()
