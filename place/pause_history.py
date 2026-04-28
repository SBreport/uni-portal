"""플레이스 지점 휴식 이력 관리."""

import sqlite3
from datetime import date


def ensure_pause_history_table(conn: sqlite3.Connection) -> None:
    """휴식 이력 테이블 보장."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS place_branch_pause_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            branch_name TEXT NOT NULL,
            paused_at DATE NOT NULL,
            resumed_at DATE,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pause_history_branch
        ON place_branch_pause_history(branch_id, paused_at DESC)
    """)
    conn.commit()


def record_pause_change(
    conn: sqlite3.Connection,
    branch_id: int,
    branch_name: str,
    old_paused: int,
    new_paused: int,
    change_date: str,
) -> None:
    """휴식 상태 변경 기록.

    - 0 → 1: 휴식 시작 (새 행 INSERT, resumed_at NULL)
    - 1 → 0: 휴식 종료 (가장 최근 NULL 행에 resumed_at UPDATE)
    """
    if old_paused == new_paused:
        return

    if old_paused == 0 and new_paused == 1:
        # 휴식 시작
        conn.execute("""
            INSERT INTO place_branch_pause_history (branch_id, branch_name, paused_at)
            VALUES (?, ?, ?)
        """, (branch_id, branch_name, change_date))
    elif old_paused == 1 and new_paused == 0:
        # 휴식 종료 — 가장 최근 미종료 행에 resumed_at 기록
        conn.execute("""
            UPDATE place_branch_pause_history
            SET resumed_at = ?
            WHERE id = (
                SELECT id FROM place_branch_pause_history
                WHERE branch_id = ? AND resumed_at IS NULL
                ORDER BY paused_at DESC LIMIT 1
            )
        """, (change_date, branch_id))
