"""블로그 게시글(blog_posts) 쿼리 모듈.

equipment.db의 blog_posts / blog_accounts / blog_sync_log 테이블 조회.
(blog/db.py의 blog_articles와는 별개 — 그쪽은 카페 원고용 blog.db)
"""

import re as _re

from shared.db import get_conn, EQUIPMENT_DB


def _conn():
    return get_conn(EQUIPMENT_DB)


# ── 지점명 정규화 ──

def normalize_branch(name: str) -> str:
    """project_branch 정규화: 핵심 지점명만 추출.
    '유앤아이 창원 - 추가 운영' → '유앤아이 창원'
    """
    name = name.strip()
    if not name:
        return name
    name = _re.sub(r"\s*\(x\)\s*$", "", name)
    name = name.split(" - ")[0].strip()
    name = _re.sub(r"\s+\d+월$", "", name)
    name = _re.sub(r"\s+(막글\s*작업|리뉴얼|추가\s*운영|작업|마감|연장|재계약|신규)$", "", name)
    name = _re.sub(r"[ㄱ-ㅎㅏ-ㅣ]+$", "", name)
    name = _re.sub(r"점$", "", name)
    return name.strip()


def merge_branches(rows) -> list:
    """정규화된 지점명으로 재그룹핑."""
    merged: dict[str, int] = {}
    for r in rows:
        key = normalize_branch(r["project_branch"])
        if not key:
            continue
        merged[key] = merged.get(key, 0) + r["cnt"]
    result = [{"branch_name": k, "cnt": v} for k, v in merged.items()]
    result.sort(key=lambda x: x["cnt"], reverse=True)
    return result


# 브랜드 식별 패턴 — 향후 브랜드 추가 시 여기에
BRAND_PATTERNS = ["유앤아이", "유앤"]


# ── 브랜치 필터 WHERE 절 헬퍼 ──

def _bf_clause(branch_filter: str | None, column: str = "branch_name", prefix: str = "AND") -> str:
    if branch_filter == "uandi":
        # BRAND_PATTERNS 기준 OR 결합 퍼지 검색
        or_clause = " OR ".join(f"{column} LIKE '%{p}%'" for p in BRAND_PATTERNS)
        return f" {prefix} ({or_clause})"
    return ""


# ── 게시글 목록 ──

def list_posts(*, page: int, per_page: int, channel=None, platform=None,
               post_type=None, post_type_main=None, blog_id=None, keyword=None,
               search=None, date_from=None, date_to=None, author=None,
               branch_name=None, project_month=None, needs_review=None,
               branch_filter=None) -> dict:
    conn = _conn()
    try:
        conditions = []
        params = []

        if branch_filter == "uandi":
            or_clause = " OR ".join(f"branch_name LIKE '%{p}%'" for p in BRAND_PATTERNS)
            conditions.append(f"({or_clause})")
        if channel:
            conditions.append("blog_channel = ?")
            params.append(channel)
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        if post_type:
            conditions.append("post_type LIKE ?")
            params.append(f"%{post_type}%")
        if post_type_main:
            conditions.append("post_type_main = ?")
            params.append(post_type_main)
        if blog_id:
            conditions.append("blog_id = ?")
            params.append(blog_id)
        if keyword:
            conditions.append("keyword LIKE ?")
            params.append(f"%{keyword}%")
        if search:
            conditions.append("(title LIKE ? OR keyword LIKE ? OR tags LIKE ? OR clean_title LIKE ?)")
            params.extend([f"%{search}%"] * 4)
        if date_from:
            conditions.append("published_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("published_at <= ?")
            params.append(date_to)
        if author:
            conditions.append("(author_main = ? OR author LIKE ?)")
            params.extend([author, f"%{author}%"])
        if branch_name:
            conditions.append("(branch_name = ? OR project_branch = ? OR project_branch LIKE ?)")
            params.extend([branch_name, branch_name, f"{branch_name}%"])
        if project_month:
            conditions.append("project_month = ?")
            params.append(project_month)
        if needs_review is not None:
            conditions.append("needs_review = ?")
            params.append(needs_review)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        total = conn.execute(f"SELECT COUNT(*) FROM blog_posts {where}", params).fetchone()[0]
        offset = (page - 1) * per_page
        rows = conn.execute(
            f"""SELECT id, content_number, title, keyword, tags, post_type,
                       blog_channel, blog_id, post_number, platform,
                       published_url, author, published_at, status, project, exposure_rank,
                       branch_name, slot_number, post_type_main, post_type_sub,
                       project_month, project_branch, status_clean, clean_title,
                       author_main, author_sub, needs_review
                FROM blog_posts {where}
                ORDER BY published_at DESC, id DESC
                LIMIT ? OFFSET ?""",
            params + [per_page, offset]
        ).fetchall()

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()


# ── 게시글 상세 ──

def get_post(post_id: int) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return None

        result = dict(row)
        links = conn.execute("""
            SELECT pbl.*, p.title_ko, p.evidence_level, p.study_type
            FROM paper_blog_links pbl
            JOIN papers p ON p.id = pbl.paper_id
            WHERE pbl.blog_post_id = ?
        """, (post_id,)).fetchall()
        result["linked_papers"] = [dict(l) for l in links]
        return result
    finally:
        conn.close()


# ── 필터 옵션 ──

def get_filter_options(branch_filter: str | None = None) -> dict:
    conn = _conn()
    try:
        bf_where = _bf_clause(branch_filter, prefix="AND")
        bf_where_only = _bf_clause(branch_filter, prefix="WHERE")
        bf_pb = _bf_clause(branch_filter, column="project_branch", prefix="AND")

        channels = conn.execute(
            f"SELECT blog_channel, COUNT(*) as cnt FROM blog_posts{bf_where_only} GROUP BY blog_channel ORDER BY cnt DESC"
        ).fetchall()
        types_main = conn.execute(
            f"SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != ''{bf_where} GROUP BY post_type_main ORDER BY cnt DESC"
        ).fetchall()
        authors = conn.execute(
            f"SELECT author_main as author, COUNT(*) as cnt FROM blog_posts WHERE author_main != ''{bf_where} GROUP BY author_main ORDER BY cnt DESC"
        ).fetchall()
        accounts = conn.execute(
            f"SELECT blog_id, blog_channel, COUNT(*) as cnt FROM blog_posts WHERE blog_id != ''{bf_where} GROUP BY blog_id ORDER BY cnt DESC LIMIT 30"
        ).fetchall()
        raw_branches = conn.execute(
            f"SELECT project_branch, COUNT(*) as cnt FROM blog_posts WHERE project_branch != ''{bf_pb} GROUP BY project_branch ORDER BY cnt DESC"
        ).fetchall()
        branches = merge_branches(raw_branches)
        project_months = conn.execute(
            f"SELECT project_month, COUNT(*) as cnt FROM blog_posts WHERE project_month != ''{bf_where} GROUP BY project_month ORDER BY project_month DESC"
        ).fetchall()
        sync = conn.execute(
            "SELECT csv_modified_at, imported_at, imported_rows, skipped_rows FROM blog_sync_log ORDER BY id DESC LIMIT 1"
        ).fetchone()

        return {
            "channels": [dict(c) for c in channels],
            "post_types_main": [dict(t) for t in types_main],
            "authors": [dict(a) for a in authors],
            "accounts": [dict(a) for a in accounts],
            "branches": [dict(b) for b in branches],
            "project_months": [dict(m) for m in project_months],
            "last_sync": dict(sync) if sync else None,
        }
    finally:
        conn.close()


# ── 대시보드 ──

def get_dashboard(branch_filter: str | None = None, month: str | None = None, period: str | None = None) -> dict:
    conn = _conn()
    try:
        return _get_dashboard_impl(conn, branch_filter, month, period)
    finally:
        conn.close()


def _get_dashboard_impl(conn, branch_filter, month, period=None):
    bf = _bf_clause(branch_filter, prefix="WHERE")
    bf_and = _bf_clause(branch_filter, prefix="AND")
    bf_pb = _bf_clause(branch_filter, column="project_branch", prefix="AND")

    # period='week'이면 month 무시하고 최근 7일 필터만 적용
    use_week = period == 'week'

    total = conn.execute(f"SELECT COUNT(*) FROM blog_posts{bf}").fetchone()[0]
    by_channel = conn.execute(
        f"SELECT blog_channel, COUNT(*) as cnt FROM blog_posts{bf} GROUP BY blog_channel"
    ).fetchall()
    review_count = conn.execute(
        f"SELECT COUNT(*) FROM blog_posts WHERE needs_review = 1{bf_and}"
    ).fetchone()[0]
    by_type = conn.execute(
        f"SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != ''{bf_and} GROUP BY post_type_main ORDER BY cnt DESC"
    ).fetchall()

    if month:
        raw_branch = conn.execute(
            f"SELECT project_branch, COUNT(*) as cnt FROM blog_posts WHERE project_branch != ''{bf_pb} AND project_month = ? GROUP BY project_branch ORDER BY cnt DESC",
            (month,)
        ).fetchall()
    else:
        raw_branch = conn.execute(
            f"SELECT project_branch, COUNT(*) as cnt FROM blog_posts WHERE project_branch != ''{bf_pb} GROUP BY project_branch ORDER BY cnt DESC"
        ).fetchall()
    by_branch = merge_branches(raw_branch)

    monthly = conn.execute(f"""
        SELECT project_month as month, COUNT(*) as cnt
        FROM blog_posts WHERE project_month != ''{bf_and}
        GROUP BY project_month ORDER BY project_month DESC LIMIT 6
    """).fetchall()

    weekly = conn.execute(f"""
        SELECT strftime('%Y-W%W', published_at) as week,
               MIN(published_at) as week_start, COUNT(*) as cnt
        FROM blog_posts
        WHERE published_at != '' AND published_at >= date('now', '-42 days'){bf_and}
        GROUP BY week ORDER BY week DESC
    """).fetchall()

    if month:
        by_author = conn.execute(
            f"SELECT author_main, COUNT(*) as cnt FROM blog_posts WHERE author_main != ''{bf_and} AND project_month = ? GROUP BY author_main ORDER BY cnt DESC",
            (month,)
        ).fetchall()
    else:
        by_author = conn.execute(
            f"SELECT author_main, COUNT(*) as cnt FROM blog_posts WHERE author_main != ''{bf_and} GROUP BY author_main ORDER BY cnt DESC"
        ).fetchall()

    by_type_monthly = None
    if use_week:
        # 주간(최근 7일) 원고 종류 분포
        by_type_monthly = [dict(r) for r in conn.execute(
            f"SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != '' AND published_at >= date('now', '-7 days'){bf_and} GROUP BY post_type_main ORDER BY cnt DESC"
        ).fetchall()]
    elif month:
        by_type_monthly = [dict(r) for r in conn.execute(
            f"SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != ''{bf_and} AND project_month = ? GROUP BY post_type_main ORDER BY cnt DESC",
            (month,)
        ).fetchall()]

    this_week = conn.execute(f"""
        SELECT id, clean_title, keyword, blog_channel, post_type_main, author_main, published_at, branch_name
        FROM blog_posts WHERE published_at >= date('now', '-7 days'){bf_and}
        ORDER BY published_at DESC
    """).fetchall()

    last_week = conn.execute(f"""
        SELECT id, clean_title, keyword, blog_channel, post_type_main, author_main, published_at, branch_name
        FROM blog_posts
        WHERE published_at >= date('now', '-14 days') AND published_at < date('now', '-7 days'){bf_and}
        ORDER BY published_at DESC
    """).fetchall()

    result = {
        "total": total,
        "by_channel": {r["blog_channel"]: r["cnt"] for r in by_channel},
        "review_count": review_count,
        "by_type": [dict(r) for r in by_type],
        "by_branch": [dict(r) for r in by_branch],
        "monthly": [dict(m) for m in monthly],
        "weekly": [dict(w) for w in weekly],
        "by_author": [dict(a) for a in by_author],
        "this_week": [dict(r) for r in this_week],
        "last_week": [dict(r) for r in last_week],
    }
    if by_type_monthly is not None:
        result["by_type_monthly"] = by_type_monthly
    return result


# ── 통계 ──

def get_stats() -> dict:
    conn = _conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]
        by_channel = conn.execute(
            "SELECT blog_channel, COUNT(*) as cnt FROM blog_posts GROUP BY blog_channel"
        ).fetchall()
        by_type = conn.execute(
            "SELECT post_type_main, COUNT(*) as cnt FROM blog_posts WHERE post_type_main != '' GROUP BY post_type_main ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        paper_posts = conn.execute(
            "SELECT COUNT(*) FROM blog_posts WHERE post_type_main = '논문글'"
        ).fetchone()[0]
        monthly = conn.execute("""
            SELECT project_month as month, COUNT(*) as cnt
            FROM blog_posts WHERE project_month != ''
            GROUP BY project_month ORDER BY project_month DESC LIMIT 6
        """).fetchall()
        sync_log = conn.execute(
            "SELECT * FROM blog_sync_log ORDER BY id DESC LIMIT 5"
        ).fetchall()
        return {
            "total": total,
            "by_channel": {r["blog_channel"]: r["cnt"] for r in by_channel},
            "by_type": [dict(r) for r in by_type],
            "paper_posts": paper_posts,
            "monthly": [dict(m) for m in monthly],
            "sync_log": [dict(s) for s in sync_log],
        }
    finally:
        conn.close()


# ── 계정 목록 ──

def list_accounts(channel=None, search=None, branch_filter=None) -> list:
    conn = _conn()
    try:
        conditions = []
        params = []

        if channel:
            conditions.append("ba.channel = ?")
            params.append(channel)
        if search:
            conditions.append("(ba.blog_id LIKE ? OR ba.account_name LIKE ? OR ba.blog_nickname LIKE ? OR ba.blog_title LIKE ?)")
            params.extend([f"%{search}%"] * 4)

        bp_join = "bp.blog_id = ba.blog_id"
        having = ""
        if branch_filter == "uandi":
            bp_join += " AND bp.branch_name LIKE '%유앤%'"
            having = "HAVING COUNT(bp.id) > 0"

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        rows = conn.execute(f"""
            SELECT ba.*,
                   COUNT(bp.id) as post_count,
                   SUM(CASE WHEN bp.published_at >= date('now', '-30 days') THEN 1 ELSE 0 END) as recent_count,
                   MAX(bp.published_at) as last_published
            FROM blog_accounts ba
            LEFT JOIN blog_posts bp ON {bp_join}
            {where}
            GROUP BY ba.id
            {having}
            ORDER BY post_count DESC
        """, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_account(blog_id: str, updates: dict) -> bool:
    conn = _conn()
    try:
        existing = conn.execute("SELECT id FROM blog_accounts WHERE blog_id = ?", (blog_id,)).fetchone()
        if not existing:
            return False

        set_parts = []
        params = []
        for field, val in updates.items():
            if val is not None:
                set_parts.append(f"{field} = ?")
                params.append(val)

        if not set_parts:
            return True

        params.append(blog_id)
        conn.execute(f"UPDATE blog_accounts SET {', '.join(set_parts)} WHERE blog_id = ?", params)
        conn.commit()
        return True
    finally:
        conn.close()


# ── Notion 토큰 ──

def get_notion_token() -> str | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT value FROM app_settings WHERE key = 'notion_token'").fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def get_notion_token_status() -> dict:
    conn = _conn()
    try:
        row = conn.execute("SELECT value, updated_at FROM app_settings WHERE key = 'notion_token'").fetchone()
        if row and row["value"]:
            masked = row["value"][:8] + "..." + row["value"][-4:]
            return {"saved": True, "masked": masked, "updated_at": row["updated_at"]}
        return {"saved": False}
    finally:
        conn.close()


def save_notion_token(token: str) -> str:
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO app_settings (key, value, updated_at) VALUES ('notion_token', ?, datetime('now','localtime')) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (token,),
        )
        conn.commit()
        return token[:8] + "..." + token[-4:]
    finally:
        conn.close()


def get_last_sync_status() -> dict | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM notion_sync_log ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── HOME 대시보드 (전체 현황) ──

def get_home_dashboard() -> dict:
    conn = _conn()
    try:
        return _get_home_dashboard_impl(conn)
    finally:
        conn.close()


def _get_home_dashboard_impl(conn):
    branch_count = conn.execute("SELECT COUNT(*) FROM evt_branches WHERE is_active = 1").fetchone()[0]
    equip_total = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    equip_photo = conn.execute("SELECT COUNT(*) FROM equipment WHERE photo_status = 1").fetchone()[0]

    evt_row = conn.execute("""
        SELECT p.label, COUNT(i.id) as cnt
        FROM evt_periods p JOIN evt_items i ON i.event_period_id = p.id
        WHERE p.is_current = 1 GROUP BY p.id
    """).fetchone()
    evt_label = evt_row["label"] if evt_row else "-"
    evt_count = evt_row["cnt"] if evt_row else 0

    cafe_row = conn.execute("""
        SELECT p.label,
               COUNT(a.id) as total,
               SUM(CASE WHEN a.status = '발행완료' THEN 1 ELSE 0 END) as published,
               SUM(CASE WHEN a.status = '작성대기' THEN 1 ELSE 0 END) as pending
        FROM cafe_periods p
        JOIN cafe_branch_periods bp ON bp.cafe_period_id = p.id
        JOIN cafe_articles a ON a.branch_period_id = bp.id
        WHERE p.is_current = 1 GROUP BY p.id
    """).fetchone()
    cafe_label = cafe_row["label"] if cafe_row else "-"
    cafe_total = cafe_row["total"] if cafe_row else 0
    cafe_published = cafe_row["published"] if cafe_row else 0
    cafe_pending = cafe_row["pending"] if cafe_row else 0

    dict_total = conn.execute("SELECT COUNT(*) FROM device_info").fetchone()[0]
    dict_verified = conn.execute("SELECT COUNT(*) FROM device_info WHERE is_verified = 1").fetchone()[0]

    recent_syncs = [dict(r) for r in conn.execute(
        "SELECT sync_type, added, skipped, conflicts, synced_at, triggered_by FROM sync_log ORDER BY synced_at DESC LIMIT 5"
    ).fetchall()]

    # ── 블로그 요약 ──
    blog_total = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]
    blog_review = conn.execute(
        "SELECT COUNT(*) FROM blog_posts WHERE needs_review = 1"
    ).fetchone()[0]
    blog_weekly = [dict(r) for r in conn.execute("""
        SELECT strftime('%Y-W%W', published_at) as week,
               MIN(published_at) as week_start, COUNT(*) as cnt
        FROM blog_posts
        WHERE published_at != '' AND published_at >= date('now', '-42 days')
        GROUP BY week ORDER BY week DESC
    """).fetchall()]
    blog_this_week = conn.execute(
        "SELECT COUNT(*) FROM blog_posts WHERE published_at >= date('now', '-7 days')"
    ).fetchone()[0]

    # ── 플레이스 / 웹페이지 요약 (Google Sheets, 캐시 활용) ──
    place_summary = _fetch_place_summary()
    webpage_summary = _fetch_webpage_summary()

    return {
        "branches": branch_count,
        "equipment": {"total": equip_total, "photo_done": equip_photo},
        "events": {"label": evt_label, "count": evt_count},
        "cafe": {"label": cafe_label, "total": cafe_total, "published": cafe_published, "pending": cafe_pending},
        "dictionary": {"total": dict_total, "verified": dict_verified},
        "recent_syncs": recent_syncs,
        "blog": {
            "total": blog_total,
            "review_count": blog_review,
            "this_week": blog_this_week,
            "weekly": blog_weekly,
        },
        "place": place_summary,
        "webpage": webpage_summary,
    }


def _fetch_place_summary() -> dict:
    """플레이스 최신 월 요약 (성공/실패/미달)."""
    try:
        from place.sheets import list_months, get_ranking
        months = list_months()
        if not months:
            return {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0, "month": "-"}
        latest = months[0]
        data = get_ranking(latest)
        summary = data.get("summary", {})
        summary["month"] = latest
        return summary
    except Exception:
        return {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0, "month": "-"}


def _fetch_webpage_summary() -> dict:
    """웹페이지 최신 월 요약 (노출/미노출/미달)."""
    try:
        from webpage.sheets import list_months, get_ranking
        months = list_months()
        if not months:
            return {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0, "month": "-"}
        latest = months[0]
        data = get_ranking(latest)
        summary = data.get("summary", {})
        summary["month"] = latest
        return summary
    except Exception:
        return {"total": 0, "success_today": 0, "fail_today": 0, "midal": 0, "month": "-"}
