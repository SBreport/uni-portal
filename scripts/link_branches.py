# -*- coding: utf-8 -*-
"""
link_branches.py
~~~~~~~~~~~~~~~~
Add evt_branch_id to blog_posts, place_daily, webpage_daily
and populate it by matching each table's branch_name to evt_branches.

Run:
    python scripts/link_branches.py

매핑 함수는 blog/branch_link.py (공용 모듈)에서 가져온다.
"""

import sqlite3
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import os

# 프로젝트 루트를 sys.path에 추가 (공용 모듈 import용)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

DB = os.path.join(_ROOT, "data", "equipment.db")

# 매핑 로직은 공용 모듈에서 가져옴 (import 부작용 없음)
from blog.branch_link import (
    load_branches,
    resolve_blog,
    resolve_place,
    resolve_webpage,
)


# ---------------------------------------------------------------------------
# Part A – Add columns (idempotent)
# ---------------------------------------------------------------------------

def add_columns(conn):
    cur = conn.cursor()
    for table in ("blog_posts", "place_daily", "webpage_daily"):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN evt_branch_id INTEGER")
            print(f"  [+] Added evt_branch_id to {table}")
        except sqlite3.OperationalError:
            print(f"  [=] evt_branch_id already exists in {table} (skipped)")
    conn.commit()


# ---------------------------------------------------------------------------
# Part D – Apply updates and print statistics
# ---------------------------------------------------------------------------

def update_table(conn, table: str, resolver, by_name: dict, by_short: dict):
    cur = conn.cursor()

    # 모든 distinct branch_name 가져오기
    cur.execute(f"SELECT DISTINCT branch_name FROM {table}")
    distinct_names = [r[0] for r in cur.fetchall()]

    # 매핑 딕셔너리 구성
    mapping = {}  # branch_name -> evt_branch_id (None 가능)
    for bn in distinct_names:
        mapping[bn] = resolver(bn, by_name, by_short)

    # DB 업데이트 적용
    for bn, eid in mapping.items():
        if eid is not None:
            cur.execute(
                f"UPDATE {table} SET evt_branch_id = ? WHERE branch_name = ?",
                (eid, bn),
            )
        else:
            # 명시적 NULL 초기화 (재실행 시 멱등성 보장)
            cur.execute(
                f"UPDATE {table} SET evt_branch_id = NULL WHERE branch_name = ?",
                (bn,),
            )
    conn.commit()

    # 통계
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE evt_branch_id IS NOT NULL")
    mapped = cur.fetchone()[0]
    unmapped = total - mapped

    return total, mapped, unmapped, mapping


def print_blog_details(conn, mapping: dict):
    """매핑 안 된 블로그 게시글 내역 출력."""
    cur = conn.cursor()
    unmapped_yuanai = []
    unmapped_other  = []

    for bn, eid in mapping.items():
        if eid is None:
            if (bn or "").startswith("유앤"):
                unmapped_yuanai.append(bn)
            else:
                unmapped_other.append(bn)

    if unmapped_yuanai:
        print(f"\n  [!] 유앤아이계 blog accounts that did NOT map ({len(unmapped_yuanai)}):")
        for bn in sorted(unmapped_yuanai):
            cur.execute("SELECT COUNT(*) FROM blog_posts WHERE branch_name = ?", (bn,))
            cnt = cur.fetchone()[0]
            print(f"      '{bn}'  ({cnt} posts)")

    if unmapped_other:
        print(f"\n  [i] Non-유앤아이 (NULL is expected) — {len(unmapped_other)} distinct names:")
        shown = sorted(unmapped_other)[:30]
        for bn in shown:
            cur.execute("SELECT COUNT(*) FROM blog_posts WHERE branch_name = ?", (bn,))
            cnt = cur.fetchone()[0]
            print(f"      '{bn}'  ({cnt} posts)")
        if len(unmapped_other) > 30:
            print(f"      ... and {len(unmapped_other) - 30} more")


def main():
    conn = sqlite3.connect(DB)

    print("=" * 60)
    print("Step 1: Add evt_branch_id columns")
    print("=" * 60)
    add_columns(conn)

    print("\n" + "=" * 60)
    print("Step 2: Load evt_branches lookup tables")
    print("=" * 60)
    by_name, by_short = load_branches(conn)
    print(f"  Loaded {len(by_name)} branches by name, {len(by_short)} by short_name")

    print("\n" + "=" * 60)
    print("Step 3: Map and update tables")
    print("=" * 60)

    # blog_posts
    print("\n--- blog_posts ---")
    b_total, b_mapped, b_unmapped, blog_mapping = update_table(
        conn, "blog_posts", resolve_blog, by_name, by_short
    )
    print(f"  Total:   {b_total:,}")
    print(f"  Mapped:  {b_mapped:,}  ({b_mapped/b_total*100:.1f}%)")
    print(f"  Unmapped:{b_unmapped:,}  ({b_unmapped/b_total*100:.1f}%)")
    print_blog_details(conn, blog_mapping)

    # place_daily
    print("\n--- place_daily ---")
    p_total, p_mapped, p_unmapped, place_mapping = update_table(
        conn, "place_daily", resolve_place, by_name, by_short
    )
    print(f"  Total:   {p_total:,}")
    print(f"  Mapped:  {p_mapped:,}  ({p_mapped/p_total*100:.1f}%)")
    print(f"  Unmapped:{p_unmapped:,}  ({p_unmapped/p_total*100:.1f}%)")
    if p_unmapped > 0:
        print("  Unmapped place branch_names:")
        for bn, eid in place_mapping.items():
            if eid is None:
                print(f"    '{bn}'")

    # webpage_daily
    print("\n--- webpage_daily ---")
    w_total, w_mapped, w_unmapped, webpage_mapping = update_table(
        conn, "webpage_daily", resolve_webpage, by_name, by_short
    )
    print(f"  Total:   {w_total:,}")
    print(f"  Mapped:  {w_mapped:,}  ({w_mapped/w_total*100:.1f}%)")
    print(f"  Unmapped:{w_unmapped:,}  ({w_unmapped/w_total*100:.1f}%)")
    if w_unmapped > 0:
        print("  Unmapped webpage branch_names:")
        for bn, eid in webpage_mapping.items():
            if eid is None:
                print(f"    '{bn}'")

    print("\n" + "=" * 60)
    print("Done.")
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
