"""공통 SQLite 연결 유틸리티.

모든 모듈이 동일한 PRAGMA 설정(WAL, busy_timeout)을 사용하도록 보장.
"""

import sqlite3
import os
from datetime import datetime

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# DB 경로 상수
EQUIPMENT_DB = os.path.join(_DATA_DIR, "equipment.db")
CAFE_DB = os.path.join(_DATA_DIR, "cafe.db")
BLOG_DB = os.path.join(_DATA_DIR, "blog.db")
SYSTEM_DB = os.path.join(_DATA_DIR, "system.db")


def get_conn(db_path: str = EQUIPMENT_DB, *, attach: dict[str, str] | None = None) -> sqlite3.Connection:
    """SQLite 연결 반환 (WAL + busy_timeout 30초).

    Args:
        db_path: 연결할 DB 파일 경로. 기본값은 equipment.db.
        attach: 추가 ATTACH할 DB. {"alias": "/path/to/db"} 형식.
    """
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row

    if attach:
        for alias, path in attach.items():
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                try:
                    conn.execute(f"ATTACH DATABASE '{abs_path}' AS {alias}")
                except sqlite3.OperationalError:
                    pass  # 이미 ATTACH된 경우

    return conn


def now_str() -> str:
    """SQLite DEFAULT와 일관된 날짜 문자열 반환.

    형식: '2026-04-01 14:30:00' (공백 구분, 초까지)
    SQLite의 datetime('now','localtime')와 동일.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_sync(sync_type: str, added: int = 0, skipped: int = 0, conflicts: int = 0,
             detail: str = "", triggered_by: str = "manual") -> None:
    """sync_log 통합 기록 헬퍼.

    - synced_at은 KST datetime.now()로 명시 (SQLite DEFAULT CURRENT_TIMESTAMP는 UTC라 사용 금지)
    - 별도 connection으로 안전 기록 (호출자의 트랜잭션 영향 없음)
    - 호출자가 try/except로 감싸서 실패 로깅도 가능
    """
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute(
            "INSERT INTO sync_log (sync_type, added, skipped, conflicts, "
            "detail, synced_at, triggered_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sync_type, added, skipped, conflicts, detail,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), triggered_by)
        )
        conn.commit()
    finally:
        conn.close()
