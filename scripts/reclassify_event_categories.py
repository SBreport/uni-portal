"""기존 이벤트 아이템의 카테고리 재분류 마이그레이션.

기타(category_id=16)로 분류된 아이템들을 category_map.json 규칙으로
재분류한다. 실행 전 --dry-run으로 결과를 먼저 확인할 수 있다.

사용법:
  python scripts/reclassify_event_categories.py --dry-run   # 미리보기
  python scripts/reclassify_event_categories.py              # 실제 적용
"""

import sys
import os
import argparse

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_conn, EQUIPMENT_DB
from events.normalizer import CategoryNormalizer


def reclassify(dry_run: bool = True) -> dict:
    """기타 카테고리 아이템을 재분류."""
    conn = get_conn(EQUIPMENT_DB)
    normalizer = CategoryNormalizer()

    # 표준 카테고리명 → id 매핑
    categories = conn.execute("SELECT id, name FROM evt_categories").fetchall()
    cat_name_to_id = {row[1]: row[0] for row in categories}
    cat_id_to_name = {row[0]: row[1] for row in categories}

    # 기타(16)에 속한 아이템 조회
    etc_id = cat_name_to_id.get("기타", 16)
    items = conn.execute(
        "SELECT id, raw_category, raw_event_name FROM evt_items WHERE category_id = ?",
        (etc_id,)
    ).fetchall()

    print(f"기타 아이템 총 {len(items)}건 검사 중...")

    # 재분류 결과 집계
    reclassified = {}  # category_name → [(item_id, raw_category), ...]
    still_etc = []
    errors = []

    for item_id, raw_cat, raw_name in items:
        if not raw_cat:
            still_etc.append((item_id, raw_cat))
            continue

        new_cat_name = normalizer.normalize(raw_cat)

        if new_cat_name == "기타":
            still_etc.append((item_id, raw_cat))
            continue

        new_cat_id = cat_name_to_id.get(new_cat_name)
        if new_cat_id is None:
            errors.append(f"표준 카테고리 '{new_cat_name}'이 DB에 없음 (raw: {raw_cat})")
            still_etc.append((item_id, raw_cat))
            continue

        reclassified.setdefault(new_cat_name, [])
        reclassified[new_cat_name].append((item_id, new_cat_id, raw_cat))

    # 결과 출력
    total_reclassified = sum(len(v) for v in reclassified.values())
    print(f"\n=== 재분류 결과 ===")
    print(f"  재분류 성공: {total_reclassified}/{len(items)} ({round(total_reclassified/len(items)*100, 1) if items else 0}%)")
    print(f"  여전히 기타: {len(still_etc)}")
    print(f"  오류: {len(errors)}")
    print()

    for cat_name in sorted(reclassified.keys(), key=lambda c: -len(reclassified[c])):
        entries = reclassified[cat_name]
        # raw_category 변형 종류 보기
        variants = {}
        for _, _, raw in entries:
            variants[raw] = variants.get(raw, 0) + 1
        top_variants = sorted(variants.items(), key=lambda x: -x[1])[:3]
        variant_str = ", ".join(f"'{v[0]}'({v[1]})" for v in top_variants)
        print(f"  {cat_name:>12}: {len(entries):>5}건  예: {variant_str}")

    if still_etc:
        print(f"\n  미분류 {len(still_etc)}건:")
        # 미분류 raw_category 집계
        etc_variants = {}
        for _, raw in still_etc:
            etc_variants[raw or "(null)"] = etc_variants.get(raw or "(null)", 0) + 1
        for raw, cnt in sorted(etc_variants.items(), key=lambda x: -x[1]):
            print(f"    {cnt:>4}건  {raw}")

    if errors:
        print(f"\n  오류:")
        for e in errors[:10]:
            print(f"    {e}")

    # 실제 적용
    if not dry_run and total_reclassified > 0:
        print(f"\n적용 중...")
        updated = 0
        for cat_name, entries in reclassified.items():
            for item_id, new_cat_id, _ in entries:
                conn.execute(
                    "UPDATE evt_items SET category_id = ? WHERE id = ?",
                    (new_cat_id, item_id)
                )
                updated += 1
        conn.commit()
        print(f"완료: {updated}건 업데이트")
    elif dry_run:
        print(f"\n[DRY RUN] 실제 변경 없음. --dry-run 제거하면 적용됩니다.")

    conn.close()

    return {
        "total_checked": len(items),
        "reclassified": total_reclassified,
        "still_etc": len(still_etc),
        "errors": len(errors),
        "by_category": {k: len(v) for k, v in reclassified.items()},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="이벤트 카테고리 재분류")
    parser.add_argument("--dry-run", action="store_true", default=False,
                        help="변경하지 않고 결과만 확인")
    args = parser.parse_args()
    reclassify(dry_run=args.dry_run)
