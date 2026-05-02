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
    return run_check_all(triggered_by="manual")


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


# ── 진단용 (admin 전용 read-only) ──

@router.get("/diagnostics")
async def get_diagnostics(user: Annotated[dict, Depends(require_role("admin"))]):
    """SB체커 운영 상태 진단 — 자동 연동/측정이 왜 안 되는지 즉시 파악."""
    from shared.db import get_conn, EQUIPMENT_DB
    conn = get_conn(EQUIPMENT_DB)
    try:
        # rank_check_keywords origin/is_active 분포
        kw_rows = conn.execute("""
            SELECT origin, is_active, COUNT(*) AS c
              FROM rank_check_keywords
             GROUP BY origin, is_active
        """).fetchall()
        kw_breakdown = [dict(r) for r in kw_rows]
        kw_total = sum(r["c"] for r in kw_breakdown)

        # evt_branches default_place_id 등록 상태
        branch_active = conn.execute(
            "SELECT COUNT(*) FROM evt_branches WHERE is_active = 1"
        ).fetchone()[0]
        branch_missing_pid = conn.execute("""
            SELECT COUNT(*) FROM evt_branches
             WHERE is_active = 1
               AND (default_place_id IS NULL OR default_place_id = '')
        """).fetchone()[0]

        # place_daily distinct 키워드 (자동 연동의 source)
        pd_distinct = conn.execute("""
            SELECT COUNT(DISTINCT branch_id || '|' || keyword)
              FROM place_daily
             WHERE keyword != '' AND branch_id > 0
        """).fetchone()[0]
        pd_today = conn.execute("""
            SELECT COUNT(*) FROM place_daily WHERE date = date('now','localtime')
        """).fetchone()[0]

        # rank_checks 최근 7일
        rc_recent = conn.execute("""
            SELECT COUNT(*) FROM rank_checks
             WHERE date >= date('now','-7 days','localtime')
        """).fetchone()[0]
        rc_today = conn.execute("""
            SELECT COUNT(*) FROM rank_checks WHERE date = date('now','localtime')
        """).fetchone()[0]

        # 자동 연동 hook이 발동했는지 sync_log에서 확인
        last_place_sync = conn.execute("""
            SELECT synced_at, triggered_by, detail FROM sync_log
             WHERE sync_type = 'place_sheets_to_db'
             ORDER BY synced_at DESC LIMIT 1
        """).fetchone()

        return {
            "rank_check_keywords": {
                "total": kw_total,
                "breakdown": kw_breakdown,
            },
            "evt_branches": {
                "active": branch_active,
                "default_place_id_missing": branch_missing_pid,
            },
            "place_daily": {
                "distinct_keywords": pd_distinct,
                "rows_today": pd_today,
            },
            "rank_checks": {
                "rows_today": rc_today,
                "rows_last_7_days": rc_recent,
            },
            "last_place_sync": dict(last_place_sync) if last_place_sync else None,
        }
    finally:
        conn.close()


class PlaceIdEntry(BaseModel):
    branch_id: int
    place_id: str


class AutoMatchRequest(BaseModel):
    brand_prefix: Optional[str] = None  # 검색 시 prefix로 결합 (예: '유앤아이의원')


@router.post("/auto-match-branches")
async def auto_match_branches(
    user: Annotated[dict, Depends(require_role("admin"))],
    body: AutoMatchRequest = None,
):
    """default_place_id 미등록 지점 전체에 네이버 검색 자동 매칭.

    body.brand_prefix가 있으면 모든 검색어에 prefix 결합 (예: '유앤아이의원 강남점').
    score >= 0.95: 자동 저장. 0.7~0.95: 검토 대기. <0.7: 수동 필요.
    응답: {matched, pending_review, manual_required, stats}
    """
    from shared.db import get_conn, EQUIPMENT_DB
    from checker.place_id_finder import auto_match_unregistered_branches
    bp = (body.brand_prefix if body else None)
    conn = get_conn(EQUIPMENT_DB)
    try:
        return auto_match_unregistered_branches(conn, brand_prefix=bp, dry_run=False)
    finally:
        conn.close()


@router.post("/save-place-ids")
async def save_place_ids(
    items: list[PlaceIdEntry],
    user: Annotated[dict, Depends(require_role("admin"))],
):
    """admin이 검토/입력 화면에서 확정한 [{branch_id, place_id}] 일괄 저장.

    각 지점 default_place_id 저장 + 해당 지점의 추적 미설정 키워드 자동 활성화.
    응답: {saved, activated_keywords}
    """
    from shared.db import get_conn, EQUIPMENT_DB
    from checker.place_id_finder import save_place_ids_bulk
    conn = get_conn(EQUIPMENT_DB)
    try:
        return save_place_ids_bulk(conn, [it.model_dump() for it in items])
    finally:
        conn.close()


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
