"""주간 보고서 SQLite 읽기/쓰기 모듈.

테이블: weekly_reports
DB: equipment.db (shared.db.EQUIPMENT_DB)
"""

import json
import sqlite3
from typing import Optional

from shared.db import get_conn, EQUIPMENT_DB


def _ensure_tables():
    """weekly_reports 테이블 초기화."""
    conn = sqlite3.connect(EQUIPMENT_DB)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS weekly_reports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start  DATE NOT NULL UNIQUE,
                week_end    DATE NOT NULL,
                title       TEXT DEFAULT '',
                data_json   TEXT NOT NULL DEFAULT '{}',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by  INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_weekly_reports_week_start
                ON weekly_reports(week_start DESC);
        """)
        conn.commit()
    finally:
        conn.close()


def _ensure_is_paused_column():
    """evt_branches.is_paused 컬럼 보장 (SQLite는 IF NOT EXISTS 미지원)."""
    conn = sqlite3.connect(EQUIPMENT_DB)
    try:
        conn.execute("ALTER TABLE evt_branches ADD COLUMN is_paused INTEGER NOT NULL DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 이미 존재하면 무시
    finally:
        conn.close()


# 모듈 import 시점에 테이블 보장
_ensure_tables()
_ensure_is_paused_column()


def list_reports(limit: Optional[int] = None) -> list[dict]:
    """주차 목록. 최신순. data_json은 제외(목록이 무거워지지 않게)."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = """
            SELECT id, week_start, week_end, title, created_at, updated_at, created_by
            FROM weekly_reports
            ORDER BY week_start DESC
        """
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [dict(r) for r in conn.execute(sql).fetchall()]
    finally:
        conn.close()


def get_report(week_start: str) -> Optional[dict]:
    """단건 조회. data_json은 dict로 파싱해서 반환."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT * FROM weekly_reports WHERE week_start = ?",
            (week_start,),
        ).fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result["data"] = json.loads(result.pop("data_json") or "{}")
        except json.JSONDecodeError:
            result["data"] = {}
            result.pop("data_json", None)
        return result
    finally:
        conn.close()


def create_report(
    week_start: str,
    week_end: str,
    title: str,
    data: dict,
    created_by: Optional[int],
) -> dict:
    """신규 작성. UNIQUE(week_start) 위반 시 sqlite3.IntegrityError 발생."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute(
            """INSERT INTO weekly_reports (week_start, week_end, title, data_json, created_by)
               VALUES (?, ?, ?, ?, ?)""",
            (week_start, week_end, title or "", json.dumps(data, ensure_ascii=False), created_by),
        )
        conn.commit()
        return get_report(week_start)
    finally:
        conn.close()


def update_report(
    week_start: str,
    title: Optional[str],
    data: Optional[dict],
) -> Optional[dict]:
    """수정. 전달된 필드만 업데이트. updated_at 자동 갱신."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        existing = conn.execute(
            "SELECT id FROM weekly_reports WHERE week_start = ?", (week_start,)
        ).fetchone()
        if not existing:
            return None
        sets = ["updated_at = CURRENT_TIMESTAMP"]
        params: list = []
        if title is not None:
            sets.append("title = ?")
            params.append(title)
        if data is not None:
            sets.append("data_json = ?")
            params.append(json.dumps(data, ensure_ascii=False))
        params.append(week_start)
        conn.execute(
            f"UPDATE weekly_reports SET {', '.join(sets)} WHERE week_start = ?",
            params,
        )
        conn.commit()
        return get_report(week_start)
    finally:
        conn.close()


def delete_report(week_start: str) -> bool:
    """삭제. 성공 시 True, 대상 없으면 False."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        cur = conn.execute("DELETE FROM weekly_reports WHERE week_start = ?", (week_start,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
