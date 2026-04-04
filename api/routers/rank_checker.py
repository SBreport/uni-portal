"""순위 체크 라우터 — SB체커 기능 (admin/editor 전용)."""

import json
import sqlite3
import tempfile
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
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


@router.get("/check-all-stream")
async def check_all_stream(user: Annotated[dict, Depends(_editor)]):
    """전 지점 순위 체크 — SSE 스트리밍."""
    from checker.place_rank import run_check_all_stream

    def event_generator():
        for event in run_check_all_stream():
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


# ── SB_CHECKER DB 임포트 ──

@router.post("/import-sb-db")
async def import_sb_db(
    user: Annotated[dict, Depends(require_role("admin"))],
    file: UploadFile = File(...),
):
    """SB_CHECKER data.db 업로드 → keywords를 rank_check_keywords로 마이그레이션.

    SB_CHECKER DB 스키마:
      - customers: id, name (지점명)
      - keywords: id, customerId, customerName, keyword, searchKeyword,
                  placeId, executor, guaranteedRank, contractStatus, memo
    """
    from shared.db import get_conn, EQUIPMENT_DB

    # 업로드 파일을 임시 파일로 저장
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # SB_CHECKER DB 열기
        sb_conn = sqlite3.connect(tmp_path)
        sb_conn.row_factory = sqlite3.Row

        # keywords 테이블 읽기 (active만)
        sb_keywords = sb_conn.execute("""
            SELECT k.*, c.name as customer_name_joined
            FROM keywords k
            LEFT JOIN customers c ON k.customerId = c.id
            WHERE k.contractStatus = 'active'
            ORDER BY k.customerName, k.keyword
        """).fetchall()
        sb_keywords = [dict(r) for r in sb_keywords]
        sb_conn.close()

        # uni-portal의 evt_branches에서 지점명 → branch_id 매핑
        conn = get_conn(EQUIPMENT_DB)
        try:
            branches = conn.execute("SELECT id, name FROM evt_branches").fetchall()
            branch_map = {r["name"]: r["id"] for r in branches}
            # short_name도 매핑 (e.g., "선릉" → "선릉유앤아이")
            branch_by_short = {}
            for r in branches:
                short = r["name"].replace("유앤아이", "")
                branch_by_short[short] = r["id"]
                branch_by_short[r["name"]] = r["id"]

            imported = 0
            skipped = 0
            unmatched = []

            for kw in sb_keywords:
                customer_name = kw.get("customerName") or kw.get("customer_name_joined") or ""
                keyword = kw.get("keyword", "")
                place_id = str(kw.get("placeId", "")).replace(".0", "").strip()
                search_keyword = kw.get("searchKeyword") or ""
                guaranteed_rank = kw.get("guaranteedRank") or 5
                memo = kw.get("memo") or kw.get("executor") or ""

                if not keyword or not place_id:
                    skipped += 1
                    continue

                # 지점명 매핑
                branch_id = branch_map.get(customer_name) or branch_by_short.get(customer_name)
                if not branch_id:
                    # "유앤아이" 붙여서 재시도
                    branch_id = branch_map.get(customer_name + "유앤아이")

                if not branch_id:
                    skipped += 1
                    unmatched.append(customer_name)
                    continue

                # branch_name 확정
                branch_name = customer_name if customer_name in branch_map else customer_name + "유앤아이"
                if branch_name not in branch_map:
                    # branch_by_short에서 찾은 경우
                    for name, bid in branch_map.items():
                        if bid == branch_id:
                            branch_name = name
                            break

                conn.execute("""
                    INSERT OR IGNORE INTO rank_check_keywords
                    (branch_id, branch_name, keyword, search_keyword, place_id, guaranteed_rank, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (branch_id, branch_name, keyword, search_keyword, place_id, guaranteed_rank, memo))
                imported += 1

            conn.commit()

            return {
                "ok": True,
                "imported": imported,
                "skipped": skipped,
                "total_in_sb": len(sb_keywords),
                "unmatched_branches": list(set(unmatched)),
            }
        finally:
            conn.close()
    finally:
        import os
        os.unlink(tmp_path)
