"""순위 체크 라우터 — SB체커 기능 (admin/editor 전용)."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from api.deps import get_current_user, require_role

router = APIRouter(prefix="/rank-checker", tags=["Rank Checker"])
_editor = require_role("editor")


class KeywordCreate(BaseModel):
    branch_id: int
    branch_name: str
    keyword: str
    search_keyword: str = ""
    place_id: str
    guaranteed_rank: int = 5
    memo: str = ""


class KeywordUpdate(BaseModel):
    keyword: Optional[str] = None
    search_keyword: Optional[str] = None
    place_id: Optional[str] = None
    guaranteed_rank: Optional[int] = None
    is_active: Optional[int] = None
    memo: Optional[str] = None


# ── 키워드 CRUD ──

@router.get("/keywords")
async def list_keywords(
    user: Annotated[dict, Depends(_editor)],
    branch_id: Optional[int] = None,
):
    """등록된 체크 키워드 목록."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT * FROM rank_check_keywords WHERE is_active = 1"
        params = []
        if branch_id:
            sql += " AND branch_id = ?"
            params.append(branch_id)
        sql += " ORDER BY branch_name, keyword"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@router.post("/keywords")
async def create_keyword(req: KeywordCreate, user: Annotated[dict, Depends(_editor)]):
    """체크 키워드 등록."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute("""
            INSERT OR IGNORE INTO rank_check_keywords
            (branch_id, branch_name, keyword, search_keyword, place_id, guaranteed_rank, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (req.branch_id, req.branch_name, req.keyword,
              req.search_keyword, req.place_id, req.guaranteed_rank, req.memo))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.patch("/keywords/{keyword_id}")
async def update_keyword(keyword_id: int, req: KeywordUpdate, user: Annotated[dict, Depends(_editor)]):
    """체크 키워드 수정."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        fields = {k: v for k, v in req.model_dump().items() if v is not None}
        if not fields:
            return {"ok": True}
        sets = ", ".join(f"{k} = ?" for k in fields)
        params = list(fields.values()) + [keyword_id]
        conn.execute(f"UPDATE rank_check_keywords SET {sets} WHERE id = ?", params)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/keywords/{keyword_id}")
async def delete_keyword(keyword_id: int, user: Annotated[dict, Depends(_editor)]):
    """체크 키워드 비활성화."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute("UPDATE rank_check_keywords SET is_active = 0 WHERE id = ?", (keyword_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


# ── 순위 체크 실행 ──

@router.post("/check/{branch_id}")
async def check_branch(branch_id: int, user: Annotated[dict, Depends(_editor)]):
    """특정 지점 순위 체크 실행."""
    from checker.place_rank import run_check_for_branch
    return run_check_for_branch(branch_id)


@router.post("/check-all")
async def check_all(user: Annotated[dict, Depends(_editor)]):
    """전 지점 순위 체크 실행."""
    from checker.place_rank import run_check_all
    return run_check_all()


# ── 결과 조회 ──

@router.get("/history/{branch_id}")
async def get_history(branch_id: int, user: Annotated[dict, Depends(_editor)], days: int = 30):
    """지점별 순위 체크 이력."""
    from checker.place_rank import get_branch_rank_history
    return get_branch_rank_history(branch_id, days)


@router.get("/comparison/{branch_id}")
async def get_comparison(
    branch_id: int,
    user: Annotated[dict, Depends(_editor)],
    date: Optional[str] = None,
):
    """실행사 vs SB체커 비교."""
    from checker.place_rank import get_comparison
    return get_comparison(branch_id, date)
