"""지점명(branch_name) ↔ evt_branches.id 매핑 유틸.

place_daily.evt_branch_id가 아직 채워지지 않은 레거시 데이터를 위해
branch_name 문자열에서 evt_branches를 해석하는 공통 로직을 제공한다.

핵심 원칙: `short_name`이 `branch_name`에 포함되는 경우 중
**가장 긴 short_name을 우선** 매칭. 이로써 '광주'와 '경기광주' 처럼
한쪽이 다른쪽의 부분 문자열인 경우에도 정확히 분리된다.
"""

import sqlite3
from typing import Optional


def resolve_evt_branch_id(conn: sqlite3.Connection, branch_name: str) -> Optional[int]:
    """branch_name ('광주유앤아이')을 evt_branches.id로 해석.

    Returns:
        해당 지점 id. 매칭 안 되면 None.
    """
    if not branch_name:
        return None
    row = conn.execute(
        """SELECT id FROM evt_branches
           WHERE short_name IS NOT NULL AND short_name != ''
             AND INSTR(?, short_name) > 0
           ORDER BY LENGTH(short_name) DESC LIMIT 1""",
        (branch_name,),
    ).fetchone()
    if row is None:
        return None
    # sqlite3.Row / tuple 양쪽 지원
    return row["id"] if hasattr(row, "keys") else row[0]


def list_branch_names_for(
    conn: sqlite3.Connection,
    evt_branch_id: int,
    table: str,
) -> list[str]:
    """주어진 evt_branch_id에 해당하는 `table`의 DISTINCT branch_name 목록.

    table은 'place_daily' 또는 'webpage_daily' 등.
    place_daily.evt_branch_id FK가 비어있는 레거시 케이스용 대체 수단.
    """
    if table not in {"place_daily", "webpage_daily"}:
        raise ValueError(f"허용되지 않는 테이블: {table}")
    all_names = [
        r[0] for r in conn.execute(
            f"SELECT DISTINCT branch_name FROM {table} WHERE branch_name IS NOT NULL"
        ).fetchall()
    ]
    return [n for n in all_names if resolve_evt_branch_id(conn, n) == evt_branch_id]
