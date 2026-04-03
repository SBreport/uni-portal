"""지점 정보 라우터 — 지점별 보유장비+이벤트+민원 통합 조회."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_current_user

router = APIRouter(prefix="/branch-info", tags=["Branch Info"])


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
