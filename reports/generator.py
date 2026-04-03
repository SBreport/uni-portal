"""보고서 생성기 — 지점별 마케팅 성과 통합 집계."""

from shared.db import get_conn, EQUIPMENT_DB
import os


def get_branch_report(branch_id: int) -> dict:
    """지점별 마케팅 보고서 데이터 생성."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 지점 정보
        branch = conn.execute(
            "SELECT id, name FROM evt_branches WHERE id = ?", (branch_id,)
        ).fetchone()
        if not branch:
            return None
        branch_name = branch["name"]

        report = {
            "branch_id": branch_id,
            "branch_name": branch_name,
            "equipment": _get_equipment_summary(conn, branch_name),
            "events": _get_event_summary(conn, branch_id),
            "blog": _get_blog_summary(conn, branch_name),
            "place": _get_place_summary(conn, branch_id),
            "webpage": _get_webpage_summary(conn, branch_id),
            "complaints": _get_complaint_summary(conn, branch_id),
        }

        # 카페 데이터 (cafe.db에서)
        report["cafe"] = _get_cafe_summary(branch_id, branch_name)

        return report
    finally:
        conn.close()


def get_all_branches_summary() -> list[dict]:
    """전 지점 요약 보고서."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        branches = conn.execute("SELECT id, name FROM evt_branches ORDER BY name").fetchall()
        summaries = []
        for b in branches:
            bid, bname = b["id"], b["name"]

            # 장비 수
            equip_count = conn.execute(
                "SELECT COUNT(*) FROM equipment WHERE branch_id = (SELECT id FROM branches WHERE name = ?)",
                (bname,)
            ).fetchone()[0]

            # 이벤트 수
            event_count = conn.execute(
                "SELECT COUNT(*) FROM evt_items WHERE branch_id = ?", (bid,)
            ).fetchone()[0]

            # 플레이스 최근 노출
            place_exposed = conn.execute(
                "SELECT COUNT(*) FROM place_daily WHERE branch_id = ? AND is_exposed = 1",
                (bid,)
            ).fetchone()[0]

            # 웹페이지 최근 노출
            webpage_exposed = conn.execute(
                "SELECT COUNT(*) FROM webpage_daily WHERE branch_id = ? AND is_exposed = 1",
                (bid,)
            ).fetchone()[0]

            # 민원
            complaint_open = conn.execute(
                "SELECT COUNT(*) FROM complaints WHERE branch_id = ? AND status NOT IN ('closed')",
                (bid,)
            ).fetchone()[0]

            summaries.append({
                "branch_id": bid,
                "branch_name": bname,
                "equipment_count": equip_count,
                "event_count": event_count,
                "place_exposed_days": place_exposed,
                "webpage_exposed_days": webpage_exposed,
                "open_complaints": complaint_open,
            })
        return summaries
    finally:
        conn.close()


def _get_equipment_summary(conn, branch_name: str) -> dict:
    """보유장비 요약."""
    rows = conn.execute("""
        SELECT e.name, e.quantity, e.photo_status, c.name as category
        FROM equipment e
        LEFT JOIN branches b ON e.branch_id = b.id
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE b.name = ?
        ORDER BY c.name, e.name
    """, (branch_name,)).fetchall()
    return {
        "total": len(rows),
        "with_photo": sum(1 for r in rows if r["photo_status"] in ("있음", "O", "1", 1)),
        "items": [dict(r) for r in rows[:20]],
    }


def _get_event_summary(conn, branch_id: int) -> dict:
    """이벤트 요약."""
    rows = conn.execute("""
        SELECT ei.display_name, ei.event_price, ei.regular_price,
               ec.name as category, ep.year, ep.start_month
        FROM evt_items ei
        LEFT JOIN evt_categories ec ON ei.category_id = ec.id
        LEFT JOIN evt_periods ep ON ei.event_period_id = ep.id
        WHERE ei.branch_id = ?
        ORDER BY ep.year DESC, ep.start_month DESC
        LIMIT 20
    """, (branch_id,)).fetchall()
    return {
        "total": len(rows),
        "items": [dict(r) for r in rows],
    }


def _get_blog_summary(conn, branch_name: str) -> dict:
    """블로그 요약."""
    rows = conn.execute("""
        SELECT id, title, keyword, status, published_at, blog_channel
        FROM blog_posts
        WHERE branch_name = ? OR title LIKE ?
        ORDER BY published_at DESC
        LIMIT 10
    """, (branch_name, f"%{branch_name}%")).fetchall()
    return {
        "total": len(rows),
        "posts": [dict(r) for r in rows],
    }


def _get_place_summary(conn, branch_id: int) -> dict:
    """플레이스 노출 요약."""
    rows = conn.execute("""
        SELECT date, is_exposed, rank, keyword
        FROM place_daily
        WHERE branch_id = ?
        ORDER BY date DESC
        LIMIT 30
    """, (branch_id,)).fetchall()
    exposed = sum(1 for r in rows if r["is_exposed"])
    return {
        "total_days": len(rows),
        "exposed_days": exposed,
        "exposure_rate": round(exposed / len(rows) * 100, 1) if rows else 0,
        "recent": [dict(r) for r in rows[:10]],
    }


def _get_webpage_summary(conn, branch_id: int) -> dict:
    """웹페이지 노출 요약."""
    rows = conn.execute("""
        SELECT date, is_exposed, keyword, executor
        FROM webpage_daily
        WHERE branch_id = ?
        ORDER BY date DESC
        LIMIT 30
    """, (branch_id,)).fetchall()
    exposed = sum(1 for r in rows if r["is_exposed"])
    return {
        "total_days": len(rows),
        "exposed_days": exposed,
        "exposure_rate": round(exposed / len(rows) * 100, 1) if rows else 0,
        "recent": [dict(r) for r in rows[:10]],
    }


def _get_complaint_summary(conn, branch_id: int) -> dict:
    """민원 요약."""
    rows = conn.execute("""
        SELECT status, COUNT(*) as cnt
        FROM complaints WHERE branch_id = ?
        GROUP BY status
    """, (branch_id,)).fetchall()
    status_counts = {r["status"]: r["cnt"] for r in rows}
    recent = conn.execute("""
        SELECT id, title, status, severity, created_at
        FROM complaints WHERE branch_id = ?
        ORDER BY created_at DESC LIMIT 5
    """, (branch_id,)).fetchall()
    return {
        "status_counts": status_counts,
        "total": sum(status_counts.values()),
        "recent": [dict(r) for r in recent],
    }


def _get_cafe_summary(branch_id: int, branch_name: str) -> dict:
    """카페 마케팅 요약 (cafe.db에서)."""
    try:
        cafe_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cafe.db")
        if not os.path.exists(cafe_db):
            return {"total": 0, "articles": []}

        import sqlite3
        conn = sqlite3.connect(cafe_db)
        conn.row_factory = sqlite3.Row

        # cafe_branch_periods에서 해당 지점의 branch_period 찾기
        rows = conn.execute("""
            SELECT ca.id, ca.title, ca.equipment_name, ca.status, ca.category
            FROM cafe_articles ca
            JOIN cafe_branch_periods cbp ON ca.branch_period_id = cbp.id
            WHERE cbp.branch_id = ?
            ORDER BY ca.id DESC
            LIMIT 10
        """, (branch_id,)).fetchall()

        total = conn.execute("""
            SELECT COUNT(*) FROM cafe_articles ca
            JOIN cafe_branch_periods cbp ON ca.branch_period_id = cbp.id
            WHERE cbp.branch_id = ?
        """, (branch_id,)).fetchone()[0]

        conn.close()
        return {
            "total": total,
            "articles": [dict(r) for r in rows],
        }
    except Exception:
        return {"total": 0, "articles": []}
