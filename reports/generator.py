"""보고서 생성기 — 지점별/월별 마케팅 성과 통합 집계.

노출 순서:
  1. 브랜드 블로그 (blog_channel='br')
  2. 최적 블로그 (blog_channel='opt')
  3. 카페
  4. 플레이스 상위노출
  5. 웹사이트 상위노출
  6. 민원 (있을 때만)
"""

from shared.db import get_conn, EQUIPMENT_DB
import os


def get_branch_report(branch_id: int, year: int = None, month: int = None) -> dict:
    """지점별 마케팅 보고서 (월별 필터 지원)."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        branch = conn.execute(
            "SELECT id, name FROM evt_branches WHERE id = ?", (branch_id,)
        ).fetchone()
        if not branch:
            return None
        branch_name = branch["name"]

        # 섹션별 데이터 수집 (순서대로)
        sections = []

        # 1. 브랜드 블로그
        brand_blog = _get_blog_by_channel(conn, branch_name, 'br', year, month)
        if brand_blog["total"] > 0:
            sections.append({"key": "brand_blog", "title": "브랜드 블로그", "data": brand_blog})

        # 2. 최적 블로그
        opt_blog = _get_blog_by_channel(conn, branch_name, 'opt', year, month)
        if opt_blog["total"] > 0:
            sections.append({"key": "opt_blog", "title": "최적화 블로그", "data": opt_blog})

        # 3. 카페
        cafe = _get_cafe_summary(branch_id, branch_name, year, month)
        if cafe["total"] > 0:
            sections.append({"key": "cafe", "title": "카페 마케팅", "data": cafe})

        # 4. 플레이스
        place = _get_place_summary(conn, branch_id, year, month)
        if place["total_days"] > 0:
            sections.append({"key": "place", "title": "플레이스 상위노출", "data": place})

        # 5. 웹사이트
        webpage = _get_webpage_summary(conn, branch_id, year, month)
        if webpage["total_days"] > 0:
            sections.append({"key": "webpage", "title": "웹사이트 상위노출", "data": webpage})

        # 6. 민원 (있을 때만)
        complaints = _get_complaint_summary(conn, branch_id, year, month)
        if complaints["total"] > 0:
            sections.append({"key": "complaints", "title": "민원 현황", "data": complaints})

        return {
            "branch_id": branch_id,
            "branch_name": branch_name,
            "year": year,
            "month": month,
            "sections": sections,
        }
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

            equip_count = conn.execute(
                "SELECT COUNT(*) FROM equipment WHERE branch_id = (SELECT id FROM branches WHERE name = ?)",
                (bname,)
            ).fetchone()[0]

            ev_count = conn.execute(
                "SELECT COUNT(*) FROM evt_items WHERE branch_id = ?", (bid,)
            ).fetchone()[0]

            place_exposed = conn.execute(
                "SELECT COUNT(*) FROM place_daily WHERE branch_id = ? AND is_exposed = 1",
                (bid,)
            ).fetchone()[0]

            webpage_exposed = conn.execute(
                "SELECT COUNT(*) FROM webpage_daily WHERE branch_id = ? AND is_exposed = 1",
                (bid,)
            ).fetchone()[0]

            complaint_open = conn.execute(
                "SELECT COUNT(*) FROM complaints WHERE branch_id = ? AND status NOT IN ('closed')",
                (bid,)
            ).fetchone()[0]

            summaries.append({
                "branch_id": bid,
                "branch_name": bname,
                "equipment_count": equip_count,
                "event_count": ev_count,
                "place_exposed_days": place_exposed,
                "webpage_exposed_days": webpage_exposed,
                "open_complaints": complaint_open,
            })
        return summaries
    finally:
        conn.close()


def _month_filter(year, month):
    """월별 필터 SQL 조건 생성."""
    if year and month:
        date_from = f"{year}-{month:02d}-01"
        if month == 12:
            date_to = f"{year + 1}-01-01"
        else:
            date_to = f"{year}-{month + 1:02d}-01"
        return date_from, date_to
    return None, None


def _get_blog_by_channel(conn, branch_name: str, channel: str, year=None, month=None) -> dict:
    """블로그 채널별 요약 (br=브랜드, opt=최적)."""
    sql = """
        SELECT id, title, keyword, status, published_at, blog_channel, published_url, author
        FROM blog_posts
        WHERE blog_channel = ? AND (branch_name = ? OR title LIKE ?)
    """
    params = [channel, branch_name, f"%{branch_name}%"]

    if year and month:
        date_from, date_to = _month_filter(year, month)
        sql += " AND published_at >= ? AND published_at < ?"
        params.extend([date_from, date_to])

    sql += " ORDER BY published_at DESC LIMIT 30"
    rows = conn.execute(sql, params).fetchall()

    return {
        "total": len(rows),
        "posts": [dict(r) for r in rows],
    }


def _get_place_summary(conn, branch_id: int, year=None, month=None) -> dict:
    """플레이스 노출 요약."""
    sql = "SELECT date, is_exposed, rank, keyword FROM place_daily WHERE branch_id = ?"
    params = [branch_id]

    if year and month:
        date_from, date_to = _month_filter(year, month)
        sql += " AND date >= ? AND date < ?"
        params.extend([date_from, date_to])

    sql += " ORDER BY date DESC LIMIT 31"
    rows = conn.execute(sql, params).fetchall()
    exposed = sum(1 for r in rows if r["is_exposed"])

    return {
        "total_days": len(rows),
        "exposed_days": exposed,
        "exposure_rate": round(exposed / len(rows) * 100, 1) if rows else 0,
        "recent": [dict(r) for r in rows],
    }


def _get_webpage_summary(conn, branch_id: int, year=None, month=None) -> dict:
    """웹페이지 노출 요약."""
    sql = "SELECT date, is_exposed, keyword, executor FROM webpage_daily WHERE branch_id = ?"
    params = [branch_id]

    if year and month:
        date_from, date_to = _month_filter(year, month)
        sql += " AND date >= ? AND date < ?"
        params.extend([date_from, date_to])

    sql += " ORDER BY date DESC LIMIT 31"
    rows = conn.execute(sql, params).fetchall()
    exposed = sum(1 for r in rows if r["is_exposed"])

    return {
        "total_days": len(rows),
        "exposed_days": exposed,
        "exposure_rate": round(exposed / len(rows) * 100, 1) if rows else 0,
        "recent": [dict(r) for r in rows],
    }


def _get_complaint_summary(conn, branch_id: int, year=None, month=None) -> dict:
    """민원 요약."""
    sql = "SELECT status, COUNT(*) as cnt FROM complaints WHERE branch_id = ?"
    params = [branch_id]

    if year and month:
        date_from, date_to = _month_filter(year, month)
        sql += " AND created_at >= ? AND created_at < ?"
        params.extend([date_from, date_to])

    sql += " GROUP BY status"
    rows = conn.execute(sql, params).fetchall()
    status_counts = {r["status"]: r["cnt"] for r in rows}

    recent_sql = "SELECT id, title, status, severity, created_at FROM complaints WHERE branch_id = ?"
    recent_params = [branch_id]
    if year and month:
        date_from, date_to = _month_filter(year, month)
        recent_sql += " AND created_at >= ? AND created_at < ?"
        recent_params.extend([date_from, date_to])
    recent_sql += " ORDER BY created_at DESC LIMIT 5"
    recent = conn.execute(recent_sql, recent_params).fetchall()

    return {
        "status_counts": status_counts,
        "total": sum(status_counts.values()),
        "recent": [dict(r) for r in recent],
    }


def _get_cafe_summary(branch_id: int, branch_name: str, year=None, month=None) -> dict:
    """카페 마케팅 요약 (cafe.db)."""
    try:
        cafe_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cafe.db")
        if not os.path.exists(cafe_db):
            return {"total": 0, "articles": []}

        import sqlite3
        conn = sqlite3.connect(cafe_db)
        conn.row_factory = sqlite3.Row

        sql = """
            SELECT ca.id, ca.title, ca.equipment_name, ca.status, ca.category
            FROM cafe_articles ca
            JOIN cafe_branch_periods cbp ON ca.branch_period_id = cbp.id
            JOIN cafe_periods cp ON cbp.period_id = cp.id
            WHERE cbp.branch_id = ?
        """
        params = [branch_id]

        if year and month:
            sql += " AND cp.year = ? AND cp.month = ?"
            params.extend([year, month])

        sql += " ORDER BY ca.id DESC LIMIT 20"
        rows = conn.execute(sql, params).fetchall()

        count_sql = """
            SELECT COUNT(*) FROM cafe_articles ca
            JOIN cafe_branch_periods cbp ON ca.branch_period_id = cbp.id
            JOIN cafe_periods cp ON cbp.period_id = cp.id
            WHERE cbp.branch_id = ?
        """
        count_params = [branch_id]
        if year and month:
            count_sql += " AND cp.year = ? AND cp.month = ?"
            count_params.extend([year, month])

        total = conn.execute(count_sql, count_params).fetchone()[0]
        conn.close()

        return {
            "total": total,
            "articles": [dict(r) for r in rows],
        }
    except Exception:
        return {"total": 0, "articles": []}
