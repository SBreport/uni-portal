"""시술 카탈로그 크로스체크 — 장비/이벤트/논문/콘텐츠 통합 조회."""

from shared.db import get_conn, EQUIPMENT_DB


def get_cross_reference(catalog_id: int) -> dict:
    """treatment_catalog 항목 기준으로 관련 정보 통합 조회."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 1. 카탈로그 항목
        item = conn.execute("SELECT * FROM treatment_catalog WHERE id = ?", (catalog_id,)).fetchone()
        if not item:
            return None
        item = dict(item)

        result = {
            "catalog": item,
            "device_info": None,
            "equipment_branches": [],
            "events": [],
            "papers": [],
            "blog_posts": [],
        }

        # 2. device_info (장비 상세) — device_id가 있는 경우
        if item.get("device_id"):
            dev = conn.execute("SELECT * FROM device_info WHERE id = ?", (item["device_id"],)).fetchone()
            if dev:
                result["device_info"] = dict(dev)

            # 2b. 보유 지점
            equips = conn.execute("""
                SELECT e.*, b.name as branch_name
                FROM equipment e
                LEFT JOIN branches b ON e.branch_id = b.id
                WHERE e.name LIKE ? OR e.name LIKE ?
                ORDER BY b.name
            """, (f"%{item['item_name']}%", f"%{item.get('display_name', '')}%")).fetchall()
            result["equipment_branches"] = [dict(r) for r in equips]

            # 2c. 관련 논문
            papers = conn.execute("""
                SELECT p.id, p.title, p.title_ko, p.authors, p.journal, p.pub_year,
                       p.evidence_level, p.study_type, p.one_line_summary
                FROM papers p
                WHERE p.device_info_id = ?
                ORDER BY p.pub_year DESC
            """, (item["device_id"],)).fetchall()
            result["papers"] = [dict(r) for r in papers]

        # 3. 관련 이벤트 — 카테고리명 또는 item_name으로 검색
        search_terms = [item["item_name"]]
        if item.get("display_name") and item["display_name"] != item["item_name"]:
            search_terms.append(item["display_name"])

        event_sql = """
            SELECT ei.id, ei.raw_event_name, ei.display_name, ei.event_price, ei.regular_price,
                   eb.name as branch_name, ep.year, ep.start_month, ep.end_month
            FROM evt_items ei
            LEFT JOIN evt_branches eb ON ei.branch_id = eb.id
            LEFT JOIN evt_periods ep ON ei.event_period_id = ep.id
            WHERE """ + " OR ".join(["ei.raw_event_name LIKE ? OR ei.display_name LIKE ?"] * len(search_terms))
        event_params = []
        for term in search_terms:
            event_params.extend([f"%{term}%", f"%{term}%"])
        event_sql += " ORDER BY ep.year DESC, ep.start_month DESC LIMIT 20"

        events = conn.execute(event_sql, event_params).fetchall()
        result["events"] = [dict(r) for r in events]

        # 4. 블로그 게시글 — keyword 매칭
        blogs = conn.execute("""
            SELECT id, title, keyword, blog_channel, platform, published_url,
                   author, published_at, status
            FROM blog_posts
            WHERE keyword LIKE ? OR title LIKE ?
            ORDER BY published_at DESC LIMIT 10
        """, (f"%{item['item_name']}%", f"%{item['item_name']}%")).fetchall()
        result["blog_posts"] = [dict(r) for r in blogs]

        return result
    finally:
        conn.close()


def search_cross_reference(query: str) -> list[dict]:
    """검색어로 treatment_catalog + 관련 정보 간략 조회."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        items = conn.execute("""
            SELECT id, item_type, category, item_name, display_name, device_id
            FROM treatment_catalog
            WHERE is_active = 1 AND (item_name LIKE ? OR display_name LIKE ? OR category LIKE ?)
            ORDER BY category, item_name LIMIT 20
        """, (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        return [dict(r) for r in items]
    finally:
        conn.close()


def get_crossref_by_name(query: str) -> dict:
    """장비/시술명으로 직접 크로스체크 (treatment_catalog 없이도 동작).

    지점정보에서 장비명 클릭 → 여기로 연결.
    device_info, equipment, evt_items, papers, blog_posts를 직접 검색.
    """
    conn = get_conn(EQUIPMENT_DB)
    try:
        q = query.strip()
        result = {
            "query": q,
            "device_info": None,
            "equipment_branches": [],
            "events": [],
            "papers": [],
            "blog_posts": [],
            "catalog": None,
        }

        # 1. device_info 매칭
        dev = conn.execute(
            "SELECT * FROM device_info WHERE name LIKE ? OR aliases LIKE ? LIMIT 1",
            (f"%{q}%", f"%{q}%")
        ).fetchone()
        if dev:
            result["device_info"] = dict(dev)

            # 보유 지점
            equips = conn.execute("""
                SELECT e.*, b.name as branch_name
                FROM equipment e
                LEFT JOIN branches b ON e.branch_id = b.id
                WHERE e.name LIKE ?
                ORDER BY b.name
            """, (f"%{q}%",)).fetchall()
            result["equipment_branches"] = [dict(r) for r in equips]

            # 논문
            papers = conn.execute("""
                SELECT p.id, p.title, p.title_ko, p.authors, p.journal, p.pub_year,
                       p.evidence_level, p.study_type, p.one_line_summary
                FROM papers p
                WHERE p.device_info_id = ?
                ORDER BY p.pub_year DESC
            """, (dev["id"],)).fetchall()
            result["papers"] = [dict(r) for r in papers]

        # 2. 이벤트 검색
        events = conn.execute("""
            SELECT ei.id, ei.raw_event_name, ei.display_name, ei.event_price, ei.regular_price,
                   eb.name as branch_name, ep.year, ep.start_month, ep.end_month
            FROM evt_items ei
            LEFT JOIN evt_branches eb ON ei.branch_id = eb.id
            LEFT JOIN evt_periods ep ON ei.event_period_id = ep.id
            WHERE ei.raw_event_name LIKE ? OR ei.display_name LIKE ?
            ORDER BY ep.year DESC, ep.start_month DESC LIMIT 20
        """, (f"%{q}%", f"%{q}%")).fetchall()
        result["events"] = [dict(r) for r in events]

        # 3. 블로그
        blogs = conn.execute("""
            SELECT id, title, keyword, blog_channel, platform, published_url,
                   author, published_at, status
            FROM blog_posts
            WHERE keyword LIKE ? OR title LIKE ?
            ORDER BY published_at DESC LIMIT 10
        """, (f"%{q}%", f"%{q}%")).fetchall()
        result["blog_posts"] = [dict(r) for r in blogs]

        # 4. treatment_catalog에도 있으면 포함
        cat = conn.execute(
            "SELECT * FROM treatment_catalog WHERE is_active = 1 AND (item_name LIKE ? OR display_name LIKE ?) LIMIT 1",
            (f"%{q}%", f"%{q}%")
        ).fetchone()
        if cat:
            result["catalog"] = dict(cat)

        return result
    finally:
        conn.close()
