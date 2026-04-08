"""NAS 배포 후 DB 마이그레이션 통합 스크립트.

2026-04-08 세션에서 추가된 모든 DB 변경사항을 한번에 적용합니다.

사용법:
  python scripts/migrate_all.py          # 실제 적용
  python scripts/migrate_all.py --check  # 현재 상태만 확인
"""

import sys
import os
import argparse
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.db import get_conn, EQUIPMENT_DB


def add_column_safe(conn, table, column, coltype="TEXT"):
    """컬럼이 없으면 추가, 있으면 무시."""
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")
        print(f"  + {table}.{column} ({coltype}) 추가")
        return True
    except sqlite3.OperationalError:
        return False


def check_column_exists(conn, table, column):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return column in cols


def run_migration(check_only=False):
    conn = get_conn(EQUIPMENT_DB)
    print(f"DB: {EQUIPMENT_DB}")
    print()

    # ── 1. 새 컬럼 추가 ──
    print("=== 1. 컬럼 추가 ===")
    columns_to_add = [
        ("equipment", "evt_branch_id", "INTEGER"),
        ("equipment", "device_info_id", "INTEGER"),
        ("evt_treatments", "item_type", "TEXT"),
        ("evt_treatments", "device_info_id", "INTEGER"),
        ("blog_posts", "evt_branch_id", "INTEGER"),
        ("place_daily", "evt_branch_id", "INTEGER"),
        ("webpage_daily", "evt_branch_id", "INTEGER"),
    ]

    for table, col, coltype in columns_to_add:
        exists = check_column_exists(conn, table, col)
        if check_only:
            status = "OK" if exists else "MISSING"
            print(f"  {table}.{col}: {status}")
        elif not exists:
            add_column_safe(conn, table, col, coltype)
        else:
            print(f"  {table}.{col}: 이미 존재")

    if check_only:
        print("\n[CHECK MODE] 실제 변경 없음.")
        conn.close()
        return

    conn.commit()

    # ── 2. 이벤트 카테고리 재분류 ──
    print("\n=== 2. 이벤트 카테고리 재분류 ===")
    etc_count = conn.execute(
        "SELECT COUNT(*) FROM evt_items WHERE category_id = 16"
    ).fetchone()[0]
    if etc_count > 0:
        print(f"  기타 {etc_count}건 재분류 중...")
        from events.normalizer import CategoryNormalizer
        normalizer = CategoryNormalizer()
        cat_map = {r[1]: r[0] for r in conn.execute("SELECT id, name FROM evt_categories").fetchall()}

        items = conn.execute("SELECT id, raw_category FROM evt_items WHERE category_id = 16").fetchall()
        updated = 0
        for item_id, raw_cat in items:
            if not raw_cat:
                continue
            new_name = normalizer.normalize(raw_cat)
            new_id = cat_map.get(new_name)
            if new_id and new_id != 16:
                conn.execute("UPDATE evt_items SET category_id = ? WHERE id = ?", (new_id, item_id))
                updated += 1
        conn.commit()
        print(f"  재분류 완료: {updated}/{etc_count}")
    else:
        print("  기타 0건 — 이미 분류됨")

    # ── 3. device_info 확장 ──
    print("\n=== 3. device_info 확장 ===")
    di_count = conn.execute("SELECT COUNT(*) FROM device_info").fetchone()[0]
    if di_count < 200:
        print(f"  현재 {di_count}건 → expand_device_info 실행...")
        conn.close()
        os.system(f"{sys.executable} scripts/expand_device_info.py")
        conn = get_conn(EQUIPMENT_DB)
        di_count2 = conn.execute("SELECT COUNT(*) FROM device_info").fetchone()[0]
        print(f"  완료: {di_count} → {di_count2}건")
    else:
        print(f"  {di_count}건 — 이미 확장됨")

    # ── 4. 시술명 분류 ──
    print("\n=== 4. 시술명 분류 ===")
    classified = conn.execute(
        "SELECT COUNT(*) FROM evt_treatments WHERE item_type IS NOT NULL"
    ).fetchone()[0]
    total_treat = conn.execute("SELECT COUNT(*) FROM evt_treatments").fetchone()[0]
    if classified < total_treat * 0.5:
        print(f"  분류 {classified}/{total_treat} — normalize_treatments 실행...")
        conn.close()
        os.system(f"{sys.executable} scripts/normalize_treatments.py")
        conn = get_conn(EQUIPMENT_DB)
    else:
        print(f"  {classified}/{total_treat} — 이미 분류됨")

    # ── 5. 지점 통합 (equipment.evt_branch_id) ──
    print("\n=== 5. 지점 통합 ===")
    null_evt_br = conn.execute(
        "SELECT COUNT(*) FROM equipment WHERE evt_branch_id IS NULL"
    ).fetchone()[0]
    if null_evt_br > 0:
        print(f"  evt_branch_id NULL: {null_evt_br}건 — unify_branches 실행...")
        conn.close()
        os.system(f"{sys.executable} scripts/unify_branches.py")
        conn = get_conn(EQUIPMENT_DB)
    else:
        print(f"  equipment 전량 매핑됨")

    # ── 6. 블로그/플레이스/웹페이지 → 지점 연결 ──
    print("\n=== 6. 블로그/플레이스/웹페이지 지점 연결 ===")
    blog_null = conn.execute(
        "SELECT COUNT(*) FROM blog_posts WHERE evt_branch_id IS NULL AND branch_name LIKE '유앤%'"
    ).fetchone()[0]
    place_null = conn.execute(
        "SELECT COUNT(*) FROM place_daily WHERE evt_branch_id IS NULL"
    ).fetchone()[0]
    web_null = conn.execute(
        "SELECT COUNT(*) FROM webpage_daily WHERE evt_branch_id IS NULL"
    ).fetchone()[0]

    if blog_null + place_null + web_null > 0:
        print(f"  미매핑: 블로그 {blog_null}, 플레이스 {place_null}, 웹페이지 {web_null}")
        conn.close()
        os.system(f"{sys.executable} scripts/link_branches.py")
        conn = get_conn(EQUIPMENT_DB)
    else:
        print(f"  전량 매핑됨")

    # ── 7. 최종 현황 ──
    print("\n=== 최종 현황 ===")
    di = conn.execute("SELECT COUNT(*) FROM device_info").fetchone()[0]
    equip_linked = conn.execute("SELECT COUNT(*) FROM equipment WHERE device_info_id IS NOT NULL").fetchone()[0]
    equip_total = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    etc = conn.execute("SELECT COUNT(*) FROM evt_items WHERE category_id = 16").fetchone()[0]
    evt_total = conn.execute("SELECT COUNT(*) FROM evt_items").fetchone()[0]
    blog_linked = conn.execute("SELECT COUNT(*) FROM blog_posts WHERE evt_branch_id IS NOT NULL").fetchone()[0]
    blog_total = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]

    print(f"  device_info: {di}건")
    print(f"  equipment → device_info: {equip_linked}/{equip_total}")
    print(f"  이벤트 기타: {etc}/{evt_total}")
    print(f"  블로그 → 지점: {blog_linked}/{blog_total}")

    conn.close()
    print("\n마이그레이션 완료!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DB 마이그레이션 통합 실행")
    parser.add_argument("--check", action="store_true", help="현재 상태만 확인")
    args = parser.parse_args()
    run_migration(check_only=args.check)
