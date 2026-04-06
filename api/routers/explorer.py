"""Explorer 라우터 — 통합 탐색 API (4개 진입점).

키워드→논문→블로그→시술→장비→지점→이벤트 연결 탐색.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query

from api.deps import get_current_user
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter()


# ──────────────────────────────────────────────
# 1. 지점 기준 탐색
# ──────────────────────────────────────────────

@router.get("/by-branch")
async def explore_by_branch(
    user: Annotated[dict, Depends(get_current_user)],
    branch_id: int = Query(..., description="evt_branches.id"),
):
    """지점 ID 기준으로 장비·이벤트·순위·블로그·민원 통합 조회."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 지점 기본 정보
        branch = conn.execute("""
            SELECT eb.id, eb.name, eb.short_name, er.name AS region_name
            FROM evt_branches eb
            LEFT JOIN evt_regions er ON eb.region_id = er.id
            WHERE eb.id = ?
        """, (branch_id,)).fetchone()

        if not branch:
            return {"branch": None, "equipment": [], "events": [],
                    "place_rank": None, "webpage_rank": None,
                    "blog_count": 0, "complaints_open": 0}

        branch_dict = dict(branch)

        # 장비 목록 (device_info JOIN)
        equipment = conn.execute("""
            SELECT e.id, e.name, c.name AS category, e.quantity,
                   e.photo_status, di.id AS device_info_id, di.name AS device_name
            FROM equipment e
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN device_info di ON e.device_info_id = di.id
            WHERE e.evt_branch_id = ?
            ORDER BY c.name, e.name
        """, (branch_id,)).fetchall()
        equipment_list = [dict(r) for r in equipment]

        # 현재 기간 이벤트 (is_current=1 또는 가장 최근 기간)
        current_period = conn.execute("""
            SELECT id FROM evt_periods
            WHERE is_current = 1
            ORDER BY year DESC, start_month DESC
            LIMIT 1
        """).fetchone()

        events = []
        if current_period:
            events_rows = conn.execute("""
                SELECT ei.id, ec.display_name AS category, ei.display_name,
                       ei.event_price, ei.regular_price, ei.discount_rate
                FROM evt_items ei
                LEFT JOIN evt_categories ec ON ei.category_id = ec.id
                WHERE ei.branch_id = ? AND ei.event_period_id = ? AND ei.is_active = 1
                ORDER BY ec.sort_order, ei.row_order
            """, (branch_id, current_period["id"])).fetchall()
            events = [dict(r) for r in events_rows]

        # 플레이스 순위 — 최신 날짜 집계
        place_rank = None
        place_latest = conn.execute("""
            SELECT MAX(date) AS latest_date FROM place_daily WHERE branch_id = ?
        """, (branch_id,)).fetchone()
        if place_latest and place_latest["latest_date"]:
            pr = conn.execute("""
                SELECT
                    SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS success_today,
                    SUM(CASE WHEN is_exposed = 0 THEN 1 ELSE 0 END) AS fail_today,
                    COUNT(*) AS total
                FROM place_daily
                WHERE branch_id = ? AND date = ?
            """, (branch_id, place_latest["latest_date"])).fetchone()
            if pr:
                place_rank = dict(pr)

        # 웹페이지 순위 — 최신 날짜 집계
        webpage_rank = None
        web_latest = conn.execute("""
            SELECT MAX(date) AS latest_date FROM webpage_daily WHERE branch_id = ?
        """, (branch_id,)).fetchone()
        if web_latest and web_latest["latest_date"]:
            wr = conn.execute("""
                SELECT
                    SUM(CASE WHEN is_exposed = 1 THEN 1 ELSE 0 END) AS success_today,
                    SUM(CASE WHEN is_exposed = 0 THEN 1 ELSE 0 END) AS fail_today,
                    COUNT(*) AS total
                FROM webpage_daily
                WHERE branch_id = ? AND date = ?
            """, (branch_id, web_latest["latest_date"])).fetchone()
            if wr:
                webpage_rank = dict(wr)

        # 블로그 게시글 수 — branch_name 기준
        blog_count = conn.execute("""
            SELECT COUNT(*) AS cnt FROM blog_posts WHERE branch_name = ?
        """, (branch_dict["name"],)).fetchone()["cnt"]

        # 열린 민원 수
        complaints_open = conn.execute("""
            SELECT COUNT(*) AS cnt FROM complaints
            WHERE branch_id = ? AND status NOT IN ('resolved', 'closed')
        """, (branch_id,)).fetchone()["cnt"]

        return {
            "branch": branch_dict,
            "equipment": equipment_list,
            "events": events,
            "place_rank": place_rank,
            "webpage_rank": webpage_rank,
            "blog_count": blog_count,
            "complaints_open": complaints_open,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 2. 카테고리 기준 탐색
# ──────────────────────────────────────────────

@router.get("/by-category")
async def explore_by_category(
    user: Annotated[dict, Depends(get_current_user)],
    category_id: int = Query(..., description="evt_categories.id"),
):
    """카테고리 ID 기준으로 시술·이벤트·장비·논문 통합 조회."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 카테고리 기본 정보
        category = conn.execute("""
            SELECT id, name, display_name FROM evt_categories WHERE id = ?
        """, (category_id,)).fetchone()

        if not category:
            return {"category": None, "events_by_branch": [], "devices": [], "papers_count": 0}

        category_dict = dict(category)

        # 현재 기간 이벤트 — 지점별로 그룹
        current_period = conn.execute("""
            SELECT id FROM evt_periods
            WHERE is_current = 1
            ORDER BY year DESC, start_month DESC
            LIMIT 1
        """).fetchone()

        events_by_branch: list[dict] = []
        if current_period:
            rows = conn.execute("""
                SELECT eb.name AS branch_name,
                       ei.display_name, ei.event_price, ei.regular_price, ei.discount_rate
                FROM evt_items ei
                LEFT JOIN evt_branches eb ON ei.branch_id = eb.id
                WHERE ei.category_id = ? AND ei.event_period_id = ? AND ei.is_active = 1
                ORDER BY eb.name, ei.row_order
            """, (category_id, current_period["id"])).fetchall()

            # branch_name 기준으로 그룹화
            branch_map: dict[str, list] = {}
            for r in rows:
                bn = r["branch_name"] or "미지정"
                branch_map.setdefault(bn, []).append({
                    "display_name": r["display_name"],
                    "event_price": r["event_price"],
                    "regular_price": r["regular_price"],
                    "discount_rate": r["discount_rate"],
                })
            events_by_branch = [
                {"branch_name": k, "items": v}
                for k, v in sorted(branch_map.items())
            ]

        # 관련 장비 — evt_treatments.device_info_id를 통해 연결
        devices = conn.execute("""
            SELECT DISTINCT di.id AS device_info_id, di.name, di.summary, di.category
            FROM evt_treatments et
            JOIN device_info di ON et.device_info_id = di.id
            WHERE et.category_id = ? AND di.id IS NOT NULL
            ORDER BY di.name
        """, (category_id,)).fetchall()
        devices_list = [dict(r) for r in devices]

        # 논문 수 — 관련 장비를 통해 간접 연결
        device_ids = [d["device_info_id"] for d in devices_list]
        papers_count = 0
        if device_ids:
            placeholders = ",".join("?" * len(device_ids))
            papers_count = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM papers WHERE device_info_id IN ({placeholders})",
                device_ids,
            ).fetchone()["cnt"]

        return {
            "category": category_dict,
            "events_by_branch": events_by_branch,
            "devices": devices_list,
            "papers_count": papers_count,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 3. 장비 기준 탐색
# ──────────────────────────────────────────────

@router.get("/by-device")
async def explore_by_device(
    user: Annotated[dict, Depends(get_current_user)],
    device_id: int = Query(..., description="device_info.id"),
):
    """장비(device_info) ID 기준으로 지점·이벤트·논문·블로그·시술 통합 조회."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 장비 기본 정보
        device = conn.execute("""
            SELECT id, name, category, summary, target, mechanism, aliases
            FROM device_info WHERE id = ?
        """, (device_id,)).fetchone()

        if not device:
            return {"device": None, "owning_branches": [], "events": [],
                    "papers": [], "blog_posts": [], "related_treatments": []}

        device_dict = dict(device)
        device_name = device_dict["name"]

        # 보유 지점 — evt_branch_id 기준 우선, fallback: 장비명 LIKE
        owning_branches = conn.execute("""
            SELECT eb.name AS branch_name, SUM(e.quantity) AS quantity
            FROM equipment e
            JOIN evt_branches eb ON e.evt_branch_id = eb.id
            WHERE e.device_info_id = ?
            GROUP BY eb.id, eb.name
            ORDER BY eb.name
        """, (device_id,)).fetchall()

        if not owning_branches:
            # fallback: 장비명 LIKE 검색
            owning_branches = conn.execute("""
                SELECT eb.name AS branch_name, SUM(e.quantity) AS quantity
                FROM equipment e
                JOIN evt_branches eb ON e.evt_branch_id = eb.id
                WHERE e.name LIKE ?
                GROUP BY eb.id, eb.name
                ORDER BY eb.name
            """, (f"%{device_name}%",)).fetchall()

        owning_branches_list = [dict(r) for r in owning_branches]

        # 관련 이벤트 — evt_treatments.device_info_id → evt_item_components → evt_items
        events = conn.execute("""
            SELECT DISTINCT eb.name AS branch_name,
                   ei.display_name, ei.event_price, ei.regular_price, ei.discount_rate
            FROM evt_treatments et
            JOIN evt_item_components eic ON eic.treatment_id = et.id
            JOIN evt_items ei ON ei.id = eic.event_item_id
            JOIN evt_branches eb ON ei.branch_id = eb.id
            WHERE et.device_info_id = ? AND ei.is_active = 1
            ORDER BY eb.name, ei.display_name
            LIMIT 50
        """, (device_id,)).fetchall()
        events_list = [dict(r) for r in events]

        # 논문 — device_info_id 직접 참조 + paper_devices 다대다 연결
        papers = conn.execute("""
            SELECT id, title, title_ko, journal, pub_year, one_line_summary
            FROM papers WHERE device_info_id = ?
            ORDER BY pub_year DESC
        """, (device_id,)).fetchall()
        papers_set = {r["id"]: dict(r) for r in papers}

        # paper_devices 다대다 연결도 포함
        papers_via_link = conn.execute("""
            SELECT p.id, p.title, p.title_ko, p.journal, p.pub_year, p.one_line_summary
            FROM paper_devices pd
            JOIN papers p ON p.id = pd.paper_id
            WHERE pd.device_info_id = ?
            ORDER BY p.pub_year DESC
        """, (device_id,)).fetchall()
        for r in papers_via_link:
            papers_set.setdefault(r["id"], dict(r))

        papers_list = sorted(papers_set.values(), key=lambda x: -(x["pub_year"] or 0))

        # 블로그 게시글 — 장비명 또는 aliases 기준 keyword/title 검색
        aliases_raw = device_dict.get("aliases") or ""
        alias_terms = [a.strip() for a in aliases_raw.split(",") if a.strip()]
        search_terms = [device_name] + alias_terms

        # LIKE 조건 동적 생성
        like_clauses = " OR ".join(
            ["(keyword LIKE ? OR title LIKE ?)"] * len(search_terms)
        )
        like_params: list = []
        for t in search_terms:
            like_params.extend([f"%{t}%", f"%{t}%"])

        blog_sql = f"""
            SELECT id, title, keyword, published_at, branch_name, author
            FROM blog_posts
            WHERE {like_clauses}
            ORDER BY published_at DESC
            LIMIT 20
        """
        blog_posts = conn.execute(blog_sql, like_params).fetchall()
        blog_posts_list = [dict(r) for r in blog_posts]

        # 관련 시술 — evt_treatments WHERE device_info_id = X
        related_treatments = conn.execute("""
            SELECT id, name, item_type
            FROM evt_treatments
            WHERE device_info_id = ? AND is_active = 1
            ORDER BY name
            LIMIT 30
        """, (device_id,)).fetchall()
        related_treatments_list = [dict(r) for r in related_treatments]

        return {
            "device": device_dict,
            "owning_branches": owning_branches_list,
            "events": events_list,
            "papers": papers_list,
            "blog_posts": blog_posts_list,
            "related_treatments": related_treatments_list,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 4. 유니버설 검색
# ──────────────────────────────────────────────

@router.get("/search")
async def explorer_search(
    user: Annotated[dict, Depends(get_current_user)],
    q: str = Query(..., min_length=1, description="검색어"),
):
    """전 도메인 통합 검색 — 도메인별 최대 10건."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        like = f"%{q}%"

        # 지점
        branches = conn.execute("""
            SELECT id, name FROM evt_branches
            WHERE name LIKE ? OR short_name LIKE ?
            LIMIT 10
        """, (like, like)).fetchall()

        # 장비 (device_info)
        devices = conn.execute("""
            SELECT id, name, category FROM device_info
            WHERE name LIKE ? OR aliases LIKE ? OR summary LIKE ?
            LIMIT 10
        """, (like, like, like)).fetchall()

        # 이벤트 상품
        events = conn.execute("""
            SELECT ei.id, ei.display_name, eb.name AS branch_name, ei.event_price
            FROM evt_items ei
            LEFT JOIN evt_branches eb ON ei.branch_id = eb.id
            WHERE ei.display_name LIKE ? OR ei.raw_event_name LIKE ?
            ORDER BY ei.id DESC
            LIMIT 10
        """, (like, like)).fetchall()

        # 시술
        treatments = conn.execute("""
            SELECT id, name, item_type FROM evt_treatments
            WHERE name LIKE ? OR brand LIKE ?
            LIMIT 10
        """, (like, like)).fetchall()

        # 논문
        papers = conn.execute("""
            SELECT id, title, title_ko FROM papers
            WHERE title LIKE ? OR title_ko LIKE ? OR keywords LIKE ?
            ORDER BY pub_year DESC
            LIMIT 10
        """, (like, like, like)).fetchall()

        # 블로그
        blog_posts = conn.execute("""
            SELECT id, title, keyword FROM blog_posts
            WHERE title LIKE ? OR keyword LIKE ?
            ORDER BY published_at DESC
            LIMIT 10
        """, (like, like)).fetchall()

        return {
            "branches": [dict(r) for r in branches],
            "devices": [dict(r) for r in devices],
            "events": [dict(r) for r in events],
            "treatments": [dict(r) for r in treatments],
            "papers": [dict(r) for r in papers],
            "blog_posts": [dict(r) for r in blog_posts],
        }
    finally:
        conn.close()
