"""블로그 콘텐츠 데이터 SQLite 읽기/쓰기 모듈.

테이블: blog_articles, blog_tags, blog_status_log
DB: data/blog.db (카페/장비와 독립)
"""

import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "blog.db")
EQUIPMENT_DB_PATH = os.path.join(DB_DIR, "equipment.db")


def _ensure_tables():
    """blog.db 테이블 초기화."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS blog_articles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id       INTEGER,
            branch_name     TEXT DEFAULT '',
            title           TEXT NOT NULL DEFAULT '',
            body            TEXT DEFAULT '',
            category        TEXT DEFAULT '',
            equipment_name  TEXT DEFAULT '',
            device_info_id  INTEGER,
            writer          TEXT DEFAULT '',
            status          TEXT DEFAULT '작성대기',
            published_url   TEXT DEFAULT '',
            published_at    TEXT,
            year            INTEGER,
            month           INTEGER,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS blog_tags (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      INTEGER NOT NULL,
            device_info_id  INTEGER,
            tag_name        TEXT NOT NULL,
            UNIQUE(article_id, tag_name)
        );

        CREATE TABLE IF NOT EXISTS blog_status_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      INTEGER NOT NULL,
            old_status      TEXT,
            new_status      TEXT NOT NULL,
            changed_by      TEXT DEFAULT '',
            note            TEXT DEFAULT '',
            changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

_ensure_tables()


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


# ── CRUD ──

def get_all_articles(year: int = None, month: int = None,
                     branch_name: str = None, status: str = None) -> list[dict]:
    conn = _get_conn()
    query = "SELECT * FROM blog_articles WHERE 1=1"
    params = []
    if year:
        query += " AND year = ?"
        params.append(year)
    if month:
        query += " AND month = ?"
        params.append(month)
    if branch_name:
        query += " AND branch_name = ?"
        params.append(branch_name)
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY year DESC, month DESC, id DESC"
    rows = [dict(r) for r in conn.execute(query, params).fetchall()]
    conn.close()
    return rows


def get_article(article_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM blog_articles WHERE id = ?", (article_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_article(**kwargs) -> int:
    conn = _get_conn()
    cols = [k for k in kwargs if kwargs[k] is not None]
    vals = [kwargs[k] for k in cols]
    placeholders = ",".join(["?"] * len(cols))
    col_str = ",".join(cols)
    c = conn.execute(f"INSERT INTO blog_articles ({col_str}) VALUES ({placeholders})", vals)
    conn.commit()
    article_id = c.lastrowid
    conn.close()
    return article_id


def update_article(article_id: int, **kwargs) -> bool:
    conn = _get_conn()
    sets = []
    vals = []
    for k, v in kwargs.items():
        sets.append(f"{k} = ?")
        vals.append(v)
    sets.append("updated_at = ?")
    vals.append(datetime.now().isoformat())
    vals.append(article_id)
    conn.execute(f"UPDATE blog_articles SET {','.join(sets)} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return True


def delete_article(article_id: int) -> bool:
    conn = _get_conn()
    conn.execute("DELETE FROM blog_tags WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM blog_status_log WHERE article_id = ?", (article_id,))
    conn.execute("DELETE FROM blog_articles WHERE id = ?", (article_id,))
    conn.commit()
    conn.close()
    return True


# ── 태그 ──

def get_tags(article_id: int) -> list[dict]:
    conn = _get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM blog_tags WHERE article_id = ?", (article_id,)
    ).fetchall()]
    conn.close()
    return rows


def add_tag(article_id: int, tag_name: str, device_info_id: int = None):
    conn = _get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO blog_tags (article_id, tag_name, device_info_id) VALUES (?,?,?)",
        (article_id, tag_name, device_info_id)
    )
    conn.commit()
    conn.close()


# ── 상태 이력 ──

def log_status_change(article_id: int, old_status: str, new_status: str,
                      changed_by: str = "", note: str = ""):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO blog_status_log (article_id, old_status, new_status, changed_by, note) VALUES (?,?,?,?,?)",
        (article_id, old_status, new_status, changed_by, note)
    )
    conn.commit()
    conn.close()


# ── 장비별 블로그 조회 (크로스 DB) ──

def get_articles_by_device(device_info_id: int) -> list[dict]:
    """특정 장비와 관련된 블로그 원고 목록."""
    conn = _get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM blog_articles WHERE device_info_id = ? ORDER BY year DESC, month DESC",
        (device_info_id,)
    ).fetchall()]
    conn.close()
    return rows
