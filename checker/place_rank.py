"""네이버 플레이스 순위 체크 — SB_CHECKER에서 이식.

네이버 Place GraphQL API를 사용하여 키워드 검색 시 특정 place_id의 순위를 확인.
"""

import json
import time
import threading
import urllib.parse
import logging
from datetime import datetime, date
from typing import Optional

import requests

from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)

_rank_check_lock = threading.Lock()

GRAPHQL_URL = "https://api.place.naver.com/graphql"
GRAPHQL_QUERY = (
    "query getNxList($input: HospitalListInput) {"
    "  businesses: hospitals(input: $input) {"
    "    total"
    "    items {"
    "      id name category roadAddress"
    "      visitorReviewCount visitorReviewScore phone"
    "    }"
    "    queryString siteSort"
    "  }"
    "}"
)
DISPLAY = 50
USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 "
    "Mobile/15E148 Safari/604.1"
)


def _fetch_place_page(keyword: str, start: int = 1) -> dict:
    """네이버 플레이스 GraphQL API 검색."""
    payload = json.dumps({
        "operationName": "getNxList",
        "variables": {
            "input": {"query": keyword, "start": start, "display": DISPLAY}
        },
        "query": GRAPHQL_QUERY,
    })
    encoded = urllib.parse.quote(keyword)
    resp = requests.post(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "Referer": f"https://m.place.naver.com/hospital/list?query={encoded}",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def check_place_rank(keyword: str, place_id: str, max_results: int = 150) -> Optional[int]:
    """키워드로 검색하여 place_id의 순위 반환. 미노출 시 None."""
    place_id = str(place_id).replace('.0', '').strip()
    rank = 0
    start = 1

    while rank < max_results:
        try:
            data = _fetch_place_page(keyword, start=start)
        except Exception as e:
            logger.error(f"Place API 오류: {keyword} - {e}")
            return None

        businesses = data.get("data", {}).get("businesses", {})
        total = businesses.get("total", 0)
        items = businesses.get("items", [])
        if not items:
            break

        for item in items:
            rank += 1
            if rank > max_results:
                break
            if str(item.get("id", "")).strip() == place_id:
                return rank

        start += DISPLAY
        if start > total:
            break

    return None


def run_check_for_branch(branch_id: int) -> dict:
    """특정 지점의 등록된 키워드 전체 순위 체크."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        keywords = conn.execute(
            "SELECT * FROM rank_check_keywords WHERE branch_id = ? AND is_active = 1",
            (branch_id,)
        ).fetchall()

        if not keywords:
            return {"ok": True, "checked": 0, "message": "등록된 키워드 없음"}

        today = date.today().isoformat()
        results = []

        for kw in keywords:
            search_kw = kw["search_keyword"] or kw["keyword"]
            place_id = kw["place_id"]

            rank = check_place_rank(search_kw, place_id)
            is_exposed = 1 if rank and rank <= (kw["guaranteed_rank"] or 5) else 0

            conn.execute("""
                INSERT OR REPLACE INTO rank_checks
                (date, keyword_id, branch_id, branch_name, keyword, rank, is_exposed, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (today, kw["id"], kw["branch_id"], kw["branch_name"],
                  kw["keyword"], rank, is_exposed, datetime.now().isoformat()))

            results.append({
                "keyword": kw["keyword"],
                "rank": rank,
                "is_exposed": is_exposed,
            })

            time.sleep(0.5)

        conn.commit()
        return {"ok": True, "checked": len(results), "results": results}
    finally:
        conn.close()


def run_check_all(triggered_by: str = "manual") -> dict:
    """전 지점 순위 체크 (락 가드 + sync_log 기록)."""
    if not _rank_check_lock.acquire(blocking=False):
        return {"ok": False, "skipped": True, "reason": "이미 측정이 진행 중입니다"}
    try:
        return _run_check_all_inner(triggered_by)
    finally:
        _rank_check_lock.release()


def _run_check_all_inner(triggered_by: str) -> dict:
    """run_check_all 실제 실행 로직."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        branches = conn.execute(
            "SELECT DISTINCT branch_id, branch_name FROM rank_check_keywords WHERE is_active = 1"
        ).fetchall()
        branches = list(branches)
    finally:
        conn.close()

    success_count = 0
    failed_count = 0
    all_results = []

    for b in branches:
        result = run_check_for_branch(b["branch_id"])
        branch_success = result.get("checked", 0)
        success_count += branch_success
        all_results.extend(result.get("results", []))
        if not result.get("ok", True):
            failed_count += 1

    # is_active=0인 키워드 수 (=place_id 미등록 등으로 추적 미설정)
    conn2 = get_conn(EQUIPMENT_DB)
    try:
        skipped_count = conn2.execute(
            "SELECT COUNT(*) FROM rank_check_keywords WHERE is_active = 0"
        ).fetchone()[0]
        inactive_count = skipped_count

        # 측정 결과 기록
        detail_parts = [f"측정 {success_count}건"]
        if failed_count > 0:
            detail_parts.append(f"실패 {failed_count}건")
        if skipped_count > 0:
            detail_parts.append(f"미측정 {skipped_count}건 (place_id 미등록 등)")
        detail = ", ".join(detail_parts)

        if inactive_count > 0:
            detail = f"실패: 추적 미설정 키워드 {inactive_count}건. " + detail

        conn2.execute("""
            INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail, synced_at, triggered_by)
            VALUES ('rank_check_auto', ?, ?, 0, ?, ?, ?)
        """, (success_count, skipped_count, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), triggered_by))
        conn2.commit()
    finally:
        conn2.close()

    return {
        "ok": True,
        "branches": len(branches),
        "total_checked": success_count,
        "results": all_results,
    }


def run_check_all_stream():
    """전 지점 순위 체크 — 키워드마다 yield하는 제너레이터.

    Yields:
        dict: 각 단계의 상태 메시지.
            type="start"    → 전체 시작 정보
            type="checking"  → 키워드 체크 시작
            type="result"    → 키워드 체크 결과
            type="branch_done" → 지점 완료
            type="done"      → 전체 완료
            type="error"     → 오류
    """
    conn = get_conn(EQUIPMENT_DB)
    try:
        branches = conn.execute(
            "SELECT DISTINCT branch_id, branch_name FROM rank_check_keywords WHERE is_active = 1"
        ).fetchall()
        branches = [dict(b) for b in branches]
    finally:
        conn.close()

    # 키워드 총 개수
    conn2 = get_conn(EQUIPMENT_DB)
    try:
        total_keywords = conn2.execute(
            "SELECT COUNT(*) FROM rank_check_keywords WHERE is_active = 1"
        ).fetchone()[0]
    finally:
        conn2.close()

    yield {
        "type": "start",
        "total_branches": len(branches),
        "total_keywords": total_keywords,
    }

    checked = 0
    branch_idx = 0

    for b in branches:
        branch_idx += 1
        bid = b["branch_id"]
        bname = b["branch_name"]

        conn3 = get_conn(EQUIPMENT_DB)
        try:
            keywords = conn3.execute(
                "SELECT * FROM rank_check_keywords WHERE branch_id = ? AND is_active = 1",
                (bid,)
            ).fetchall()
            keywords = [dict(kw) for kw in keywords]
        finally:
            conn3.close()

        for kw in keywords:
            checked += 1
            search_kw = kw["search_keyword"] or kw["keyword"]

            yield {
                "type": "checking",
                "branch_idx": branch_idx,
                "branch_name": bname,
                "keyword": kw["keyword"],
                "checked": checked,
                "total_keywords": total_keywords,
            }

            try:
                rank = check_place_rank(search_kw, kw["place_id"])
                is_exposed = 1 if rank and rank <= (kw["guaranteed_rank"] or 5) else 0

                today = date.today().isoformat()
                conn4 = get_conn(EQUIPMENT_DB)
                try:
                    conn4.execute("""
                        INSERT OR REPLACE INTO rank_checks
                        (date, keyword_id, branch_id, branch_name, keyword, rank, is_exposed, checked_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (today, kw["id"], bid, bname, kw["keyword"], rank, is_exposed,
                          datetime.now().isoformat()))
                    conn4.commit()
                finally:
                    conn4.close()

                yield {
                    "type": "result",
                    "branch_name": bname,
                    "keyword": kw["keyword"],
                    "rank": rank,
                    "is_exposed": is_exposed,
                    "guaranteed_rank": kw["guaranteed_rank"],
                    "checked": checked,
                    "total_keywords": total_keywords,
                }
            except Exception as e:
                yield {
                    "type": "error",
                    "branch_name": bname,
                    "keyword": kw["keyword"],
                    "error": str(e),
                    "checked": checked,
                    "total_keywords": total_keywords,
                }

            time.sleep(0.5)

        yield {
            "type": "branch_done",
            "branch_idx": branch_idx,
            "branch_name": bname,
            "total_branches": len(branches),
        }

    yield {
        "type": "done",
        "total_branches": len(branches),
        "total_checked": checked,
    }


def get_branch_rank_history(branch_id: int, days: int = 30) -> list[dict]:
    """지점의 순위 체크 이력."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("""
            SELECT rc.date, rc.keyword, rc.rank, rc.is_exposed, rc.checked_at,
                   rck.guaranteed_rank, rck.place_id
            FROM rank_checks rc
            JOIN rank_check_keywords rck ON rc.keyword_id = rck.id
            WHERE rc.branch_id = ?
            ORDER BY rc.date DESC, rc.keyword
            LIMIT ?
        """, (branch_id, days * 10)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_comparison(branch_id: int, check_date: str = None) -> dict:
    """외주사 보고 vs SB체커 실측 비교.

    상태:
    - match:           둘 다 보고, 노출 일치
    - mismatch:        둘 다 보고, 노출 다름 (외주사 잘못 보고)
    - agency_missing:  SB는 측정, 외주사 보고 누락 (외주사 직무 태만)
    - checker_missing: 외주사는 보고, SB 미측정 (자동 측정 실패 또는 키워드 미등록)

    데이터 베이스는 place_daily — 단독 추적(origin='manual'이고 place_daily에 없는 것)은 비교 제외.
    """
    if not check_date:
        check_date = date.today().isoformat()

    conn = get_conn(EQUIPMENT_DB)
    try:
        # 외주사 보고 (place_daily) — 베이스
        agency = conn.execute("""
            SELECT keyword, is_exposed, rank FROM place_daily
            WHERE branch_id = ? AND date = ?
        """, (branch_id, check_date)).fetchall()
        agency_map = {r["keyword"]: dict(r) for r in agency}

        # SB체커 측정 (rank_checks JOIN rank_check_keywords)
        checker = conn.execute("""
            SELECT rc.keyword, rc.rank, rc.is_exposed, rck.guaranteed_rank
              FROM rank_checks rc
              JOIN rank_check_keywords rck ON rc.keyword_id = rck.id
             WHERE rc.branch_id = ? AND rc.date = ?
        """, (branch_id, check_date)).fetchall()
        checker_map = {r["keyword"]: dict(r) for r in checker}

        # 합집합 키워드 — 단, 단독 추적(origin='manual'+place_daily에 없는 것)은 제외
        all_keywords = set(agency_map.keys())
        # SB만 측정된 경우 (agency_missing)도 origin이 auto_synced인 것만 포함
        for kw, c in checker_map.items():
            if kw not in agency_map:
                # origin 검사
                row = conn.execute(
                    "SELECT origin FROM rank_check_keywords WHERE branch_id=? AND keyword=? LIMIT 1",
                    (branch_id, kw)
                ).fetchone()
                if row and row["origin"] == "auto_synced":
                    all_keywords.add(kw)

        comparisons = []
        counts = {"match": 0, "mismatch": 0, "agency_missing": 0, "checker_missing": 0}
        for kw in sorted(all_keywords):
            a = agency_map.get(kw)
            c = checker_map.get(kw)

            if a and c:
                state = "match" if a["is_exposed"] == c["is_exposed"] else "mismatch"
            elif c and not a:
                state = "agency_missing"
            elif a and not c:
                state = "checker_missing"
            else:
                continue
            counts[state] += 1

            comparisons.append({
                "keyword": kw,
                "agency": {"is_exposed": a["is_exposed"], "rank": a.get("rank")} if a else None,
                "checker": {"rank": c["rank"], "is_exposed": c["is_exposed"], "guaranteed_rank": c.get("guaranteed_rank")} if c else None,
                "state": state,
            })

        return {
            "date": check_date,
            "branch_id": branch_id,
            "comparisons": comparisons,
            "counts": counts,
            # 호환성: 기존 mismatch_count 유지
            "mismatch_count": counts["mismatch"],
        }
    finally:
        conn.close()
