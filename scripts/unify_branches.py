"""지점 테이블 통합 마이그레이션.

branches(장비 출처)와 evt_branches(이벤트 출처)를 통합한다.
evt_branches를 마스터로 삼고, equipment.branch_id를 evt_branches 기준으로 재매핑.

변경 사항:
  1. 퍙택점(오타) → 평택점으로 수정 (branches 테이블)
  2. equipment.branch_id를 evt_branches.id로 재매핑
     (branches.name = evt_branches.name 기준)
  3. equipment 테이블에 evt_branch_id 컬럼 추가 (새 FK)

사용법:
  python scripts/unify_branches.py --dry-run   # 미리보기
  python scripts/unify_branches.py              # 실제 적용
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.db import get_conn, EQUIPMENT_DB


def unify_branches(dry_run: bool = True) -> dict:
    conn = get_conn(EQUIPMENT_DB)

    # ── 1. 현황 파악 ──
    branches = conn.execute("SELECT id, name FROM branches ORDER BY name").fetchall()
    evt_branches = conn.execute("SELECT id, name FROM evt_branches ORDER BY name").fetchall()

    br_name_to_id = {r[1]: r[0] for r in branches}
    eb_name_to_id = {r[1]: r[0] for r in evt_branches}

    print(f"branches: {len(branches)}건, evt_branches: {len(evt_branches)}건")

    # ── 2. 오타 수정: 퍙택점 → 평택점 ──
    typo_fix = None
    if "퍙택점" in br_name_to_id and "평택점" not in br_name_to_id:
        typo_fix = ("퍙택점", "평택점", br_name_to_id["퍙택점"])
        print(f"  오타 수정: 퍙택점(id={typo_fix[2]}) → 평택점")
        if not dry_run:
            conn.execute("UPDATE branches SET name = ? WHERE id = ?", ("평택점", typo_fix[2]))
            br_name_to_id["평택점"] = br_name_to_id.pop("퍙택점")

    # ── 3. branches → evt_branches 매핑 테이블 구축 ──
    mapping = {}  # branches.id → evt_branches.id
    unmapped = []

    for br_name, br_id in br_name_to_id.items():
        if br_name in eb_name_to_id:
            mapping[br_id] = eb_name_to_id[br_name]
        else:
            unmapped.append((br_name, br_id))

    print(f"  매핑 성공: {len(mapping)}/{len(br_name_to_id)}")
    if unmapped:
        print(f"  매핑 실패: {unmapped}")

    # ── 4. equipment 테이블에 evt_branch_id 컬럼 추가 ──
    try:
        conn.execute("ALTER TABLE equipment ADD COLUMN evt_branch_id INTEGER")
        print("  equipment.evt_branch_id 컬럼 추가")
    except Exception:
        print("  equipment.evt_branch_id 컬럼 이미 존재")

    # ── 5. equipment.evt_branch_id 업데이트 ──
    equip_rows = conn.execute("SELECT id, branch_id FROM equipment").fetchall()
    updated = 0
    skipped = 0

    for equip_id, old_branch_id in equip_rows:
        if old_branch_id in mapping:
            new_id = mapping[old_branch_id]
            if not dry_run:
                conn.execute(
                    "UPDATE equipment SET evt_branch_id = ? WHERE id = ?",
                    (new_id, equip_id)
                )
            updated += 1
        else:
            skipped += 1

    print(f"  equipment 재매핑: {updated}건 성공, {skipped}건 스킵")

    # ── 6. 검증: evt_branch_id가 설정된 장비의 지점명 일치 확인 ──
    if not dry_run:
        conn.commit()
        mismatches = conn.execute("""
            SELECT e.id, b.name as old_name, eb.name as new_name
            FROM equipment e
            JOIN branches b ON e.branch_id = b.id
            JOIN evt_branches eb ON e.evt_branch_id = eb.id
            WHERE b.name != eb.name
        """).fetchall()
        if mismatches:
            print(f"\n  경고: 이름 불일치 {len(mismatches)}건!")
            for m in mismatches[:5]:
                print(f"    equipment#{m[0]}: {m[1]} ≠ {m[2]}")
        else:
            print(f"  검증 완료: 이름 불일치 0건")

    if dry_run:
        print(f"\n[DRY RUN] 실제 변경 없음.")
    else:
        print(f"\n적용 완료.")

    conn.close()
    return {"mapped": updated, "skipped": skipped, "typo_fixed": typo_fix is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="지점 테이블 통합")
    parser.add_argument("--dry-run", action="store_true", default=False)
    args = parser.parse_args()
    unify_branches(dry_run=args.dry_run)
