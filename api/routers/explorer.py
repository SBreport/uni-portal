"""Explorer 라우터 — 통합 탐색 API (6개 엔드포인트).

키워드→논문→블로그→시술→장비→지점→이벤트 연결 탐색.
FK 기반 조인으로 완전한 연결 데이터 반환.
"""

import json
from datetime import date as date_mod
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query

from api.deps import get_current_user
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter()


# ──────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────

def _get_current_period_id(conn) -> Optional[int]:
    """is_current=1인 이벤트 기간 ID 반환."""
    row = conn.execute("""
        SELECT id FROM evt_periods
        WHERE is_current = 1
        ORDER BY year DESC, start_month DESC
        LIMIT 1
    """).fetchone()
    return row["id"] if row else None


def _get_current_cafe_period_id(conn) -> Optional[int]:
    """is_current=1인 카페 기간 ID 반환."""
    row = conn.execute("""
        SELECT id FROM cafe_periods
        WHERE is_current = 1
        ORDER BY year DESC, month DESC
        LIMIT 1
    """).fetchone()
    return row["id"] if row else None


# ──────────────────────────────────────────────
# 1. 지점 기준 탐색
# ──────────────────────────────────────────────

@router.get("/by-branch")
async def explore_by_branch(
    user: Annotated[dict, Depends(get_current_user)],
    branch_id: int = Query(..., description="evt_branches.id"),
):
    """지점 ID 기준으로 장비·이벤트·순위·블로그·카페·민원 통합 조회."""
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
            return {
                "branch": None,
                "equipment": [],
                "events_by_category": {},
                "recent_blogs": [],
                "cafe_summary": {"total": 0, "published": 0, "pending": 0},
                "place_keywords": [],
                "webpage_keywords": [],
                "complaints_open": 0,
            }

        branch_dict = dict(branch)

        # ── 장비 목록 (device_info FK JOIN) ──
        equipment_rows = conn.execute("""
            SELECT COALESCE(di.name, e.name) AS name, e.quantity,
                   di.id   AS device_info_id,
                   di.category AS device_category,
                   di.summary  AS device_summary,
                   COALESCE(di.device_type, 'equipment') AS device_type
            FROM equipment e
            LEFT JOIN device_info di ON e.device_info_id = di.id
            WHERE e.evt_branch_id = ?
            ORDER BY di.category, e.name
        """, (branch_id,)).fetchall()
        equipment_list = [dict(r) for r in equipment_rows]

        # ── 현재 기간 이벤트 — 카테고리별 그룹 ──
        events_by_category: dict[str, list] = {}
        period_id = _get_current_period_id(conn)
        if period_id:
            evt_rows = conn.execute("""
                SELECT ec.display_name AS category,
                       ei.display_name, ei.event_price,
                       ei.regular_price, ei.discount_rate
                FROM evt_items ei
                JOIN evt_categories ec ON ei.category_id = ec.id
                WHERE ei.branch_id = ? AND ei.event_period_id = ? AND ei.is_active = 1
                ORDER BY ec.sort_order, ei.row_order
            """, (branch_id, period_id)).fetchall()
            for r in evt_rows:
                cat = r["category"] or "기타"
                events_by_category.setdefault(cat, []).append({
                    "display_name": r["display_name"],
                    "event_price": r["event_price"],
                    "regular_price": r["regular_price"],
                    "discount_rate": r["discount_rate"],
                })

        # ── 블로그 전체 건수 (브랜드/최적 분리) + 최근 15건 ──
        blog_counts = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN blog_channel = 'br' THEN 1 ELSE 0 END) AS brand_count,
                SUM(CASE WHEN blog_channel = 'opt' THEN 1 ELSE 0 END) AS optimal_count
            FROM blog_posts
            WHERE evt_branch_id = ?
        """, (branch_id,)).fetchone()
        blog_summary = {
            "total": blog_counts["total"] or 0,
            "brand_count": blog_counts["brand_count"] or 0,
            "optimal_count": blog_counts["optimal_count"] or 0,
        }

        blog_rows = conn.execute("""
            SELECT id, COALESCE(clean_title, scraped_title, title, keyword) AS title,
                   keyword, published_at, author,
                   blog_channel, post_type, published_url
            FROM blog_posts
            WHERE evt_branch_id = ?
            ORDER BY published_at DESC
            LIMIT 15
        """, (branch_id,)).fetchall()
        recent_blogs = [dict(r) for r in blog_rows]

        # ── 카페 현황 (cafe_branch_periods — 현재 기간) ──
        cafe_summary = {"total": 0, "published": 0, "pending": 0}
        cafe_period_id = _get_current_cafe_period_id(conn)
        if cafe_period_id:
            cbp = conn.execute("""
                SELECT id FROM cafe_branch_periods
                WHERE cafe_period_id = ? AND branch_id = ?
                LIMIT 1
            """, (cafe_period_id, branch_id)).fetchone()
            if cbp:
                totals = conn.execute("""
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN status IN ('발행완료','완료') THEN 1 ELSE 0 END) AS published,
                        SUM(CASE WHEN status NOT IN ('발행완료','완료') THEN 1 ELSE 0 END) AS pending
                    FROM cafe_articles
                    WHERE branch_period_id = ?
                """, (cbp["id"],)).fetchone()
                if totals:
                    cafe_summary = {
                        "total": totals["total"] or 0,
                        "published": totals["published"] or 0,
                        "pending": totals["pending"] or 0,
                    }

        # ── 플레이스 키워드 최신 날짜 (evt_branch_id FK → branch_id → branch_name 폴백) ──
        place_keywords: list[dict] = []

        def _fetch_place_keywords(conn, where_col: str, where_val, top5_col: str) -> tuple[list[dict], str | None]:
            """주어진 컬럼·값으로 place_daily 최신 날짜 키워드 조회 + last_top5_date 첨부.
            Returns (keywords, latest_date)."""
            latest = conn.execute(
                f"SELECT MAX(date) AS latest_date FROM place_daily WHERE {where_col} = ?",
                (where_val,)
            ).fetchone()
            if not (latest and latest["latest_date"]):
                return [], None
            pk_rows = conn.execute(
                f"""SELECT keyword, rank, is_exposed
                    FROM place_daily
                    WHERE {where_col} = ? AND date = ?
                    ORDER BY is_exposed DESC, rank ASC""",
                (where_val, latest["latest_date"])
            ).fetchall()
            result = []
            for r in pk_rows:
                d = dict(r)
                if not d["rank"] or d["rank"] > 5:
                    last_top5 = conn.execute(
                        f"""SELECT MAX(date) AS d FROM place_daily
                            WHERE {top5_col} = ? AND keyword = ? AND rank > 0 AND rank <= 5""",
                        (where_val, d["keyword"])
                    ).fetchone()
                    d["last_top5_date"] = last_top5["d"] if last_top5 else None
                else:
                    d["last_top5_date"] = None
                result.append(d)
            return result, latest["latest_date"]

        # 1차: evt_branch_id
        place_keywords, place_latest_date = _fetch_place_keywords(conn, "evt_branch_id", branch_id, "evt_branch_id")
        # 2차 폴백: branch_id
        if not place_keywords:
            place_keywords, place_latest_date = _fetch_place_keywords(conn, "branch_id", branch_id, "branch_id")
        # 3차 폴백: branch_name LIKE short_name
        if not place_keywords:
            short = branch_dict.get("short_name") or branch_dict["name"].replace("점", "")
            like_pat = f"%{short}%"
            place_latest_fb = conn.execute("""
                SELECT MAX(date) AS latest_date FROM place_daily
                WHERE branch_name LIKE ?
            """, (like_pat,)).fetchone()
            if place_latest_fb and place_latest_fb["latest_date"]:
                place_latest_date = place_latest_fb["latest_date"]
                pk_rows = conn.execute("""
                    SELECT keyword, rank, is_exposed
                    FROM place_daily
                    WHERE branch_name LIKE ? AND date = ?
                    ORDER BY is_exposed DESC, rank ASC
                """, (like_pat, place_latest_date)).fetchall()
                for r in pk_rows:
                    d = dict(r)
                    if not d["rank"] or d["rank"] > 5:
                        last_top5 = conn.execute("""
                            SELECT MAX(date) AS d FROM place_daily
                            WHERE branch_name LIKE ? AND keyword = ? AND rank > 0 AND rank <= 5
                        """, (like_pat, d["keyword"])).fetchone()
                        d["last_top5_date"] = last_top5["d"] if last_top5 else None
                    else:
                        d["last_top5_date"] = None
                    place_keywords.append(d)

        # ── 금일 전부 미노출이면 전일 데이터로 폴백 ──
        today_str = date_mod.today().isoformat()
        place_data_date = place_latest_date
        place_not_updated = False

        if place_keywords and place_latest_date == today_str:
            all_not_exposed = all(k.get("is_exposed", 0) == 0 for k in place_keywords)
            if all_not_exposed:
                # 3단계 중 어느 경로였는지 무관하게, 전일 데이터를 branch_name LIKE로 조회
                short = branch_dict.get("short_name") or branch_dict["name"].replace("점", "")
                like_pat = f"%{short}%"
                prev_date_row = conn.execute("""
                    SELECT MAX(date) AS prev_date FROM place_daily
                    WHERE branch_name LIKE ? AND date < ?
                """, (like_pat, today_str)).fetchone()
                if prev_date_row and prev_date_row["prev_date"]:
                    prev_date = prev_date_row["prev_date"]
                    pk_rows = conn.execute("""
                        SELECT keyword, rank, is_exposed
                        FROM place_daily
                        WHERE branch_name LIKE ? AND date = ?
                        ORDER BY is_exposed DESC, rank ASC
                    """, (like_pat, prev_date)).fetchall()
                    place_keywords_prev = []
                    for r in pk_rows:
                        d = dict(r)
                        if not d["rank"] or d["rank"] > 5:
                            last_top5 = conn.execute("""
                                SELECT MAX(date) AS d FROM place_daily
                                WHERE branch_name LIKE ? AND keyword = ? AND rank > 0 AND rank <= 5
                            """, (like_pat, d["keyword"])).fetchone()
                            d["last_top5_date"] = last_top5["d"] if last_top5 else None
                        else:
                            d["last_top5_date"] = None
                        place_keywords_prev.append(d)
                    if place_keywords_prev:
                        place_keywords = place_keywords_prev
                        place_data_date = prev_date
                else:
                    place_not_updated = True

        # ── 웹페이지 키워드 최신 날짜 (evt_branch_id FK → branch_id → branch_name 폴백) ──
        webpage_keywords: list[dict] = []

        def _fetch_webpage_keywords(conn, where_col: str, where_val) -> tuple[list[dict], str | None]:
            """주어진 컬럼·값으로 webpage_daily 최신 날짜 키워드 조회.
            Returns (keywords, latest_date)."""
            latest = conn.execute(
                f"SELECT MAX(date) AS latest_date FROM webpage_daily WHERE {where_col} = ?",
                (where_val,)
            ).fetchone()
            if not (latest and latest["latest_date"]):
                return [], None
            wk_rows = conn.execute(
                f"""SELECT keyword, rank, is_exposed
                    FROM webpage_daily
                    WHERE {where_col} = ? AND date = ?
                    ORDER BY is_exposed DESC, rank ASC""",
                (where_val, latest["latest_date"])
            ).fetchall()
            return [dict(r) for r in wk_rows], latest["latest_date"]

        # 1차: evt_branch_id
        webpage_keywords, webpage_latest_date = _fetch_webpage_keywords(conn, "evt_branch_id", branch_id)
        # 2차 폴백: branch_id
        if not webpage_keywords:
            webpage_keywords, webpage_latest_date = _fetch_webpage_keywords(conn, "branch_id", branch_id)
        # 3차 폴백: branch_name LIKE short_name
        if not webpage_keywords:
            short = branch_dict.get("short_name") or branch_dict["name"].replace("점", "")
            like_pat = f"%{short}%"
            web_latest_fb = conn.execute("""
                SELECT MAX(date) AS latest_date FROM webpage_daily
                WHERE branch_name LIKE ?
            """, (like_pat,)).fetchone()
            if web_latest_fb and web_latest_fb["latest_date"]:
                webpage_latest_date = web_latest_fb["latest_date"]
                wk_rows = conn.execute("""
                    SELECT keyword, rank, is_exposed
                    FROM webpage_daily
                    WHERE branch_name LIKE ? AND date = ?
                    ORDER BY is_exposed DESC, rank ASC
                """, (like_pat, webpage_latest_date)).fetchall()
                webpage_keywords = [dict(r) for r in wk_rows]

        # ── 금일 전부 미노출이면 전일 데이터로 폴백 ──
        webpage_data_date = webpage_latest_date
        webpage_not_updated = False

        if webpage_keywords and webpage_latest_date == today_str:
            all_not_exposed_web = all(k.get("is_exposed", 0) == 0 for k in webpage_keywords)
            if all_not_exposed_web:
                short = branch_dict.get("short_name") or branch_dict["name"].replace("점", "")
                like_pat = f"%{short}%"
                prev_date_row_web = conn.execute("""
                    SELECT MAX(date) AS prev_date FROM webpage_daily
                    WHERE branch_name LIKE ? AND date < ?
                """, (like_pat, today_str)).fetchone()
                if prev_date_row_web and prev_date_row_web["prev_date"]:
                    prev_date_web = prev_date_row_web["prev_date"]
                    wk_rows = conn.execute("""
                        SELECT keyword, rank, is_exposed
                        FROM webpage_daily
                        WHERE branch_name LIKE ? AND date = ?
                        ORDER BY is_exposed DESC, rank ASC
                    """, (like_pat, prev_date_web)).fetchall()
                    webpage_keywords_prev = [dict(r) for r in wk_rows]
                    if webpage_keywords_prev:
                        webpage_keywords = webpage_keywords_prev
                        webpage_data_date = prev_date_web
                else:
                    webpage_not_updated = True

        # ── 열린 민원 수 ──
        complaints_open = conn.execute("""
            SELECT COUNT(*) AS cnt FROM complaints
            WHERE branch_id = ? AND status NOT IN ('resolved', 'closed')
        """, (branch_id,)).fetchone()["cnt"]

        # ── 요약 집계 ──
        def _rank_summary(keywords: list[dict]) -> dict | None:
            if not keywords:
                return None
            total = len(keywords)
            success = sum(1 for k in keywords if k.get("is_exposed"))
            fail = total - success
            return {"success_today": success, "fail_today": fail, "total": total}

        return {
            "branch": branch_dict,
            "equipment": equipment_list,
            "events_by_category": events_by_category,
            "blog_summary": blog_summary,
            "recent_blogs": recent_blogs,
            "cafe_summary": cafe_summary,
            "place_keywords": place_keywords,
            "place_data_date": place_data_date,
            "place_not_updated": place_not_updated,
            "webpage_keywords": webpage_keywords,
            "webpage_data_date": webpage_data_date,
            "webpage_not_updated": webpage_not_updated,
            "place_rank": _rank_summary(place_keywords),
            "webpage_rank": _rank_summary(webpage_keywords),
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
        category = conn.execute("""
            SELECT id, name, display_name FROM evt_categories WHERE id = ?
        """, (category_id,)).fetchone()

        if not category:
            return {"category": None, "events_by_branch": [], "devices": [], "papers_count": 0}

        category_dict = dict(category)

        # 현재 기간 이벤트 — 지점별 그룹
        events_by_branch: list[dict] = []
        period_id = _get_current_period_id(conn)
        if period_id:
            rows = conn.execute("""
                SELECT eb.name AS branch_name,
                       ei.display_name, ei.event_price, ei.regular_price, ei.discount_rate
                FROM evt_items ei
                LEFT JOIN evt_branches eb ON ei.branch_id = eb.id
                WHERE ei.category_id = ? AND ei.event_period_id = ? AND ei.is_active = 1
                ORDER BY eb.name, ei.row_order
            """, (category_id, period_id)).fetchall()
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

        # 관련 장비 — evt_treatments.device_info_id FK
        devices = conn.execute("""
            SELECT DISTINCT di.id AS device_info_id, di.name, di.summary, di.category
            FROM evt_treatments et
            JOIN device_info di ON et.device_info_id = di.id
            WHERE et.category_id = ? AND di.id IS NOT NULL
            ORDER BY di.name
        """, (category_id,)).fetchall()
        devices_list = [dict(r) for r in devices]

        # 논문 수 — 관련 장비 통해 연결
        device_ids = [d["device_info_id"] for d in devices_list]
        papers_count = 0
        if device_ids:
            placeholders = ",".join("?" * len(device_ids))
            papers_count = conn.execute(
                f"SELECT COUNT(*) AS cnt FROM papers WHERE device_info_id IN ({placeholders})",
                device_ids,
            ).fetchone()["cnt"]

        # ── treatment_body_tags 집계 ──
        # 해당 카테고리의 evt_items ID 통해 연결
        tags_query = """
            SELECT tbt.tag_type, tbt.tag_category, tbt.tag_value, COUNT(*) AS cnt
            FROM treatment_body_tags tbt
            JOIN evt_items ei ON tbt.source = 'evt_items' AND tbt.source_id = ei.id
            WHERE ei.category_id = ?
            GROUP BY tbt.tag_type, tbt.tag_category, tbt.tag_value
            ORDER BY cnt DESC
        """
        tag_rows = conn.execute(tags_query, (category_id,)).fetchall()

        tags_body_parts: list[dict] = []
        tags_purposes: list[dict] = []
        tags_equipment: list[dict] = []
        tags_materials: list[dict] = []

        for r in tag_rows:
            item = {"value": r["tag_value"], "category": r["tag_category"], "count": r["cnt"]}
            tt = r["tag_type"]
            if tt == "body_part":
                tags_body_parts.append(item)
            elif tt == "purpose":
                tags_purposes.append(item)
            elif tt == "equipment":
                tags_equipment.append(item)
            elif tt == "material":
                tags_materials.append(item)

        return {
            "category": category_dict,
            "events_by_branch": events_by_branch,
            "devices": devices_list,
            "papers_count": papers_count,
            "tags_body_parts": tags_body_parts,
            "tags_purposes": tags_purposes,
            "tags_equipment": tags_equipment,
            "tags_materials": tags_materials,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 2b. 카테고리 요약 카드 (이벤트 건수 포함)
# ──────────────────────────────────────────────

@router.get("/category-summary")
async def category_summary(
    user: Annotated[dict, Depends(get_current_user)],
):
    """카테고리별 이벤트 건수 포함 요약 카드 (현재 기간 기준)."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        period_id = _get_current_period_id(conn)

        if period_id:
            rows = conn.execute("""
                SELECT ec.id, ec.name, ec.display_name,
                       COUNT(ei.id) AS event_count
                FROM evt_categories ec
                LEFT JOIN evt_items ei
                    ON ei.category_id = ec.id
                    AND ei.event_period_id = ?
                    AND ei.is_active = 1
                WHERE ec.is_active = 1
                GROUP BY ec.id, ec.name, ec.display_name
                ORDER BY ec.sort_order, ec.name
            """, (period_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, name, display_name, 0 AS event_count
                FROM evt_categories
                WHERE is_active = 1
                ORDER BY sort_order, name
            """).fetchall()

        return [dict(r) for r in rows]
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
        device = conn.execute("""
            SELECT id, name, category, summary, target, mechanism, aliases
            FROM device_info WHERE id = ?
        """, (device_id,)).fetchone()

        if not device:
            return {
                "device": None,
                "owning_branches": [],
                "events": [],
                "papers": [],
                "blog_posts": [],
                "keyword_summary": [],
                "related_treatments": [],
            }

        device_dict = dict(device)
        device_name = device_dict["name"]

        # aliases 파싱
        aliases_raw = device_dict.get("aliases") or "[]"
        try:
            alias_list = json.loads(aliases_raw) if aliases_raw.startswith("[") else []
        except Exception:
            alias_list = []
        search_names = [device_name] + alias_list

        # ── 보유 지점 — device_info_id FK 우선, 없으면 name LIKE 폴백 ──
        owning_branches_rows = conn.execute("""
            SELECT eb.name AS branch_name, SUM(e.quantity) AS quantity
            FROM equipment e
            JOIN evt_branches eb ON e.evt_branch_id = eb.id
            WHERE e.device_info_id = ?
            GROUP BY eb.id, eb.name
            ORDER BY eb.name
        """, (device_id,)).fetchall()
        owning_branches_list = [dict(r) for r in owning_branches_rows]

        # FK 미설정 폴백: name LIKE
        if not owning_branches_list:
            like_conditions = " OR ".join(["e.name LIKE ?"] * len(search_names))
            like_params = [f"%{n}%" for n in search_names]
            owning_branches_rows = conn.execute(f"""
                SELECT eb.name AS branch_name, SUM(e.quantity) AS quantity
                FROM equipment e
                JOIN evt_branches eb ON e.evt_branch_id = eb.id
                WHERE ({like_conditions}) AND e.device_info_id IS NULL
                GROUP BY eb.id, eb.name
                ORDER BY eb.name
            """, like_params).fetchall()
            owning_branches_list = [dict(r) for r in owning_branches_rows]

        # ── 관련 이벤트 — evt_treatments.device_info_id → components → items (현재 기간) ──
        period_id = _get_current_period_id(conn)
        events_list: list[dict] = []
        if period_id:
            events_rows = conn.execute("""
                SELECT DISTINCT eb.name AS branch_name,
                       ei.display_name, ei.event_price, ei.regular_price, ei.discount_rate
                FROM evt_treatments et
                JOIN evt_item_components eic ON eic.treatment_id = et.id
                JOIN evt_items ei ON ei.id = eic.event_item_id
                JOIN evt_branches eb ON ei.branch_id = eb.id
                WHERE et.device_info_id = ?
                  AND ei.event_period_id = ?
                  AND ei.is_active = 1
                ORDER BY eb.name, ei.display_name
                LIMIT 50
            """, (device_id, period_id)).fetchall()
            events_list = [dict(r) for r in events_rows]

        # ── 논문 — device_info_id 직접 참조 + paper_devices 다대다 ──
        papers_rows = conn.execute("""
            SELECT id, title, title_ko, journal, pub_year, one_line_summary
            FROM papers WHERE device_info_id = ?
            ORDER BY pub_year DESC
        """, (device_id,)).fetchall()
        papers_set = {r["id"]: dict(r) for r in papers_rows}

        papers_via_link = conn.execute("""
            SELECT p.id, p.title, p.title_ko, p.journal, p.pub_year, p.one_line_summary
            FROM paper_devices pd
            JOIN papers p ON p.id = pd.paper_id
            WHERE pd.device_info_id = ?
            ORDER BY p.pub_year DESC
        """, (device_id,)).fetchall()
        for r in papers_via_link:
            papers_set.setdefault(r["id"], dict(r))

        papers_list = sorted(papers_set.values(), key=lambda x: -(x.get("pub_year") or 0))

        # ── 블로그 게시글 — 장비명/aliases LIKE 검색 ──
        like_clauses = " OR ".join(
            ["(keyword LIKE ? OR title LIKE ?)"] * len(search_names)
        )
        like_params_blog: list = []
        for t in search_names:
            like_params_blog.extend([f"%{t}%", f"%{t}%"])

        blog_rows = conn.execute(f"""
            SELECT bp.id, COALESCE(bp.clean_title, bp.scraped_title, bp.title, bp.keyword) AS title,
                   bp.keyword, bp.published_at, bp.author,
                   bp.published_url, eb.name AS branch_name
            FROM blog_posts bp
            LEFT JOIN evt_branches eb ON bp.evt_branch_id = eb.id
            WHERE {like_clauses}
            ORDER BY bp.published_at DESC
            LIMIT 20
        """, like_params_blog).fetchall()
        blog_posts_list = [dict(r) for r in blog_rows]

        # ── 키워드 요약 — blog_posts의 keyword 집계 ──
        kw_rows = conn.execute(f"""
            SELECT keyword, COUNT(*) AS cnt
            FROM blog_posts
            WHERE keyword IS NOT NULL AND keyword != ''
              AND ({like_clauses})
            GROUP BY keyword
            ORDER BY cnt DESC
            LIMIT 15
        """, like_params_blog).fetchall()
        keyword_summary = [f"{r['keyword']}({r['cnt']})" for r in kw_rows]

        # ── 관련 시술 ──
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
            "keyword_summary": keyword_summary,
            "related_treatments": related_treatments_list,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 3b. 장비 전체 목록 (탐색기 장비 탭용)
# ──────────────────────────────────────────────

@router.get("/devices")
async def list_devices(
    user: Annotated[dict, Depends(get_current_user)],
):
    """device_info 전체 목록 (id, name, category)."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT id, name, category FROM device_info
            ORDER BY category, name
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 4. 논문 탐색
# ──────────────────────────────────────────────

@router.get("/papers")
async def explore_papers(
    user: Annotated[dict, Depends(get_current_user)],
    device_id: Optional[int] = Query(None, description="device_info.id 필터"),
    q: Optional[str] = Query(None, description="제목/요약 검색어"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """논문 페이지네이션 조회 — 연결된 장비 + 블로그 링크 포함."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        conditions: list[str] = []
        params: list = []

        if device_id is not None:
            conditions.append("""
                (p.device_info_id = ?
                 OR EXISTS (
                     SELECT 1 FROM paper_devices pd
                     WHERE pd.paper_id = p.id AND pd.device_info_id = ?
                 ))
            """)
            params.extend([device_id, device_id])

        if q:
            like = f"%{q}%"
            conditions.append("""
                (p.title LIKE ? OR p.title_ko LIKE ?
                 OR p.abstract_summary LIKE ? OR p.one_line_summary LIKE ?
                 OR p.keywords LIKE ?)
            """)
            params.extend([like, like, like, like, like])

        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        total = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM papers p {where_clause}", params
        ).fetchone()["cnt"]

        offset = (page - 1) * per_page
        rows = conn.execute(f"""
            SELECT p.id, p.title, p.title_ko, p.authors, p.journal, p.pub_year,
                   p.abstract_summary, p.key_findings, p.one_line_summary, p.source_url,
                   p.device_info_id
            FROM papers p
            {where_clause}
            ORDER BY p.pub_year DESC, p.id DESC
            LIMIT ? OFFSET ?
        """, params + [per_page, offset]).fetchall()

        items = []
        for r in rows:
            paper = dict(r)

            # 연결 장비 정보
            di_id = paper.pop("device_info_id", None)
            device_info = None
            if di_id:
                di_row = conn.execute(
                    "SELECT id, name, category FROM device_info WHERE id = ?",
                    (di_id,)
                ).fetchone()
                if di_row:
                    device_info = dict(di_row)
            # paper_devices 다대다도 확인
            if not device_info:
                pd_row = conn.execute("""
                    SELECT di.id, di.name, di.category
                    FROM paper_devices pd
                    JOIN device_info di ON di.id = pd.device_info_id
                    WHERE pd.paper_id = ?
                    LIMIT 1
                """, (paper["id"],)).fetchone()
                if pd_row:
                    device_info = dict(pd_row)
            paper["device"] = device_info

            # 연결 블로그 링크
            blog_links_rows = conn.execute("""
                SELECT pbl.blog_post_id AS blog_id,
                       COALESCE(bp.clean_title, bp.scraped_title, bp.title, bp.keyword) AS title,
                       bp.keyword,
                       eb.name AS branch_name
                FROM paper_blog_links pbl
                LEFT JOIN blog_posts bp ON bp.id = pbl.blog_post_id
                LEFT JOIN evt_branches eb ON bp.evt_branch_id = eb.id
                WHERE pbl.paper_id = ?
                LIMIT 10
            """, (paper["id"],)).fetchall()
            paper["blog_links"] = [dict(bl) for bl in blog_links_rows]

            items.append(paper)

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "items": items,
        }
    finally:
        conn.close()


# ──────────────────────────────────────────────
# 5. 유니버설 검색
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

        branches = conn.execute("""
            SELECT id, name FROM evt_branches
            WHERE name LIKE ? OR short_name LIKE ?
            LIMIT 10
        """, (like, like)).fetchall()

        devices = conn.execute("""
            SELECT id, name, category FROM device_info
            WHERE name LIKE ? OR aliases LIKE ? OR summary LIKE ?
            LIMIT 10
        """, (like, like, like)).fetchall()

        events = conn.execute("""
            SELECT ei.id, ei.display_name, eb.name AS branch_name, ei.event_price
            FROM evt_items ei
            LEFT JOIN evt_branches eb ON ei.branch_id = eb.id
            WHERE ei.display_name LIKE ? OR ei.raw_event_name LIKE ?
            ORDER BY ei.id DESC
            LIMIT 10
        """, (like, like)).fetchall()

        treatments = conn.execute("""
            SELECT id, name, item_type, category_id FROM evt_treatments
            WHERE name LIKE ? OR brand LIKE ?
            LIMIT 10
        """, (like, like)).fetchall()

        papers = conn.execute("""
            SELECT id, title, title_ko FROM papers
            WHERE title LIKE ? OR title_ko LIKE ? OR keywords LIKE ?
            ORDER BY pub_year DESC
            LIMIT 10
        """, (like, like, like)).fetchall()

        blog_posts = conn.execute("""
            SELECT id, COALESCE(clean_title, scraped_title, title, keyword) AS title, keyword FROM blog_posts
            WHERE (clean_title LIKE ? OR title LIKE ? OR keyword LIKE ?)
            ORDER BY published_at DESC
            LIMIT 10
        """, (like, like, like)).fetchall()

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
