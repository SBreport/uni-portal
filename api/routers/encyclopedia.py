"""시술 백과사전 API — 목적별/부위별/장비별 조회 + 동기화 관리."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from api.deps import get_current_user, require_role

router = APIRouter(prefix="/encyclopedia", tags=["Encyclopedia"])
_admin = require_role("admin")


@router.get("/purposes")
async def list_purposes(user: dict = Depends(get_current_user)):
    """목적 카테고리 목록 + 각 목적의 시술명 수."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT tag_category, COUNT(DISTINCT source_name) as cnt
            FROM treatment_body_tags
            WHERE tag_type = 'purpose' AND tag_category != ''
            GROUP BY tag_category
            ORDER BY cnt DESC
        """).fetchall()
        return [{"name": r[0], "count": r[1]} for r in rows]
    finally:
        conn.close()


@router.get("/body-parts")
async def list_body_parts(user: dict = Depends(get_current_user)):
    """부위 목록 (대분류 → 소분류)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT tag_category as region, tag_value as part, COUNT(DISTINCT source_name) as cnt
            FROM treatment_body_tags
            WHERE tag_type = 'body_part'
            GROUP BY tag_category, tag_value
            ORDER BY cnt DESC
        """).fetchall()
        # 대분류별 그룹핑
        regions = {}
        for r in rows:
            region = r["region"]
            if region not in regions:
                regions[region] = {"region": region, "parts": [], "total": 0}
            regions[region]["parts"].append({"name": r["part"], "count": r["cnt"]})
            regions[region]["total"] += r["cnt"]
        return sorted(regions.values(), key=lambda x: x["total"], reverse=True)
    finally:
        conn.close()


@router.get("/equipment-list")
async def list_equipment(user: dict = Depends(get_current_user)):
    """장비 목록 + 보유 지점 수."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 태그에서 장비 목록
        tag_rows = conn.execute("""
            SELECT tag_value, COUNT(DISTINCT source_name) as usage_cnt
            FROM treatment_body_tags
            WHERE tag_type = 'equipment'
            GROUP BY tag_value
            ORDER BY usage_cnt DESC
        """).fetchall()

        result = []
        for r in tag_rows:
            name = r["tag_value"]
            # 보유 지점 수
            branch_cnt = conn.execute("""
                SELECT COUNT(DISTINCT branch_id) FROM equipment
                WHERE name LIKE ?
            """, (f"%{name}%",)).fetchone()[0]
            # device_info 설명
            di = conn.execute("""
                SELECT summary FROM device_info WHERE name = ? OR aliases LIKE ?
            """, (name, f"%{name}%")).fetchone()
            result.append({
                "name": name,
                "usage_count": r["usage_cnt"],
                "branch_count": branch_cnt,
                "summary": di["summary"] if di else None,
            })
        return result
    finally:
        conn.close()


@router.get("/by-purpose")
async def get_by_purpose(
    purpose: str = Query(..., description="목적 카테고리 (e.g. 탄력/리프팅, 제모)"),
    user: dict = Depends(get_current_user),
):
    """목적 → 부위별 → 장비/재료 + 지점수 + 가격범위."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 1. 이 목적에 해당하는 시술명(source_id) 목록
        purpose_items = conn.execute("""
            SELECT DISTINCT source_id, source_name
            FROM treatment_body_tags
            WHERE tag_type = 'purpose' AND tag_category = ?
        """, (purpose,)).fetchall()
        source_ids = [r["source_id"] for r in purpose_items]
        if not source_ids:
            return {"purpose": purpose, "body_parts": []}

        placeholders = ",".join("?" * len(source_ids))

        # 2. 이 시술명들의 부위 태그
        body_rows = conn.execute(f"""
            SELECT tag_value as part, tag_category as region,
                   GROUP_CONCAT(DISTINCT source_id) as source_ids
            FROM treatment_body_tags
            WHERE tag_type = 'body_part' AND source_id IN ({placeholders})
              AND source = 'evt_items'
            GROUP BY tag_value, tag_category
            ORDER BY COUNT(DISTINCT source_id) DESC
        """, source_ids).fetchall()

        body_parts = []
        for bp in body_rows:
            bp_source_ids = [int(x) for x in bp["source_ids"].split(",")]
            bp_placeholders = ",".join("?" * len(bp_source_ids))

            # 3. 이 부위+목적에 해당하는 장비/재료
            equip_rows = conn.execute(f"""
                SELECT tag_value as name, tag_type,
                       COUNT(DISTINCT source_id) as cnt
                FROM treatment_body_tags
                WHERE tag_type IN ('equipment', 'material')
                  AND source_id IN ({bp_placeholders})
                  AND source = 'evt_items'
                GROUP BY tag_value, tag_type
                ORDER BY cnt DESC
            """, bp_source_ids).fetchall()

            equipments = []
            for eq in equip_rows:
                eq_name = eq["name"]
                # 보유 지점 수
                branch_cnt = conn.execute("""
                    SELECT COUNT(DISTINCT branch_id) FROM equipment
                    WHERE name LIKE ?
                """, (f"%{eq_name}%",)).fetchone()[0]
                # device_info 설명
                di = conn.execute("""
                    SELECT summary FROM device_info
                    WHERE name = ? OR aliases LIKE ?
                """, (eq_name, f"%{eq_name}%")).fetchone()
                # 가격 범위 (이벤트에서)
                prices = conn.execute("""
                    SELECT MIN(event_price) as min_p, MAX(event_price) as max_p
                    FROM evt_items
                    WHERE raw_event_name LIKE ? AND event_price > 0
                """, (f"%{eq_name}%",)).fetchone()

                equipments.append({
                    "name": eq_name,
                    "type": "장비" if eq["tag_type"] == "equipment" else "재료",
                    "usage_count": eq["cnt"],
                    "branch_count": branch_cnt,
                    "summary": di["summary"] if di else None,
                    "price_min": prices["min_p"] if prices else None,
                    "price_max": prices["max_p"] if prices else None,
                })

            body_parts.append({
                "part": bp["part"],
                "region": bp["region"],
                "equipment": equipments,
            })

        return {"purpose": purpose, "body_parts": body_parts}
    finally:
        conn.close()


@router.get("/by-body-part")
async def get_by_body_part(
    part: str = Query(..., description="부위명 (e.g. 이마, 턱)"),
    user: dict = Depends(get_current_user),
):
    """부위 → 목적별 → 장비/재료 + 지점수 + 가격범위."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 이 부위에 해당하는 시술명
        part_items = conn.execute("""
            SELECT DISTINCT source_id FROM treatment_body_tags
            WHERE tag_type = 'body_part' AND tag_value = ? AND source = 'evt_items'
        """, (part,)).fetchall()
        source_ids = [r[0] for r in part_items]
        if not source_ids:
            return {"part": part, "purposes": []}

        placeholders = ",".join("?" * len(source_ids))

        # 목적 태그
        purpose_rows = conn.execute(f"""
            SELECT tag_category as purpose, GROUP_CONCAT(DISTINCT source_id) as source_ids
            FROM treatment_body_tags
            WHERE tag_type = 'purpose' AND source_id IN ({placeholders}) AND source = 'evt_items'
            GROUP BY tag_category
            ORDER BY COUNT(DISTINCT source_id) DESC
        """, source_ids).fetchall()

        purposes = []
        for pr in purpose_rows:
            pr_source_ids = [int(x) for x in pr["source_ids"].split(",")]
            pr_placeholders = ",".join("?" * len(pr_source_ids))

            equip_rows = conn.execute(f"""
                SELECT tag_value as name, tag_type, COUNT(DISTINCT source_id) as cnt
                FROM treatment_body_tags
                WHERE tag_type IN ('equipment', 'material')
                  AND source_id IN ({pr_placeholders}) AND source = 'evt_items'
                GROUP BY tag_value, tag_type ORDER BY cnt DESC
            """, pr_source_ids).fetchall()

            equipments = []
            for eq in equip_rows:
                eq_name = eq["name"]
                branch_cnt = conn.execute(
                    "SELECT COUNT(DISTINCT branch_id) FROM equipment WHERE name LIKE ?",
                    (f"%{eq_name}%",)
                ).fetchone()[0]
                di = conn.execute(
                    "SELECT summary FROM device_info WHERE name = ? OR aliases LIKE ?",
                    (eq_name, f"%{eq_name}%")
                ).fetchone()
                prices = conn.execute(
                    "SELECT MIN(event_price) as min_p, MAX(event_price) as max_p FROM evt_items WHERE raw_event_name LIKE ? AND event_price > 0",
                    (f"%{eq_name}%",)
                ).fetchone()
                equipments.append({
                    "name": eq_name,
                    "type": "장비" if eq["tag_type"] == "equipment" else "재료",
                    "usage_count": eq["cnt"],
                    "branch_count": branch_cnt,
                    "summary": di["summary"] if di else None,
                    "price_min": prices["min_p"] if prices else None,
                    "price_max": prices["max_p"] if prices else None,
                })

            purposes.append({
                "purpose": pr["purpose"],
                "equipment": equipments,
            })

        return {"part": part, "purposes": purposes}
    finally:
        conn.close()


@router.get("/by-equipment")
async def get_by_equipment(
    name: str = Query(..., description="장비/재료명"),
    user: dict = Depends(get_current_user),
):
    """장비 → 적용부위 + 목적 + 보유지점 + 가격범위."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 이 장비가 태깅된 시술명
        items = conn.execute("""
            SELECT DISTINCT source_id FROM treatment_body_tags
            WHERE tag_type IN ('equipment', 'material') AND tag_value = ? AND source = 'evt_items'
        """, (name,)).fetchall()
        source_ids = [r[0] for r in items]
        if not source_ids:
            return {"name": name, "body_parts": [], "purposes": [], "branches": []}

        placeholders = ",".join("?" * len(source_ids))

        # 부위
        body_rows = conn.execute(f"""
            SELECT tag_value, tag_category, COUNT(DISTINCT source_id) as cnt
            FROM treatment_body_tags
            WHERE tag_type = 'body_part' AND source_id IN ({placeholders}) AND source = 'evt_items'
            GROUP BY tag_value ORDER BY cnt DESC
        """, source_ids).fetchall()

        # 목적
        purpose_rows = conn.execute(f"""
            SELECT tag_category, COUNT(DISTINCT source_id) as cnt
            FROM treatment_body_tags
            WHERE tag_type = 'purpose' AND source_id IN ({placeholders}) AND source = 'evt_items'
            GROUP BY tag_category ORDER BY cnt DESC
        """, source_ids).fetchall()

        # device_info
        di = conn.execute(
            "SELECT * FROM device_info WHERE name = ? OR aliases LIKE ?",
            (name, f"%{name}%")
        ).fetchone()

        # 보유 지점
        branches = conn.execute("""
            SELECT e.name as equip_name, b.name as branch_name
            FROM equipment e
            LEFT JOIN evt_branches b ON e.branch_id = b.id
            WHERE e.name LIKE ?
            ORDER BY b.name
        """, (f"%{name}%",)).fetchall()

        # 가격 범위
        prices = conn.execute(
            "SELECT MIN(event_price) as min_p, MAX(event_price) as max_p FROM evt_items WHERE raw_event_name LIKE ? AND event_price > 0",
            (f"%{name}%",)
        ).fetchone()

        return {
            "name": name,
            "device_info": dict(di) if di else None,
            "body_parts": [{"part": r[0], "region": r[1], "count": r[2]} for r in body_rows],
            "purposes": [{"name": r[0], "count": r[1]} for r in purpose_rows],
            "branches": [{"equip_name": r[0], "branch_name": r[1]} for r in branches],
            "price_min": prices["min_p"] if prices else None,
            "price_max": prices["max_p"] if prices else None,
        }
    finally:
        conn.close()


# ── 백과사전 관리 (admin) ──

@router.post("/refresh")
async def refresh_encyclopedia(user=Depends(_admin)):
    """태그 재추출 + 신규/삭제 감지 + 자동 추천. 이벤트 동기화 후 호출."""
    from treatment.extract_tags import run_extraction
    from treatment.sync_diff import detect_diff_and_recommend

    extract_result = run_extraction()
    diff_result = detect_diff_and_recommend()

    return {
        "extract": extract_result,
        "diff": diff_result,
    }


@router.get("/pending")
async def get_pending(user=Depends(_admin)):
    """승인 대기 중인 항목 목록."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT * FROM encyclopedia_pending
            WHERE status = 'pending'
            ORDER BY action, created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/pending/summary")
async def get_pending_summary(user=Depends(get_current_user)):
    """승인 대기 요약 (배지 표시용)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute("""
            SELECT
                SUM(CASE WHEN action = 'new' THEN 1 ELSE 0 END) as new_cnt,
                SUM(CASE WHEN action = 'removed' THEN 1 ELSE 0 END) as removed_cnt,
                SUM(CASE WHEN action = 'recommend' THEN 1 ELSE 0 END) as recommend_cnt
            FROM encyclopedia_pending WHERE status = 'pending'
        """).fetchone()
        return {
            "new": row[0] or 0,
            "removed": row[1] or 0,
            "recommend": row[2] or 0,
            "total": (row[0] or 0) + (row[1] or 0) + (row[2] or 0),
        }
    finally:
        conn.close()


@router.post("/pending/{pending_id}/approve")
async def approve(pending_id: int, user=Depends(_admin)):
    """개별 항목 승인."""
    from treatment.sync_diff import approve_pending
    return approve_pending(pending_id)


@router.post("/pending/{pending_id}/dismiss")
async def dismiss(pending_id: int, user=Depends(_admin)):
    """개별 항목 무시."""
    from treatment.sync_diff import dismiss_pending
    return dismiss_pending(pending_id)


@router.post("/pending/approve-all")
async def approve_all(user=Depends(_admin)):
    """추천 태그 전체 일괄 승인."""
    from treatment.sync_diff import approve_all_recommended
    return approve_all_recommended()


@router.get("/untagged")
async def get_untagged(user=Depends(_admin)):
    """미분류 항목 (태그도 추천도 없는 시술명)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT DISTINCT ei.raw_event_name, ei.raw_category
            FROM evt_items ei
            WHERE ei.raw_event_name IS NOT NULL AND ei.raw_event_name != ''
              AND NOT EXISTS (
                SELECT 1 FROM treatment_body_tags t
                WHERE t.source = 'evt_items' AND t.source_name = ei.raw_event_name
              )
              AND NOT EXISTS (
                SELECT 1 FROM encyclopedia_pending p
                WHERE p.source_name = ei.raw_event_name AND p.action = 'recommend' AND p.status = 'pending'
              )
            ORDER BY ei.raw_category, ei.raw_event_name
            LIMIT 200
        """).fetchall()
        return [{"name": r[0], "category": r[1] or ""} for r in rows]
    finally:
        conn.close()
