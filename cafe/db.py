"""카페 마케팅 데이터 SQLite 읽기/쓰기 모듈.

테이블: cafe_periods, cafe_branch_periods, cafe_articles,
        cafe_comments, cafe_feedbacks, cafe_status_log, cafe_sync_log
"""

import sqlite3
import os
from datetime import datetime

import pandas as pd


DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "cafe.db")
EQUIPMENT_DB_PATH = os.path.join(DB_DIR, "equipment.db")

# 마이그레이션: equipment.db에서 cafe 테이블을 cafe.db로 복사
def _migrate_cafe_if_needed():
    """cafe.db가 없으면 equipment.db에서 cafe_* 테이블을 스키마+데이터 그대로 복사."""
    old_db = os.path.join(DB_DIR, "equipment.db")
    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        return  # 이미 존재
    if not os.path.exists(old_db):
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"ATTACH DATABASE ? AS src", (old_db,))

    cafe_tables = ['cafe_periods', 'cafe_branch_periods', 'cafe_articles',
                   'cafe_comments', 'cafe_feedbacks', 'cafe_status_log', 'cafe_sync_log']

    for tbl in cafe_tables:
        try:
            # 스키마 복사
            schema = conn.execute(
                f"SELECT sql FROM src.sqlite_master WHERE type='table' AND name=?", (tbl,)
            ).fetchone()
            if schema and schema[0]:
                conn.execute(schema[0])
                # 데이터 복사
                conn.execute(f"INSERT INTO main.{tbl} SELECT * FROM src.{tbl}")
        except Exception:
            pass

    conn.commit()
    conn.execute("DETACH DATABASE src")
    conn.close()

_migrate_cafe_if_needed()

# 원고 상태 정의
STATUSES = ["작성대기", "작성완료", "수정요청", "검수완료", "발행완료", "보류"]
STATUS_COLORS = {
    "작성대기": "#6B7280",   # gray
    "작성완료": "#F59E0B",   # amber
    "수정요청": "#EF4444",   # red
    "검수완료": "#3B82F6",   # blue
    "발행완료": "#10B981",   # green
    "보류":    "#8B5CF6",   # purple
}


def _get_conn():
    """cafe.db 연결. equipment.db를 ATTACH하여 evt_branches 등 참조 가능."""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    # foreign_keys OFF: cafe_branch_periods.branch_id가 equipment.db의 evt_branches를 참조하므로
    # 크로스 DB FK 체크 불가. 대신 애플리케이션 로직으로 무결성 보장.
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.row_factory = sqlite3.Row
    # equipment.db를 ATTACH (evt_branches JOIN 등 크로스 DB 조회용)
    equip_path = os.path.abspath(EQUIPMENT_DB_PATH)
    if os.path.exists(equip_path):
        try:
            conn.execute(f"ATTACH DATABASE '{equip_path}' AS equip")
        except sqlite3.OperationalError:
            # 이미 ATTACH 된 경우
            pass
    return conn


# ============================================================
# 기간 (Period) 관리
# ============================================================

def get_or_create_period(year: int, month: int) -> int:
    """카페 기간을 생성하거나 기존 ID를 반환."""
    conn = _get_conn()
    c = conn.cursor()
    label = f"{str(year)[-2:]}.{month:02d}"

    c.execute("SELECT id FROM cafe_periods WHERE year = ? AND month = ?", (year, month))
    row = c.fetchone()

    if row:
        period_id = row[0]
    else:
        c.execute(
            "INSERT INTO cafe_periods (year, month, label, is_current) VALUES (?, ?, ?, 1)",
            (year, month, label),
        )
        period_id = c.lastrowid

    # 현재 기간 표시 갱신
    c.execute("UPDATE cafe_periods SET is_current = 0 WHERE id != ?", (period_id,))
    c.execute("UPDATE cafe_periods SET is_current = 1 WHERE id = ?", (period_id,))
    conn.commit()
    conn.close()
    return period_id


def load_cafe_periods() -> list[dict]:
    """전체 카페 기간 목록 반환 (최신순)."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM cafe_periods ORDER BY year DESC, month DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ============================================================
# 지점-기간 (Branch Period) 관리
# ============================================================

def get_or_create_branch_period(period_id: int, branch_id: int) -> int:
    """지점-기간 메타데이터를 생성하거나 기존 ID를 반환."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM cafe_branch_periods WHERE cafe_period_id = ? AND branch_id = ?",
        (period_id, branch_id),
    )
    row = c.fetchone()
    if row:
        bp_id = row[0]
    else:
        c.execute(
            "INSERT INTO cafe_branch_periods (cafe_period_id, branch_id) VALUES (?, ?)",
            (period_id, branch_id),
        )
        bp_id = c.lastrowid
        conn.commit()
    conn.close()
    return bp_id


def update_branch_metadata(branch_period_id: int, **kwargs):
    """지점-기간 메타데이터 업데이트 (smart_manager, writer, publisher 등)."""
    allowed = {
        "smart_manager", "writer", "publisher",
        "publish_count", "review_count", "superset_count",
        "self_made", "report_link", "comment_link",
        "photo_link", "general_photo_link", "progress_note",
    }
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [branch_period_id]
    conn = _get_conn()
    conn.execute(f"UPDATE cafe_branch_periods SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def load_branch_period_meta(branch_period_id: int) -> dict | None:
    """지점-기간 메타데이터 조회."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT cbp.*, eb.name as branch_name, eb.short_name,
               cp.year, cp.month, cp.label as period_label
        FROM cafe_branch_periods cbp
        JOIN equip.evt_branches eb ON cbp.branch_id = eb.id
        JOIN cafe_periods cp ON cbp.cafe_period_id = cp.id
        WHERE cbp.id = ?
    """, (branch_period_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


# ============================================================
# 원고 (Article) CRUD
# ============================================================

def upsert_article(branch_period_id: int, article_order: int, **kwargs) -> int:
    """원고를 생성하거나 업데이트. article_id 반환."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM cafe_articles WHERE branch_period_id = ? AND article_order = ?",
        (branch_period_id, article_order),
    )
    row = c.fetchone()

    fields = {
        "keyword": kwargs.get("keyword", ""),
        "category": kwargs.get("category", ""),
        "equipment_name": kwargs.get("equipment_name", ""),
        "photo_ref": kwargs.get("photo_ref", ""),
        "title": kwargs.get("title", ""),
        "body": kwargs.get("body", ""),
    }

    if row:
        article_id = row[0]
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [datetime.now().isoformat(), article_id]
        c.execute(f"UPDATE cafe_articles SET {set_clause}, updated_at = ? WHERE id = ?", values)
    else:
        fields["branch_period_id"] = branch_period_id
        fields["article_order"] = article_order
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" * len(fields))
        c.execute(f"INSERT INTO cafe_articles ({cols}) VALUES ({placeholders})", list(fields.values()))
        article_id = c.lastrowid

    conn.commit()
    conn.close()
    return article_id


def update_article(article_id: int, **kwargs):
    """원고 필드 업데이트 (title, body, keyword, category, equipment_name, photo_ref)."""
    allowed = {"title", "body", "keyword", "category", "equipment_name", "photo_ref"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [article_id]
    conn = _get_conn()
    conn.execute(f"UPDATE cafe_articles SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def set_published_info(article_id: int, url: str, published_by: str):
    """발행 정보 기록."""
    conn = _get_conn()
    conn.execute(
        "UPDATE cafe_articles SET published_url = ?, published_at = ?, published_by = ? WHERE id = ?",
        (url, datetime.now().isoformat(), published_by, article_id),
    )
    conn.commit()
    conn.close()



def load_cafe_articles(branch_period_id: int) -> pd.DataFrame:
    """지점-기간의 원고 목록 반환 (본문 프리뷰 + 댓글/대댓글 포함)."""
    conn = _get_conn()
    df = pd.read_sql_query(
        """SELECT a.id, a.article_order, a.keyword, a.category, a.equipment_name,
                  a.title, a.body, a.status, a.published_url, a.created_at, a.updated_at,
                  COALESCE(cmt.comment_count, 0) AS comment_count,
                  COALESCE(cmt.comments_json, '[]') AS comments_json
           FROM cafe_articles a
           LEFT JOIN (
               SELECT article_id,
                      COUNT(*) AS comment_count,
                      '[' || GROUP_CONCAT(
                          '{"slot":' || slot_number ||
                          ',"comment":' || json_quote(COALESCE(comment_text, '')) ||
                          ',"reply":' || json_quote(COALESCE(reply_text, '')) || '}'
                      ) || ']' AS comments_json
               FROM cafe_comments
               WHERE comment_text != '' OR reply_text != ''
               GROUP BY article_id
           ) cmt ON cmt.article_id = a.id
           WHERE a.branch_period_id = ?
           ORDER BY a.article_order""",
        conn, params=(branch_period_id,),
    )
    conn.close()
    return df


def load_cafe_article_detail(article_id: int) -> dict | None:
    """원고 상세 + 댓글 + 피드백 조회."""
    conn = _get_conn()
    c = conn.cursor()

    # 원고 본문
    c.execute("SELECT * FROM cafe_articles WHERE id = ?", (article_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    article = dict(row)

    # 댓글 3슬롯
    c.execute(
        "SELECT slot_number, comment_text, reply_text FROM cafe_comments WHERE article_id = ? ORDER BY slot_number",
        (article_id,),
    )
    article["comments"] = [dict(r) for r in c.fetchall()]

    # 피드백 이력
    c.execute(
        "SELECT id, author, content, created_at FROM cafe_feedbacks WHERE article_id = ? ORDER BY created_at DESC",
        (article_id,),
    )
    article["feedbacks"] = [dict(r) for r in c.fetchall()]

    conn.close()
    return article


# ============================================================
# 댓글 (Comment) CRUD
# ============================================================

def upsert_comment(article_id: int, slot_number: int, comment_text: str, reply_text: str):
    """댓글/대댓글 저장 (INSERT OR REPLACE)."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO cafe_comments (article_id, slot_number, comment_text, reply_text)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(article_id, slot_number)
           DO UPDATE SET comment_text = excluded.comment_text,
                         reply_text = excluded.reply_text""",
        (article_id, slot_number, comment_text, reply_text),
    )
    conn.commit()
    conn.close()


# ============================================================
# 피드백 (Feedback)
# ============================================================

def add_feedback(article_id: int, author: str, content: str):
    """피드백 추가."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO cafe_feedbacks (article_id, author, content) VALUES (?, ?, ?)",
        (article_id, author, content),
    )
    conn.commit()
    conn.close()


# ============================================================
# 상태 관리 + 이력 로그
# ============================================================

def change_status(article_id: int, new_status: str, changed_by: str = "", note: str = ""):
    """원고 상태 변경 + 자동 이력 기록."""
    if new_status not in STATUSES:
        raise ValueError(f"유효하지 않은 상태: {new_status}")

    conn = _get_conn()
    c = conn.cursor()

    # 현재 상태 조회
    c.execute("SELECT status FROM cafe_articles WHERE id = ?", (article_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    old_status = row[0]

    if old_status == new_status:
        conn.close()
        return

    now = datetime.now().isoformat()

    # 상태 업데이트
    c.execute(
        "UPDATE cafe_articles SET status = ?, status_updated_at = ?, updated_at = ? WHERE id = ?",
        (new_status, now, now, article_id),
    )

    # 이력 기록
    c.execute(
        "INSERT INTO cafe_status_log (article_id, old_status, new_status, changed_by, note) VALUES (?, ?, ?, ?, ?)",
        (article_id, old_status, new_status, changed_by, note),
    )

    conn.commit()
    conn.close()


def load_status_history(article_id: int) -> list[dict]:
    """원고 상태 변경 이력 조회."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM cafe_status_log WHERE article_id = ? ORDER BY changed_at DESC",
        (article_id,),
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ============================================================
# 대시보드 요약
# ============================================================


def load_cafe_summary(period_id: int) -> list[dict]:
    """기간별 전 지점 원고 현황 요약."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT
            eb.name as branch_name,
            cbp.id as branch_period_id,
            cbp.smart_manager,
            cbp.writer,
            cbp.publisher,
            cbp.publish_count,
            cbp.review_count,
            cbp.superset_count,
            cbp.photo_link,
            cbp.general_photo_link,
            cbp.progress_note,
            COUNT(ca.id) as total_articles,
            SUM(CASE WHEN ca.status = '작성대기' THEN 1 ELSE 0 END) as cnt_waiting,
            SUM(CASE WHEN ca.status = '작성완료' THEN 1 ELSE 0 END) as cnt_written,
            SUM(CASE WHEN ca.status = '수정요청' THEN 1 ELSE 0 END) as cnt_revision,
            SUM(CASE WHEN ca.status = '검수완료' THEN 1 ELSE 0 END) as cnt_reviewed,
            SUM(CASE WHEN ca.status = '발행완료' THEN 1 ELSE 0 END) as cnt_published,
            SUM(CASE WHEN ca.status = '보류' THEN 1 ELSE 0 END) as cnt_hold,
            -- 원고 유형별 카운트 (category 기반)
            SUM(CASE WHEN ca.category = '정보성' THEN 1 ELSE 0 END) as cnt_info,
            SUM(CASE WHEN ca.category = '후기성' THEN 1 ELSE 0 END) as cnt_review_type,
            SUM(CASE WHEN ca.category = '슈퍼세트' THEN 1 ELSE 0 END) as cnt_superset,
            -- 유형별 완료 카운트 (발행완료 기준)
            SUM(CASE WHEN ca.category = '정보성' AND ca.status = '발행완료' THEN 1 ELSE 0 END) as cnt_info_done,
            SUM(CASE WHEN ca.category = '후기성' AND ca.status = '발행완료' THEN 1 ELSE 0 END) as cnt_review_done,
            SUM(CASE WHEN ca.category = '슈퍼세트' AND ca.status = '발행완료' THEN 1 ELSE 0 END) as cnt_superset_done
        FROM cafe_branch_periods cbp
        JOIN equip.evt_branches eb ON cbp.branch_id = eb.id
        LEFT JOIN cafe_articles ca ON ca.branch_period_id = cbp.id
        WHERE cbp.cafe_period_id = ?
        GROUP BY cbp.id
        ORDER BY eb.name
    """, (period_id,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ============================================================
# 장비 컨텍스트 (device_info + evt_items + equipment 조합)
# ============================================================

def _get_equipment_conn():
    """equipment.db 전용 연결 (이벤트/보유장비 조회용)."""
    conn = sqlite3.connect(EQUIPMENT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_equipment_context(branch_name: str, equipment_name: str) -> dict:
    """장비 상세 정보 + 해당 지점 이벤트 가격 + 보유 여부 조회.

    device_info, evt_*, equipment → equipment.db에서 조회.

    Returns:
        {
            "device_info": {...} or None,
            "events": [{"display_name": ..., "event_price": ..., ...}, ...],
            "is_owned": bool,
            "quantity": int,
        }
    """
    if not equipment_name or not equipment_name.strip():
        return {"device_info": None, "events": [], "is_owned": False, "quantity": 0}

    conn = _get_equipment_conn()
    c = conn.cursor()
    result = {"device_info": None, "events": [], "is_owned": False, "quantity": 0}

    # 1. device_info에서 장비 상세 (공용 matcher 엔진 사용)
    from equipment.matcher import match_devices
    matched = match_devices(equipment_name.strip())
    if matched:
        result["device_info"] = matched[0]

    # 2. 이벤트 검색용 키워드 수집 (장비명 + 매칭된 모든 관련 장비명)
    #    예: "써마지FLX" 클릭 → ["써마지FLX", "써마지"] 모두로 검색
    search_names = {equipment_name.strip()}
    for m in matched:
        search_names.add(m["name"])
        # aliases도 추가
        for alias in (m.get("aliases") or "").split(","):
            a = alias.strip()
            if a and len(a) >= 2:
                search_names.add(a)

    # 2-1. 해당 지점의 현재 이벤트 가격 (모든 관련 키워드로 검색)
    like_conditions = []
    like_params = [branch_name]
    for name in search_names:
        like_conditions.append("(ei.raw_event_name LIKE ? OR ei.display_name LIKE ?)")
        like_params.extend([f"%{name}%", f"%{name}%"])

    where_like = " OR ".join(like_conditions) if like_conditions else "1=0"
    c.execute(f"""
        SELECT DISTINCT ei.display_name, ei.event_price, ei.regular_price,
               ei.session_count, ei.session_unit, ei.notes
        FROM evt_items ei
        JOIN evt_branches eb ON ei.branch_id = eb.id
        JOIN evt_periods ep ON ei.event_period_id = ep.id
        WHERE eb.name = ? AND ep.is_current = 1
          AND ({where_like})
        ORDER BY ei.event_price
    """, like_params)
    result["events"] = [dict(r) for r in c.fetchall()]

    # 3. 보유 여부 확인 (equipment 테이블)
    equip_like = " OR ".join(["e.name LIKE ?" for _ in search_names])
    equip_params = [branch_name] + [f"%{n}%" for n in search_names]
    c.execute(f"""
        SELECT e.quantity
        FROM equipment e
        JOIN branches b ON e.branch_id = b.id
        WHERE b.name = ? AND ({equip_like})
    """, equip_params)
    row = c.fetchone()
    if row:
        result["is_owned"] = True
        result["quantity"] = row[0]

    conn.close()
    return result


# ============================================================
# 동기화 로그
# ============================================================

def create_sync_log(period_id: int) -> int:
    """동기화 로그 시작."""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO cafe_sync_log (cafe_period_id, status) VALUES (?, 'started')",
        (period_id,),
    )
    log_id = c.lastrowid
    conn.commit()
    conn.close()
    return log_id


def update_sync_log(log_id: int, status: str, total_branches: int, total_articles: int, error_log: str = None):
    """동기화 로그 완료."""
    conn = _get_conn()
    conn.execute(
        "UPDATE cafe_sync_log SET status = ?, total_branches = ?, total_articles = ?, error_log = ?, completed_at = ? WHERE id = ?",
        (status, total_branches, total_articles, error_log, datetime.now().isoformat(), log_id),
    )
    conn.commit()
    conn.close()
