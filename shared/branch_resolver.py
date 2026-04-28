"""지점명(branch_name) ↔ evt_branches.id 매핑 유틸.

place_daily.evt_branch_id가 아직 채워지지 않은 레거시 데이터를 위해
branch_name 문자열에서 evt_branches를 해석하는 공통 로직을 제공한다.

매칭 우선순위:
1. **aliases 정확 매칭** — `evt_branches.aliases` (JSON 배열)에 branch_name이 포함되면 바로 매칭.
   예: 부산점.aliases = ["유앤아이의원 서면점"] → '유앤아이의원 서면점'은 부산점으로.
2. **short_name INSTR 매칭** — `short_name`이 `branch_name`에 포함되는 경우 중
   **가장 긴 short_name을 우선** 매칭. '광주'와 '경기광주'처럼
   한쪽이 다른쪽의 부분 문자열인 경우에도 정확히 분리된다.

aliases는 시트별로 같은 지점을 다른 이름으로 기록하는 케이스(예: 플레이스 지명 vs 공식 지점명)를
구조적으로 해결하기 위한 1차 매칭 경로다. 신규 별칭이 필요하면
`UPDATE evt_branches SET aliases = json_array(...) WHERE id = ?` 로 등록한다.
"""

import json
import sqlite3
from typing import Optional


def _ensure_aliases_column(conn: sqlite3.Connection) -> None:
    """evt_branches.aliases 컬럼 보장 (SQLite는 IF NOT EXISTS 미지원).

    레거시 DB에는 aliases 컬럼이 없어 resolver 첫 호출 시 OperationalError가 발생할 수 있다.
    호출 시점에 try-add 패턴으로 안전하게 컬럼 추가한다.
    """
    try:
        conn.execute("ALTER TABLE evt_branches ADD COLUMN aliases TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 이미 존재하면 무시


def resolve_evt_branch_id(conn: sqlite3.Connection, branch_name: str) -> Optional[int]:
    """branch_name을 evt_branches.id로 해석.

    Returns:
        해당 지점 id. 매칭 안 되면 None.
    """
    if not branch_name:
        return None

    # aliases 컬럼 자동 마이그레이션 (레거시 DB 호환)
    _ensure_aliases_column(conn)

    # 1차: aliases 정확 매칭
    alias_rows = conn.execute(
        "SELECT id, aliases FROM evt_branches WHERE aliases IS NOT NULL AND aliases != ''"
    ).fetchall()
    for r in alias_rows:
        aliases_raw = r["aliases"] if hasattr(r, "keys") else r[1]
        if not aliases_raw:
            continue
        try:
            aliases = json.loads(aliases_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(aliases, list) and branch_name in aliases:
            return r["id"] if hasattr(r, "keys") else r[0]

    # 2차: short_name INSTR 매칭 (가장 긴 것 우선)
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
