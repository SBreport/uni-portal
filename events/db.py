"""이벤트 데이터 SQLite 읽기/쓰기 모듈.

uni-events/ingestion/db_writer.py의 PostgreSQL 로직을
SQLite(equipment.db)로 변환한 버전.
"""

import json
import sqlite3
import os
from datetime import datetime

from events.parser import ParsedEvent
from shared.db import get_conn, EQUIPMENT_DB


def _get_conn():
    return get_conn(EQUIPMENT_DB)


# ============================================================
# 쓰기 함수 (수집 파이프라인용)
# ============================================================

def ensure_period(conn, year: int, start_month: int, end_month: int, label: str, source_url: str = "") -> int:
    """이벤트 기간을 생성하거나 기존 ID를 반환."""
    c = conn.cursor()
    starts_at = f"{year}-{start_month:02d}-01"
    ends_at = f"{year}-{end_month:02d}-28"  # 간소화: 월말 대신 28일

    c.execute(
        "SELECT id FROM evt_periods WHERE year = ? AND start_month = ?",
        (year, start_month),
    )
    row = c.fetchone()

    if row:
        period_id = row[0]
        c.execute(
            "UPDATE evt_periods SET source_url = ?, is_current = 1 WHERE id = ?",
            (source_url, period_id),
        )
    else:
        c.execute(
            """INSERT INTO evt_periods (year, start_month, end_month, label, source_url, starts_at, ends_at, is_current)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (year, start_month, end_month, label, source_url, starts_at, ends_at),
        )
        period_id = c.lastrowid

    # 다른 기간의 is_current를 0으로
    c.execute("UPDATE evt_periods SET is_current = 0 WHERE id != ?", (period_id,))
    conn.commit()
    return period_id


def get_evt_branch_id(conn, query: str) -> int | None:
    """지점명으로 branch_id 조회. short_name → name → 부분매칭 순서로 검색."""
    import re
    c = conn.cursor()
    q = query.strip()
    q_no_suffix = re.sub(r"점$", "", q)  # "홍대점" → "홍대"

    # 1. short_name 정확 매칭
    c.execute("SELECT id FROM evt_branches WHERE short_name = ?", (q,))
    row = c.fetchone()
    if row:
        return row[0]

    # 2. "점" 제거 후 short_name 매칭
    if q != q_no_suffix:
        c.execute("SELECT id FROM evt_branches WHERE short_name = ?", (q_no_suffix,))
        row = c.fetchone()
        if row:
            return row[0]

    # 3. name 정확 매칭
    c.execute("SELECT id FROM evt_branches WHERE name = ?", (q,))
    row = c.fetchone()
    if row:
        return row[0]

    # 4. 의도적 퍼지 검색 — raw 파싱 텍스트("홍대점" 등) 폴백용.
    #    정제된 branch_name 해석에는 shared.branch_resolver.resolve_evt_branch_id 사용.
    c.execute("SELECT id FROM evt_branches WHERE name LIKE ? OR short_name LIKE ?",
              (f"%{q_no_suffix}%", f"%{q_no_suffix}%"))
    row = c.fetchone()
    if row:
        return row[0]

    return None


def get_evt_category_id(conn, standard_name: str) -> int:
    """표준 카테고리명으로 category_id 조회. 없으면 '기타' 반환."""
    c = conn.cursor()
    c.execute("SELECT id FROM evt_categories WHERE name = ?", (standard_name,))
    row = c.fetchone()
    if row:
        return row[0]
    c.execute("SELECT id FROM evt_categories WHERE name = '기타'")
    row = c.fetchone()
    return row[0] if row else 1


def resolve_category_by_alias(conn, raw_category: str) -> int | None:
    """카테고리 별명 테이블에서 매핑을 검색."""
    c = conn.cursor()
    c.execute(
        """SELECT ec.id FROM evt_category_aliases eca
           JOIN evt_categories ec ON ec.id = eca.category_id
           WHERE eca.alias = ? LIMIT 1""",
        (raw_category,),
    )
    row = c.fetchone()
    return row[0] if row else None


def get_or_create_treatment(conn, name: str, brand: str | None = None) -> int:
    """시술 마스터에서 ID 조회 또는 신규 생성."""
    c = conn.cursor()
    if brand:
        c.execute(
            "SELECT id FROM evt_treatments WHERE name = ? AND brand = ? LIMIT 1",
            (name, brand),
        )
    else:
        c.execute(
            "SELECT id FROM evt_treatments WHERE name = ? AND brand IS NULL LIMIT 1",
            (name,),
        )
    row = c.fetchone()
    if row:
        return row[0]

    c.execute(
        "INSERT INTO evt_treatments (name, brand) VALUES (?, ?)",
        (name, brand),
    )
    return c.lastrowid


def insert_events(
    conn,
    events: list[ParsedEvent],
    period_id: int,
    branch_id: int,
    category_resolver,
    component_parser=None,
) -> int:
    """이벤트 목록을 DB에 일괄 삽입."""
    inserted = 0
    c = conn.cursor()

    try:
        # 기존 동일 기간+지점 데이터 삭제 (재수집 시)
        c.execute(
            "DELETE FROM evt_items WHERE event_period_id = ? AND branch_id = ?",
            (period_id, branch_id),
        )

        for ev in events:
            # 카테고리 결정: DB 별명 → JSON 매핑 → 기타
            cat_id = resolve_category_by_alias(conn, ev.raw_category)
            if cat_id is None:
                standard_cat = category_resolver(ev.raw_category)
                cat_id = get_evt_category_id(conn, standard_cat)

            c.execute(
                """INSERT INTO evt_items
                    (event_period_id, branch_id, category_id,
                     raw_event_name, raw_category, display_name,
                     session_count, is_package,
                     regular_price, event_price, discount_rate,
                     notes, row_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    period_id, branch_id, cat_id,
                    ev.raw_event_name, ev.raw_category, ev.display_name,
                    ev.session_count, 1 if ev.is_package else 0,
                    ev.regular_price, ev.event_price, ev.discount_rate,
                    ev.notes, ev.row_order,
                ),
            )
            event_item_id = c.lastrowid
            inserted += 1

            # 패키지 구성요소 저장
            if ev.is_package and ev.components and component_parser:
                for order, comp_text in enumerate(ev.components, 1):
                    parsed = component_parser.parse_component(comp_text)
                    treatment_id = get_or_create_treatment(
                        conn, parsed["treatment_name"], parsed.get("brand")
                    )
                    c.execute(
                        """INSERT INTO evt_item_components
                            (event_item_id, treatment_id, raw_component,
                             dosage, session_count, component_order)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (
                            event_item_id, treatment_id, parsed["raw"],
                            parsed.get("dosage"), parsed.get("session_count"),
                            order,
                        ),
                    )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return inserted


def create_event_item(period_id, branch_id, category_id, raw_event_name,
                      display_name="", event_price=None, regular_price=None,
                      session_count=None, is_package=0, notes=""):
    """이벤트 항목 개별 생성 (웹 CRUD용). 장비명 정제 적용."""
    from shared.db import get_conn, EQUIPMENT_DB
    from equipment.db import normalize_device_name

    # 이벤트명에 포함된 장비명 정제
    clean_name = normalize_device_name(raw_event_name)
    clean_display = normalize_device_name(display_name) if display_name else clean_name

    conn = get_conn(EQUIPMENT_DB)
    try:
        discount = None
        if regular_price and event_price and regular_price > 0:
            discount = round((1 - event_price / regular_price) * 100, 1)
        c = conn.execute(
            """INSERT INTO evt_items
                (event_period_id, branch_id, category_id,
                 raw_event_name, display_name, session_count,
                 is_package, regular_price, event_price, discount_rate, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (period_id, branch_id, category_id,
             clean_name, clean_display,
             session_count, is_package, regular_price, event_price, discount, notes),
        )
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def update_event_item(item_id, **fields):
    """이벤트 항목 수정 (웹 CRUD용)."""
    from shared.db import get_conn, EQUIPMENT_DB
    if not fields:
        return False
    conn = get_conn(EQUIPMENT_DB)
    try:
        sets = []
        params = []
        for k, v in fields.items():
            if v is not None:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(item_id)
        conn.execute(f"UPDATE evt_items SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        return True
    finally:
        conn.close()


def delete_event_item(item_id):
    """이벤트 항목 삭제 (관련 components도 함께)."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute("DELETE FROM evt_item_components WHERE event_item_id = ?", (item_id,))
        conn.execute("DELETE FROM evt_items WHERE id = ?", (item_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def create_ingestion_log(conn, period_id: int) -> int:
    """수집 로그 레코드 생성."""
    c = conn.cursor()
    c.execute(
        "INSERT INTO evt_ingestion_logs (event_period_id, status) VALUES (?, 'started')",
        (period_id,),
    )
    conn.commit()
    return c.lastrowid


def update_ingestion_log(conn, log_id: int, status: str, total_branches: int, total_items: int, error_log=None):
    """수집 로그 업데이트."""
    c = conn.cursor()
    c.execute(
        """UPDATE evt_ingestion_logs
           SET status = ?, total_branches = ?, total_items = ?,
               error_log = ?, completed_at = CURRENT_TIMESTAMP
           WHERE id = ?""",
        (status, total_branches, total_items,
         json.dumps(error_log, ensure_ascii=False) if error_log else None,
         log_id),
    )
    conn.commit()


# ============================================================
# 읽기 함수
# ============================================================

def _event_query():
    """이벤트 조회 공통 SQL."""
    return """
        SELECT
            ei.id,
            eb.name AS 지점명,
            eb.short_name,
            er.name AS 지역,
            ec.display_name AS 카테고리,
            ei.raw_event_name AS 이벤트명,
            ei.display_name AS 표시명,
            ei.regular_price AS 정상가,
            ei.event_price AS 이벤트가,
            ei.discount_rate AS 할인율,
            ei.session_count AS 회차,
            ei.is_package AS 패키지,
            ei.notes AS 비고,
            ep.label AS 기간
        FROM evt_items ei
        JOIN evt_branches eb ON ei.branch_id = eb.id
        JOIN evt_regions er ON eb.region_id = er.id
        JOIN evt_categories ec ON ei.category_id = ec.id
        JOIN evt_periods ep ON ei.event_period_id = ep.id
    """



def _query_rows(conn, sql, params=()):
    """SQL 실행 → list[dict] 반환."""
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def load_current_events() -> tuple:
    """현재 날짜 기준 격월 기간의 이벤트 데이터 로드.

    Returns:
        (list[dict], is_fallback: bool)
    """
    from datetime import datetime
    now = datetime.now()
    _bm_idx = min((now.month - 1) // 2, 5)
    _pm = {0: 1, 1: 3, 2: 5, 3: 7, 4: 9, 5: 11}
    current_start_month = _pm[_bm_idx]
    current_year = now.year

    conn = _get_conn()
    try:
        base = _event_query()
        order = " ORDER BY er.sort_order, eb.name, ec.sort_order, ei.row_order"

        # 1차: 현재 날짜 기준 격월 기간
        rows = _query_rows(conn,
            base + " WHERE ep.year = ? AND ep.start_month = ? AND ei.is_active = 1" + order,
            (current_year, current_start_month),
        )
        if rows:
            return rows, False

        # 2차: 직전 격월 기간
        prev_idx = _bm_idx - 1
        prev_year = current_year
        if prev_idx < 0:
            prev_idx = 5
            prev_year -= 1
        prev_start = _pm[prev_idx]
        rows = _query_rows(conn,
            base + " WHERE ep.year = ? AND ep.start_month = ? AND ei.is_active = 1" + order,
            (prev_year, prev_start),
        )
        if rows:
            return rows, True

        # 3차: is_current=1 최종 fallback
        rows = _query_rows(conn,
            base + " WHERE ep.is_current = 1 AND ei.is_active = 1" + order,
        )
        return rows, True
    finally:
        conn.close()


def load_evt_branches() -> list[dict]:
    """이벤트 지점 목록 (ㄱㄴㄷ 순)."""
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute("""
            SELECT eb.id, eb.name, eb.short_name, er.name AS region
            FROM evt_branches eb
            JOIN evt_regions er ON eb.region_id = er.id
            WHERE eb.is_active = 1
            ORDER BY eb.name
        """)
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def load_evt_categories() -> list[dict]:
    """이벤트 카테고리 목록."""
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, name, display_name FROM evt_categories WHERE is_active = 1 ORDER BY sort_order"
        )
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def load_evt_periods() -> list[dict]:
    """이벤트 기간 목록."""
    conn = _get_conn()
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, label, year, start_month, end_month, is_current FROM evt_periods ORDER BY year DESC, start_month DESC"
        )
        return [dict(r) for r in c.fetchall()]
    finally:
        conn.close()


def load_price_history(branch_name: str = None, event_name: str = None) -> list:
    """기간별 가격 이력 조회."""
    conn = _get_conn()
    try:
        query = """
            SELECT
                eb.name AS 지점명,
                ep.label AS 기간,
                ec.display_name AS 카테고리,
                ei.raw_event_name AS 이벤트명,
                ei.regular_price AS 정상가,
                ei.event_price AS 이벤트가,
                ei.discount_rate AS 할인율,
                ep.starts_at
            FROM evt_items ei
            JOIN evt_branches eb ON ei.branch_id = eb.id
            JOIN evt_categories ec ON ei.category_id = ec.id
            JOIN evt_periods ep ON ei.event_period_id = ep.id
            WHERE ei.is_active = 1
        """
        params = []
        if branch_name:
            query += " AND eb.name = ?"
            params.append(branch_name)
        if event_name:
            query += " AND ei.raw_event_name LIKE ?"
            params.append(f"%{event_name}%")
        query += " ORDER BY ei.raw_event_name, ep.starts_at"

        return _query_rows(conn, query, params)
    finally:
        conn.close()


def search_by_treatment(query: str, period_id: int = None) -> list:
    """시술명 분해 검색 — 패키지 내 개별 시술(evt_treatments)까지 탐색."""
    conn = _get_conn()

    period_filter = "ep.is_current = 1" if period_id is None else "ep.id = ?"
    params_base = [] if period_id is None else [period_id]

    q1 = f"""
        SELECT DISTINCT
            ei.id, eb.name AS 지점명, er.name AS 지역,
            ec.display_name AS 카테고리,
            ei.raw_event_name AS 이벤트명, ei.display_name AS 표시명,
            ei.regular_price AS 정상가, ei.event_price AS 이벤트가,
            ei.discount_rate AS 할인율, ei.session_count AS 회차,
            ei.is_package AS 패키지, ei.notes AS 비고,
            ep.label AS 기간, '이벤트명' AS 매칭유형
        FROM evt_items ei
        JOIN evt_branches eb ON ei.branch_id = eb.id
        JOIN evt_regions er ON eb.region_id = er.id
        JOIN evt_categories ec ON ei.category_id = ec.id
        JOIN evt_periods ep ON ei.event_period_id = ep.id
        WHERE {period_filter} AND ei.is_active = 1 AND ei.raw_event_name LIKE ?
    """

    q2 = f"""
        SELECT DISTINCT
            ei.id, eb.name AS 지점명, er.name AS 지역,
            ec.display_name AS 카테고리,
            ei.raw_event_name AS 이벤트명, ei.display_name AS 표시명,
            ei.regular_price AS 정상가, ei.event_price AS 이벤트가,
            ei.discount_rate AS 할인율, ei.session_count AS 회차,
            ei.is_package AS 패키지, ei.notes AS 비고,
            ep.label AS 기간, '시술구성' AS 매칭유형
        FROM evt_items ei
        JOIN evt_branches eb ON ei.branch_id = eb.id
        JOIN evt_regions er ON eb.region_id = er.id
        JOIN evt_categories ec ON ei.category_id = ec.id
        JOIN evt_periods ep ON ei.event_period_id = ep.id
        JOIN evt_item_components eic ON eic.event_item_id = ei.id
        JOIN evt_treatments et ON eic.treatment_id = et.id
        WHERE {period_filter} AND ei.is_active = 1
          AND (et.name LIKE ? OR eic.raw_component LIKE ? OR et.brand LIKE ?)
    """

    combined = f"""
        SELECT * FROM ({q1} UNION {q2})
        ORDER BY 지역, 지점명, 카테고리, 이벤트명
    """

    like_q = f"%{query}%"
    params = params_base + [like_q] + params_base + [like_q, like_q, like_q]

    try:
        return _query_rows(conn, combined, params)
    finally:
        conn.close()


def load_treatment_list() -> list:
    """등록된 시술 마스터 목록 (장비 연동 대비)."""
    conn = _get_conn()
    try:
        return _query_rows(conn, """
            SELECT
                et.id, et.name AS 시술명, et.brand AS 브랜드,
                ec.display_name AS 카테고리, COUNT(eic.id) AS 사용횟수
            FROM evt_treatments et
            LEFT JOIN evt_categories ec ON et.category_id = ec.id
            LEFT JOIN evt_item_components eic ON eic.treatment_id = et.id
            WHERE et.is_active = 1
            GROUP BY et.id, et.name, et.brand, ec.display_name
            ORDER BY COUNT(eic.id) DESC, et.name
        """)
    finally:
        conn.close()


# ============================================================
# 시술 사전 함수 (설명 관리 + 장비 연동)
# ============================================================

def load_treatment_dictionary() -> list:
    """시술 사전 전체 로드 (설명·검수 상태 포함)."""
    conn = _get_conn()
    try:
        return _query_rows(conn, """
            SELECT
                et.id, et.name AS 시술명, et.brand AS 브랜드,
                ec.display_name AS 카테고리, et.description AS 설명,
                et.is_verified AS 검수완료, COUNT(eic.id) AS 이벤트사용수
            FROM evt_treatments et
            LEFT JOIN evt_categories ec ON et.category_id = ec.id
            LEFT JOIN evt_item_components eic ON eic.treatment_id = et.id
            WHERE et.is_active = 1
            GROUP BY et.id, et.name, et.brand, ec.display_name, et.description, et.is_verified
            ORDER BY ec.sort_order, et.name
        """)
    finally:
        conn.close()


def update_treatment_info(treatment_id: int, description: str, is_verified: int) -> bool:
    """시술 설명 수정 + 검수 상태 업데이트."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute(
                "UPDATE evt_treatments SET description = ?, is_verified = ? WHERE id = ?",
                (description, is_verified, treatment_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception:
        return False


def add_treatment_entry(name: str, brand: str, category_id: int, description: str) -> bool:
    """시술 사전에 새 항목 추가."""
    try:
        conn = _get_conn()
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO evt_treatments (name, brand, category_id, description, is_verified) VALUES (?, ?, ?, ?, 0)",
                (name, brand or None, category_id, description),
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception:
        return False


def get_treatment_descriptions(names: list[str]) -> dict:
    """시술명 목록 → {이름: 설명} 딕셔너리 (장비 탭·검색 결과 연동용).

    장비명과 시술명을 텍스트 매칭하여 설명을 가져옵니다.
    """
    if not names:
        return {}
    conn = _get_conn()
    try:
        c = conn.cursor()
        result = {}
        for name in names:
            c.execute(
                "SELECT name, description FROM evt_treatments WHERE ? LIKE '%' || name || '%' AND description IS NOT NULL ORDER BY LENGTH(name) DESC LIMIT 1",
                (name,),
            )
            row = c.fetchone()
            if row:
                result[name] = {"treatment": row[0], "description": row[1]}
        return result
    finally:
        conn.close()


def load_event_summary() -> list:
    """지점×카테고리별 이벤트 요약 통계."""
    conn = _get_conn()
    try:
        return _query_rows(conn, """
            SELECT
                eb.name AS 지점명, er.name AS 지역,
                ec.display_name AS 카테고리, COUNT(*) AS 이벤트수,
                MIN(ei.event_price) AS 최저가, MAX(ei.event_price) AS 최고가,
                ROUND(AVG(ei.discount_rate), 1) AS 평균할인율
            FROM evt_items ei
            JOIN evt_branches eb ON ei.branch_id = eb.id
            JOIN evt_regions er ON eb.region_id = er.id
            JOIN evt_categories ec ON ei.category_id = ec.id
            JOIN evt_periods ep ON ei.event_period_id = ep.id
            WHERE ep.is_current = 1 AND ei.is_active = 1
            GROUP BY eb.name, er.name, ec.display_name
            ORDER BY er.sort_order, eb.name, ec.sort_order
        """)
    finally:
        conn.close()
