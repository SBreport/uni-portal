"""지점명으로 네이버 플레이스 검색 → place_id 자동 매칭."""

import json
import logging
import time
from difflib import SequenceMatcher
from typing import Optional

from checker.place_rank import _fetch_place_page

logger = logging.getLogger(__name__)

# 자동 채택 임계값 (지점명 vs 검색 결과 업체명 유사도)
AUTO_THRESHOLD = 0.95
REVIEW_THRESHOLD = 0.70


def _similarity(a: str, b: str) -> float:
    """문자열 유사도 (0.0 ~ 1.0)."""
    return SequenceMatcher(None, a.strip(), b.strip()).ratio()


def find_place_id_for_branch(branch_name: str, alt_names: list[str] | None = None) -> dict:
    """지점명을 네이버 플레이스에 검색해 후보 place_id 추출.

    Args:
        branch_name: evt_branches.name (예: '유앤아이의원 강남점')
        alt_names: 대안 이름 (short_name, aliases 등). 첫 검색 결과 약하면 사용

    Returns:
        {
            "status": "matched" | "pending_review" | "manual_required",
            "best": {"place_id": str, "name": str, "score": float} | None,
            "candidates": [{"place_id", "name", "score"}, ...] (상위 3개),
            "search_keyword": 실제 사용된 검색어,
        }
    """
    keywords_to_try = [branch_name] + (alt_names or [])
    keywords_to_try = [k for k in keywords_to_try if k and k.strip()]

    best_result = None
    used_keyword = branch_name

    for kw in keywords_to_try:
        try:
            data = _fetch_place_page(kw, start=1)
        except Exception as e:
            logger.warning(f"place_id_finder: '{kw}' 검색 실패: {e}")
            continue

        items = data.get("data", {}).get("businesses", {}).get("items", [])
        if not items:
            continue

        # 상위 5개에 대해 유사도 계산
        candidates = []
        for item in items[:5]:
            pid = str(item.get("id", "")).strip()
            name = item.get("name", "")
            if not pid or not name:
                continue
            score = max(_similarity(branch_name, name), _similarity(kw, name))
            candidates.append({"place_id": pid, "name": name, "score": round(score, 3)})

        if candidates:
            candidates.sort(key=lambda c: c["score"], reverse=True)
            best = candidates[0]
            # 첫 키워드에서 자동 채택 가능하면 바로 반환
            if best["score"] >= AUTO_THRESHOLD:
                used_keyword = kw
                return {
                    "status": "matched",
                    "best": best,
                    "candidates": candidates[:3],
                    "search_keyword": kw,
                }
            # 더 좋은 후보군에 보관 (다른 alt_name도 시도해볼 가치)
            if best_result is None or best["score"] > best_result["best"]["score"]:
                best_result = {
                    "best": best,
                    "candidates": candidates[:3],
                    "search_keyword": kw,
                }

        time.sleep(0.5)  # 네이버 차단 대비

    if best_result is None:
        return {
            "status": "manual_required",
            "best": None,
            "candidates": [],
            "search_keyword": branch_name,
        }

    score = best_result["best"]["score"]
    if score >= AUTO_THRESHOLD:
        status = "matched"
    elif score >= REVIEW_THRESHOLD:
        status = "pending_review"
    else:
        status = "manual_required"

    return {
        "status": status,
        "best": best_result["best"],
        "candidates": best_result["candidates"],
        "search_keyword": best_result["search_keyword"],
    }


def auto_match_unregistered_branches(conn, dry_run: bool = False) -> dict:
    """default_place_id가 비어있는 지점 전체에 자동 매칭 시도.

    Args:
        conn: sqlite3 connection
        dry_run: True면 DB에 저장 안 하고 결과만 반환

    Returns:
        {
            "matched": [{branch_id, branch_name, place_id, matched_name, score, search_keyword}, ...],
            "pending_review": [{branch_id, branch_name, candidates: [...], search_keyword}, ...],
            "manual_required": [{branch_id, branch_name}, ...],
            "stats": {total, auto_matched, pending_review, manual_required},
        }
    """
    branches = conn.execute("""
        SELECT id, name, short_name, aliases FROM evt_branches
         WHERE is_active = 1
           AND (default_place_id IS NULL OR default_place_id = '')
         ORDER BY name
    """).fetchall()

    matched = []
    pending = []
    manual = []

    for b in branches:
        bid = b["id"]
        bname = b["name"]
        # alt_names: short_name, aliases JSON
        alts = []
        if b["short_name"]:
            alts.append(b["short_name"])
        # aliases는 JSON 배열일 수 있음
        try:
            aliases = json.loads(b["aliases"] or "[]")
            if isinstance(aliases, list):
                alts.extend([a for a in aliases if isinstance(a, str)])
        except Exception:
            pass

        result = find_place_id_for_branch(bname, alt_names=alts)

        if result["status"] == "matched":
            best = result["best"]
            matched.append({
                "branch_id": bid,
                "branch_name": bname,
                "place_id": best["place_id"],
                "matched_name": best["name"],
                "score": best["score"],
                "search_keyword": result["search_keyword"],
            })
            if not dry_run:
                _save_default_place_id(conn, bid, best["place_id"])
        elif result["status"] == "pending_review":
            pending.append({
                "branch_id": bid,
                "branch_name": bname,
                "candidates": result["candidates"],
                "search_keyword": result["search_keyword"],
            })
        else:
            manual.append({
                "branch_id": bid,
                "branch_name": bname,
            })

        time.sleep(0.5)

    return {
        "matched": matched,
        "pending_review": pending,
        "manual_required": manual,
        "stats": {
            "total": len(branches),
            "auto_matched": len(matched),
            "pending_review": len(pending),
            "manual_required": len(manual),
        },
    }


def _save_default_place_id(conn, branch_id: int, place_id: str) -> dict:
    """evt_branches.default_place_id 저장 + 해당 지점 키워드 일괄 활성화.

    is_active=0 + place_id='' 인 rank_check_keywords row를:
    - place_id를 default_place_id로 채움
    - is_active=1 로 갱신
    """
    conn.execute(
        "UPDATE evt_branches SET default_place_id = ? WHERE id = ?",
        (place_id, branch_id)
    )
    activated = conn.execute("""
        UPDATE rank_check_keywords
           SET place_id = ?, is_active = 1
         WHERE branch_id = ?
           AND is_active = 0
           AND (place_id IS NULL OR place_id = '')
    """, (place_id, branch_id)).rowcount
    conn.commit()
    return {"branch_id": branch_id, "activated_keywords": activated}


def save_place_ids_bulk(conn, items: list[dict]) -> dict:
    """admin이 화면에서 확정한 [{branch_id, place_id}] 일괄 저장.

    각 항목마다 _save_default_place_id 호출. 빈 place_id는 skip.
    """
    saved = 0
    total_activated = 0
    for it in items:
        bid = it.get("branch_id")
        pid = (it.get("place_id") or "").strip()
        if not bid or not pid:
            continue
        r = _save_default_place_id(conn, bid, pid)
        saved += 1
        total_activated += r.get("activated_keywords", 0)
    return {"saved": saved, "activated_keywords": total_activated}
