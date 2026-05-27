"""Equipment 정리 도구 라우터 (admin only).

- GET  /admin/equipment-cleanup/duplicates              : 중복 그룹 목록
- GET  /admin/equipment-cleanup/summary                 : 요약 통계
- POST /admin/equipment-cleanup/merge                   : 중복 row 통합
- POST /admin/equipment-cleanup/remap                   : device_info_id 재매핑
- GET  /admin/equipment-cleanup/auto-merge-preview      : 자동 통합 가능 그룹 미리보기
- POST /admin/equipment-cleanup/auto-merge-execute      : 자동 통합 일괄 실행
- GET  /admin/equipment-cleanup/new-master-candidates   : 신규 마스터 후보 발굴
- POST /admin/equipment-cleanup/register-new-masters    : 신규 마스터 일괄 등록
"""

import re
import sqlite3
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import require_role
from shared.db import get_conn, EQUIPMENT_DB

router = APIRouter(prefix="/admin/equipment-cleanup", tags=["EquipmentCleanup"])
_admin = require_role("admin")


# ── 헬퍼 ────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    return get_conn(EQUIPMENT_DB)


def normalize_name(name: str) -> str:
    """이름 정규화: prefix 제거, 공백 통일, 보이지 않는 문자 제거.

    - prefix 제거: "1. ", "2. ", "[1]", "(1)" 등
    - 연속 공백 → 1개
    - zero-width space 등 보이지 않는 문자 제거
    """
    if not name:
        return name
    # prefix 숫자 제거: "1. ", "2. ", "[1]", "(1)", "①" 등
    name = re.sub(r'^[\[\(]?\d+[\]\)]?\.?\s*', '', name)
    # zero-width space, BOM, soft hyphen 등 제거
    name = re.sub(r'[​‌‍﻿­]', '', name)
    # 연속 공백 → 1개 + 양쪽 strip
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_variant(name: str) -> Optional[str]:
    """equipment.name에서 괄호 안 변형 정보 추출.

    - 앞 괄호: '(나보타)보톡스' → '나보타'
    - 뒤 괄호: '보톡스(메디톡신)' → '메디톡신'
    - prefix 숫자 무시: '2. 보톡스(메디톡신)' → '메디톡신'
    - 슬래시 포함 (묶음): '케어7(비타/소노/크라)' → '비타/소노/크라' (그대로 반환)
    - 괄호 없으면 None
    """
    if not name:
        return None
    matches = re.findall(r'\(([^)]+)\)', name)
    if matches:
        return matches[-1].strip()
    return None


def _build_variant_summary(variants: list[Optional[str]]) -> dict:
    """variant 목록에서 요약 정보 생성."""
    counts: dict[str, int] = {}
    for v in variants:
        key = v if v is not None else "미명시"
        counts[key] = counts.get(key, 0) + 1
    distinct = len(counts)
    # 표시: "메디톡신 ×2 · 제오민 · 미명시" 형식 리스트
    items = [
        {"variant": k, "count": c}
        for k, c in sorted(counts.items(), key=lambda x: -x[1])
    ]
    return {
        "distinct_count": distinct,
        "items": items,
    }


# ── GET /summary ─────────────────────────────────────────────────────────────

@router.get("/summary")
async def get_cleanup_summary(user: Annotated[dict, Depends(_admin)]):
    """요약 통계: 중복 그룹 수, NULL 매핑 수."""
    conn = _conn()
    try:
        dup_groups = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT branch_id, device_info_id
                FROM equipment
                WHERE device_info_id IS NOT NULL
                GROUP BY branch_id, device_info_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        null_count = conn.execute(
            "SELECT COUNT(*) FROM equipment WHERE device_info_id IS NULL"
        ).fetchone()[0]

        dup_rows = conn.execute("""
            SELECT COALESCE(SUM(cnt - 1), 0) FROM (
                SELECT COUNT(*) as cnt
                FROM equipment
                WHERE device_info_id IS NOT NULL
                GROUP BY branch_id, device_info_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        return {
            "duplicate_groups": dup_groups,
            "duplicate_excess_rows": dup_rows,
            "null_mapping": null_count,
        }
    finally:
        conn.close()


# ── GET /duplicates ──────────────────────────────────────────────────────────

@router.get("/duplicates")
async def get_duplicates(
    user: Annotated[dict, Depends(_admin)],
    branch_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    """중복 그룹 목록 (페이지네이션).

    같은 (branch_id, device_info_id)를 가진 equipment row가 2개 이상인 그룹.
    """
    conn = _conn()
    try:
        offset = (page - 1) * page_size

        branch_filter = "AND e.branch_id = :branch_id" if branch_id else ""

        # 중복 그룹 키 목록 (페이지네이션)
        # 카테고리는 시트 권위 (categories 8종, primary_category_id 경유)
        group_rows = conn.execute(f"""
            SELECT e.branch_id, b.name AS branch_name,
                   e.device_info_id,
                   di.name AS device_info_name,
                   pc.name AS category_name,
                   COUNT(*) AS row_count,
                   SUM(e.quantity) AS total_qty
            FROM equipment e
            JOIN branches b ON e.branch_id = b.id
            LEFT JOIN device_info di ON e.device_info_id = di.id
            LEFT JOIN categories pc ON di.primary_category_id = pc.id
            WHERE e.device_info_id IS NOT NULL
            {branch_filter}
            GROUP BY e.branch_id, e.device_info_id
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC, b.name, di.name
            LIMIT :limit OFFSET :offset
        """, {"branch_id": branch_id, "limit": page_size, "offset": offset}).fetchall()

        # 전체 건수
        total_row = conn.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT branch_id, device_info_id
                FROM equipment e
                WHERE device_info_id IS NOT NULL
                {branch_filter}
                GROUP BY branch_id, device_info_id
                HAVING COUNT(*) > 1
            )
        """, {"branch_id": branch_id} if branch_id else {}).fetchone()
        total = total_row[0] if total_row else 0

        # 각 그룹의 세부 row 조회
        result = []
        for g in group_rows:
            rows = conn.execute("""
                SELECT e.id, e.name, e.quantity, e.source, e.note,
                       e.device_info_id, e.created_at, e.updated_at
                FROM equipment e
                WHERE e.branch_id = ? AND e.device_info_id = ?
                ORDER BY e.id
            """, (g["branch_id"], g["device_info_id"])).fetchall()

            serialized_rows = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "qty": r["quantity"],
                    "source": r["source"] or "sheets",
                    "note": r["note"] or "",
                    "created_at": r["created_at"],
                    "variant": extract_variant(r["name"] or ""),
                }
                for r in rows
            ]
            variant_summary = _build_variant_summary(
                [row["variant"] for row in serialized_rows]
            )

            result.append({
                "branch_id": g["branch_id"],
                "branch_name": g["branch_name"],
                "device_info_id": g["device_info_id"],
                "device_info_name": g["device_info_name"],
                "category_name": g["category_name"],
                "row_count": g["row_count"],
                "total_qty": g["total_qty"],
                "variant_summary": variant_summary,
                "rows": serialized_rows,
            })

        return {
            "groups": result,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        }
    finally:
        conn.close()


# ── POST /merge ──────────────────────────────────────────────────────────────

class MergeRequest(BaseModel):
    branch_id: int
    device_info_id: int
    target_row_id: int
    source_row_ids: list[int]
    new_name: Optional[str] = None


@router.post("/merge")
async def merge_equipment(
    body: MergeRequest,
    user: Annotated[dict, Depends(_admin)],
):
    """중복 row 통합.

    1. source_row들의 qty 합산 → target_row.quantity에 반영
    2. new_name 있으면 target_row.name 변경
    3. source_row들 DELETE
    4. 트랜잭션 보장
    """
    if not body.source_row_ids:
        raise HTTPException(400, "source_row_ids가 비어 있습니다.")
    if body.target_row_id in body.source_row_ids:
        raise HTTPException(400, "target_row_id는 source_row_ids에 포함될 수 없습니다.")

    conn = _conn()
    try:
        # target row 존재 확인
        target = conn.execute(
            "SELECT id, name, quantity, branch_id, device_info_id FROM equipment WHERE id = ?",
            (body.target_row_id,),
        ).fetchone()
        if not target:
            raise HTTPException(404, f"target_row_id={body.target_row_id} 를 찾을 수 없습니다.")

        if target["branch_id"] != body.branch_id or target["device_info_id"] != body.device_info_id:
            raise HTTPException(
                400,
                "target row의 branch_id / device_info_id가 요청값과 다릅니다."
            )

        # source row들 qty 합산
        placeholders = ",".join("?" * len(body.source_row_ids))
        sources = conn.execute(
            f"SELECT id, quantity, branch_id, device_info_id FROM equipment WHERE id IN ({placeholders})",
            body.source_row_ids,
        ).fetchall()

        if len(sources) != len(body.source_row_ids):
            found_ids = {r["id"] for r in sources}
            missing = [i for i in body.source_row_ids if i not in found_ids]
            raise HTTPException(404, f"source_row_ids 중 찾을 수 없는 id: {missing}")

        for s in sources:
            if s["branch_id"] != body.branch_id or s["device_info_id"] != body.device_info_id:
                raise HTTPException(
                    400,
                    f"source row id={s['id']}의 branch_id / device_info_id가 요청값과 다릅니다."
                )

        source_qty_total = sum(s["quantity"] for s in sources)
        new_qty = target["quantity"] + source_qty_total
        new_name = (body.new_name or "").strip() or target["name"]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 트랜잭션 시작
        conn.execute("BEGIN")

        # target 업데이트
        conn.execute(
            "UPDATE equipment SET quantity = ?, name = ?, updated_at = ? WHERE id = ?",
            (new_qty, new_name, now, body.target_row_id),
        )

        # source 삭제
        conn.execute(
            f"DELETE FROM equipment WHERE id IN ({placeholders})",
            body.source_row_ids,
        )

        conn.execute("COMMIT")

        return {
            "success": True,
            "target_id": body.target_row_id,
            "merged_count": len(body.source_row_ids),
            "new_qty": new_qty,
            "new_name": new_name,
        }

    except HTTPException:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise HTTPException(500, f"통합 실패: {str(e)}")
    finally:
        conn.close()


# ── POST /remap ──────────────────────────────────────────────────────────────

class RemapRequest(BaseModel):
    branch_id: Optional[int] = None
    force: bool = False


@router.post("/remap")
async def remap_equipment(
    body: RemapRequest,
    user: Annotated[dict, Depends(_admin)],
):
    """device_info_id 재매핑.

    - force=False (기본): device_info_id IS NULL인 row만 재매핑
    - force=True: 전체 re-run (현재 매핑 덮어씌움)
    """
    from equipment.matcher import match_single

    conn = _conn()
    try:
        # 대상 row 조회
        if body.force:
            where = "WHERE 1=1"
        else:
            where = "WHERE e.device_info_id IS NULL"

        branch_clause = "AND e.branch_id = ?" if body.branch_id else ""
        params: list = []
        if body.branch_id:
            params.append(body.branch_id)

        rows = conn.execute(
            f"SELECT id, name FROM equipment {where} {branch_clause}",
            params,
        ).fetchall()

        if not rows:
            return {"remapped_count": 0, "unmatched_count": 0}

        # device_info 전체 로드 (매번 DB 쿼리 대신 캐시)
        device_list = [
            dict(r) for r in conn.execute(
                "SELECT * FROM device_info ORDER BY usage_count DESC, name"
            ).fetchall()
        ]

        remapped = 0
        unmatched = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("BEGIN")
        for row in rows:
            dev_id, _ = match_single(row["name"], device_list)
            if dev_id is not None:
                conn.execute(
                    "UPDATE equipment SET device_info_id = ?, updated_at = ? WHERE id = ?",
                    (dev_id, now, row["id"]),
                )
                remapped += 1
            else:
                unmatched += 1
        conn.execute("COMMIT")

        return {
            "remapped_count": remapped,
            "unmatched_count": unmatched,
            "total_processed": len(rows),
        }

    except HTTPException:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise HTTPException(500, f"재매핑 실패: {str(e)}")
    finally:
        conn.close()


# ── 자동 통합 헬퍼 ────────────────────────────────────────────────────────────

def _build_auto_merge_groups(conn: sqlite3.Connection) -> list[dict]:
    """자동 통합 가능한 그룹을 Tier 1/2/3 기준으로 반환.

    반환값 각 항목:
      tier, branch_id, branch_name, device_info_id, device_info_name,
      row_ids (list[int]), qtys (list[int]), names (list[str]),
      merged_name (정규화 후 대표 이름), total_qty
    """
    # 중복 그룹의 모든 row 조회
    raw_rows = conn.execute("""
        SELECT e.id, e.branch_id, b.name AS branch_name,
               e.device_info_id, di.name AS device_info_name,
               e.name, e.quantity, e.source
        FROM equipment e
        JOIN branches b ON e.branch_id = b.id
        LEFT JOIN device_info di ON e.device_info_id = di.id
        WHERE e.device_info_id IS NOT NULL
        ORDER BY e.branch_id, e.device_info_id, e.id
    """).fetchall()

    # (branch_id, device_info_id) → list of rows
    from collections import defaultdict
    bucket: dict = defaultdict(list)
    for r in raw_rows:
        bucket[(r["branch_id"], r["device_info_id"])].append(dict(r))

    groups = []
    for (branch_id, device_info_id), rows in bucket.items():
        if len(rows) < 2:
            continue

        branch_name = rows[0]["branch_name"]
        device_info_name = rows[0]["device_info_name"] or ""

        # 이름 정규화
        norm_names = [normalize_name(r["name"] or "") for r in rows]
        variants = [extract_variant(r["name"] or "") for r in rows]

        # Tier 1: 원본 이름이 모두 동일
        if len(set(r["name"] for r in rows)) == 1:
            groups.append({
                "tier": 1,
                "branch_id": branch_id,
                "branch_name": branch_name,
                "device_info_id": device_info_id,
                "device_info_name": device_info_name,
                "row_ids": [r["id"] for r in rows],
                "qtys": [r["quantity"] for r in rows],
                "names": [r["name"] for r in rows],
                "merged_name": rows[0]["name"],
                "total_qty": sum(r["quantity"] for r in rows),
            })
            continue

        # Tier 2: 정규화 후 이름이 모두 동일, variant 모두 None
        if all(v is None for v in variants) and len(set(norm_names)) == 1:
            groups.append({
                "tier": 2,
                "branch_id": branch_id,
                "branch_name": branch_name,
                "device_info_id": device_info_id,
                "device_info_name": device_info_name,
                "row_ids": [r["id"] for r in rows],
                "qtys": [r["quantity"] for r in rows],
                "names": [r["name"] for r in rows],
                "merged_name": norm_names[0],
                "total_qty": sum(r["quantity"] for r in rows),
            })
            continue

        # Tier 3: variant 모두 동일 (None 포함)
        if len(set(v for v in variants)) == 1:
            # 정규화된 대표 이름: source='sheets' 우선, 없으면 가장 작은 id
            sorted_rows = sorted(rows, key=lambda r: (0 if r["source"] == "sheets" else 1, r["id"]))
            groups.append({
                "tier": 3,
                "branch_id": branch_id,
                "branch_name": branch_name,
                "device_info_id": device_info_id,
                "device_info_name": device_info_name,
                "row_ids": [r["id"] for r in rows],
                "qtys": [r["quantity"] for r in rows],
                "names": [r["name"] for r in rows],
                "merged_name": normalize_name(sorted_rows[0]["name"] or ""),
                "total_qty": sum(r["quantity"] for r in rows),
            })

    return groups


# ── GET /auto-merge-preview ───────────────────────────────────────────────────

@router.get("/auto-merge-preview")
async def get_auto_merge_preview(
    user: Annotated[dict, Depends(_admin)],
    page: int = 1,
    page_size: int = 50,
):
    """자동 통합 가능 그룹 미리보기.

    Tier 1/2/3 기준으로 자동 처리 가능한 그룹과 건수를 반환.
    """
    conn = _conn()
    try:
        all_groups = _build_auto_merge_groups(conn)

        tier1 = [g for g in all_groups if g["tier"] == 1]
        tier2 = [g for g in all_groups if g["tier"] == 2]
        tier3 = [g for g in all_groups if g["tier"] == 3]

        total = len(all_groups)
        total_affected_rows = sum(len(g["row_ids"]) for g in all_groups)

        # 페이지네이션
        offset = (page - 1) * page_size
        paged_groups = all_groups[offset: offset + page_size]

        # 직렬화
        serialized = [
            {
                "tier": g["tier"],
                "branch_name": g["branch_name"],
                "device_info_name": g["device_info_name"],
                "name": g["merged_name"],
                "row_ids": g["row_ids"],
                "names": g["names"],
                "qtys": g["qtys"],
                "total_qty": g["total_qty"],
            }
            for g in paged_groups
        ]

        return {
            "tier1_count": len(tier1),
            "tier2_count": len(tier2),
            "tier3_count": len(tier3),
            "total": total,
            "total_affected_rows": total_affected_rows,
            "page": page,
            "page_size": page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
            "groups": serialized,
        }
    finally:
        conn.close()


# ── POST /auto-merge-execute ──────────────────────────────────────────────────

class AutoMergeRequest(BaseModel):
    tiers: list[int]  # 처리할 tier 목록 (예: [1, 2, 3])


@router.post("/auto-merge-execute")
async def auto_merge_execute(
    body: AutoMergeRequest,
    user: Annotated[dict, Depends(_admin)],
):
    """자동 통합 일괄 실행.

    지정한 tier(들)에 해당하는 모든 자동 통합 가능 그룹을 단일 트랜잭션 안에서 처리.
    - target_row: source='sheets' 우선, 동점이면 가장 작은 id
    - target.quantity = 그룹 전체 qty 합산
    - target.name = merged_name (정규화된 대표 이름)
    - source rows DELETE
    """
    if not body.tiers:
        raise HTTPException(400, "tiers가 비어 있습니다.")
    invalid = [t for t in body.tiers if t not in (1, 2, 3)]
    if invalid:
        raise HTTPException(400, f"유효하지 않은 tier: {invalid}")

    conn = _conn()
    try:
        all_groups = _build_auto_merge_groups(conn)
        target_groups = [g for g in all_groups if g["tier"] in body.tiers]

        if not target_groups:
            return {
                "merged_groups": 0,
                "deleted_rows": 0,
                "total_qty_consolidated": 0,
            }

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("BEGIN")
        merged_groups = 0
        deleted_rows = 0
        total_qty_consolidated = 0

        for g in target_groups:
            row_ids = g["row_ids"]
            if len(row_ids) < 2:
                continue

            # target row 결정: source='sheets' 우선, 동점이면 최소 id
            rows_detail = conn.execute(
                f"SELECT id, source, quantity FROM equipment WHERE id IN ({','.join('?' * len(row_ids))})",
                row_ids,
            ).fetchall()

            # source='sheets' 우선 정렬
            sorted_rows = sorted(rows_detail, key=lambda r: (0 if r["source"] == "sheets" else 1, r["id"]))
            target_id = sorted_rows[0]["id"]
            source_ids = [r["id"] for r in sorted_rows[1:]]

            total_qty = sum(r["quantity"] for r in rows_detail)
            merged_name = g["merged_name"] or (
                conn.execute("SELECT name FROM equipment WHERE id = ?", (target_id,)).fetchone()["name"]
            )

            # target 업데이트
            conn.execute(
                "UPDATE equipment SET quantity = ?, name = ?, updated_at = ? WHERE id = ?",
                (total_qty, merged_name, now, target_id),
            )

            # source 삭제
            conn.execute(
                f"DELETE FROM equipment WHERE id IN ({','.join('?' * len(source_ids))})",
                source_ids,
            )

            merged_groups += 1
            deleted_rows += len(source_ids)
            total_qty_consolidated += total_qty

        conn.execute("COMMIT")

        return {
            "merged_groups": merged_groups,
            "deleted_rows": deleted_rows,
            "total_qty_consolidated": total_qty_consolidated,
        }

    except HTTPException:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise HTTPException(500, f"자동 통합 실패: {str(e)}")
    finally:
        conn.close()


# ── 신규 마스터 후보 발굴 헬퍼 ───────────────────────────────────────────────

def _strip_variant(name: str) -> str:
    """괄호(변형 정보) 제거 후 base name 반환."""
    return re.sub(r'\([^)]+\)', '', name).strip()


def _find_misplaced_in_groups(conn: sqlite3.Connection) -> list[dict]:
    """Tier 1: 같은 device_info 그룹 안에서 이름이 매핑 마스터와 관계 없는 outlier 검출.

    조건:
    - base_name(변형 제거 + 정규화)이 device_info.name과 substring 관계 없음
    - 같은 그룹의 다른 row 이름과도 substring 관계 없음
    """
    from collections import defaultdict

    # 전체 device_info 이름 맵
    di_map: dict[int, dict] = {
        r["id"]: dict(r)
        for r in conn.execute("SELECT * FROM device_info").fetchall()
    }

    # categories 맵
    cat_map: dict[int, str] = {
        r["id"]: r["name"]
        for r in conn.execute("SELECT id, name FROM categories").fetchall()
    }

    rows = conn.execute("""
        SELECT e.id, e.name, e.quantity, e.device_info_id, e.branch_id,
               b.name AS branch_name
        FROM equipment e
        JOIN branches b ON e.branch_id = b.id
        WHERE e.device_info_id IS NOT NULL
        ORDER BY e.device_info_id, e.branch_id
    """).fetchall()

    # (device_info_id, branch_id) → list
    bucket: dict = defaultdict(list)
    for r in rows:
        bucket[(r["device_info_id"], r["branch_id"])].append(dict(r))

    # name → candidate 축적 (중복 방지: 같은 이름은 하나로)
    candidates: dict[str, dict] = {}

    for (di_id, branch_id), group in bucket.items():
        di = di_map.get(di_id)
        if not di:
            continue
        di_name = di["name"] or ""
        di_name_lower = di_name.lower().replace(" ", "")

        for row in group:
            raw = row["name"] or ""
            norm = normalize_name(raw)
            base = _strip_variant(norm).lower().replace(" ", "")

            if not base or not di_name_lower:
                continue

            # substring 관계 확인
            if di_name_lower in base or base in di_name_lower:
                continue

            # 이 이름이 이미 후보에 있으면 지점/row 정보만 추가
            key = norm
            if key not in candidates:
                # 추천 카테고리: di의 primary_category_id 사용
                suggested_cat_id = di.get("primary_category_id")
                suggested_cat = cat_map.get(suggested_cat_id, "") if suggested_cat_id else ""

                candidates[key] = {
                    "name": norm,
                    "normalized_name": norm,
                    "current_di_id": di_id,
                    "current_di_name": di_name,
                    "branches": [],
                    "row_ids": [],
                    "total_qty": 0,
                    "suggested_category": suggested_cat,
                    "suggested_primary_category_id": suggested_cat_id,
                }

            c = candidates[key]
            branch_name = row["branch_name"]
            if branch_name not in c["branches"]:
                c["branches"].append(branch_name)
            c["row_ids"].append(row["id"])
            c["total_qty"] += row["quantity"]

    return list(candidates.values())


def _find_unmapped_frequent(conn: sqlite3.Connection, min_count: int = 2) -> list[dict]:
    """Tier 2: device_info_id IS NULL이면서 min_count회 이상 등장하는 이름."""
    cat_map: dict[int, str] = {
        r["id"]: r["name"]
        for r in conn.execute("SELECT id, name FROM categories").fetchall()
    }

    rows = conn.execute("""
        SELECT e.name, e.id, e.quantity, e.branch_id, e.category_id,
               b.name AS branch_name
        FROM equipment e
        JOIN branches b ON e.branch_id = b.id
        WHERE e.device_info_id IS NULL
        ORDER BY e.name
    """).fetchall()

    from collections import defaultdict
    name_bucket: dict[str, list] = defaultdict(list)
    for r in rows:
        norm = normalize_name(r["name"] or "")
        if norm:
            name_bucket[norm].append(dict(r))

    candidates = []
    for norm_name, group in name_bucket.items():
        if len(group) < min_count:
            continue

        # 추천 카테고리: equipment.category_id 다수결
        cat_votes: dict[int, int] = defaultdict(int)
        for row in group:
            if row.get("category_id"):
                cat_votes[row["category_id"]] += 1
        suggested_cat_id = max(cat_votes, key=cat_votes.get) if cat_votes else None
        suggested_cat = cat_map.get(suggested_cat_id, "") if suggested_cat_id else ""

        branches = list({row["branch_name"] for row in group})
        candidates.append({
            "name": norm_name,
            "normalized_name": norm_name,
            "current_di_id": None,
            "current_di_name": None,
            "branches": branches,
            "row_ids": [row["id"] for row in group],
            "total_qty": sum(row["quantity"] for row in group),
            "suggested_category": suggested_cat,
            "suggested_primary_category_id": suggested_cat_id,
        })

    # 등장 빈도 내림차순
    candidates.sort(key=lambda c: -len(c["row_ids"]))
    return candidates


# ── GET /new-master-candidates ────────────────────────────────────────────────

@router.get("/new-master-candidates")
async def get_new_master_candidates(
    user: Annotated[dict, Depends(_admin)],
):
    """신규 마스터 후보 발굴.

    - Tier 1: 잘못 매핑된 outlier (같은 device_info 그룹 안에서 이름이 다른 row)
    - Tier 2: device_info_id NULL 중 2회 이상 등장하는 이름
    """
    conn = _conn()
    try:
        tier1 = _find_misplaced_in_groups(conn)
        tier2 = _find_unmapped_frequent(conn, min_count=2)
        return {
            "tier1_candidates": tier1,
            "tier2_candidates": tier2,
            "total_candidates": len(tier1) + len(tier2),
        }
    finally:
        conn.close()


# ── POST /register-new-masters ────────────────────────────────────────────────

class NewMasterItem(BaseModel):
    name: str
    category: str = ""
    summary: str = ""
    target: str = ""
    mechanism: str = ""
    aliases: str = ""
    device_type: str = "equipment"
    primary_category_id: Optional[int] = None
    # row_ids: 이 마스터로 재매핑할 equipment row id 목록
    row_ids: list[int] = []


class RegisterNewMastersRequest(BaseModel):
    candidates: list[NewMasterItem]


@router.post("/register-new-masters")
async def register_new_masters(
    body: RegisterNewMastersRequest,
    user: Annotated[dict, Depends(_admin)],
):
    """신규 마스터 일괄 등록.

    1. device_info에 신규 row INSERT (각 후보)
    2. equipment.device_info_id 재매핑 (row_ids를 새 마스터로)
    3. 전체 트랜잭션
    """
    if not body.candidates:
        raise HTTPException(400, "candidates가 비어 있습니다.")

    conn = _conn()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 중복 이름 사전 확인
        existing = {
            r["name"]
            for r in conn.execute("SELECT name FROM device_info").fetchall()
        }
        duplicates = [c.name for c in body.candidates if c.name in existing]
        if duplicates:
            raise HTTPException(
                400,
                f"이미 존재하는 마스터 이름: {duplicates}. 등록 전 이름을 변경하세요."
            )

        conn.execute("BEGIN")
        inserted = 0
        remapped = 0

        for item in body.candidates:
            name = item.name.strip()
            if not name:
                continue

            # device_info INSERT
            cursor = conn.execute(
                """
                INSERT INTO device_info
                    (name, category, summary, target, mechanism, aliases,
                     device_type, primary_category_id, usage_count,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    name,
                    item.category,
                    item.summary,
                    item.target,
                    item.mechanism,
                    item.aliases,
                    item.device_type,
                    item.primary_category_id,
                    now,
                    now,
                ),
            )
            new_di_id = cursor.lastrowid
            inserted += 1

            # equipment rows 재매핑
            if item.row_ids:
                placeholders = ",".join("?" * len(item.row_ids))
                conn.execute(
                    f"UPDATE equipment SET device_info_id = ?, updated_at = ? WHERE id IN ({placeholders})",
                    [new_di_id, now, *item.row_ids],
                )
                remapped += len(item.row_ids)

        conn.execute("COMMIT")
        return {
            "inserted": inserted,
            "remapped": remapped,
        }

    except HTTPException:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise HTTPException(500, f"신규 마스터 등록 실패: {str(e)}")
    finally:
        conn.close()
