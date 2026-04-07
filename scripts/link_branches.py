# -*- coding: utf-8 -*-
"""
link_branches.py
~~~~~~~~~~~~~~~~
Add evt_branch_id to blog_posts, place_daily, webpage_daily
and populate it by matching each table's branch_name to evt_branches.

Run:
    python scripts/link_branches.py
"""

import sqlite3
import re
import sys
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DB = "C:/LocalGD/7_CODE/uni-portal/data/equipment.db"


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
# Part B – Build lookup structures from evt_branches
# ---------------------------------------------------------------------------

def load_branches(conn):
    """Returns two dicts:
        by_name      : { name_str -> id }   e.g. "강남점" -> 1
        by_short     : { short_name -> id } e.g. "강남" -> 1
    """
    cur = conn.cursor()
    cur.execute("SELECT id, name, short_name FROM evt_branches")
    rows = cur.fetchall()
    by_name  = {r[1]: r[0] for r in rows}
    by_short = {r[2]: r[0] for r in rows}
    return by_name, by_short


# ---------------------------------------------------------------------------
# Part C – Mapping functions
# ---------------------------------------------------------------------------

# Non-유앤아이 clinic keywords → these blog posts should stay NULL
NON_YUANAI_PREFIXES = [
    "파인드", "이효진여성의원", "이효진산부인과", "365봄", "조은", "참조은",
    "로렐의원", "레리", "신현편안", "더편한", "이다움", "이플", "푸른잎",
    "눈피부과", "굿플", "굿플란트", "굿플중랑", "민플", "닥터굿",
    "스브", "연세온아", "10월10일", "유라라", "파인리", "에이", "세련",
    "여울", "청아", "해피", "산부인과", "의원", "클리닉", "피부과",
    "병원", "한의원",
]

# Blog-specific special cases: "유앤XXX" → branch name
BLOG_SPECIAL = {
    "유앤검단":  "인천검단점",
    "유앤배곧":  "시흥배곧점",
    "유앤미금":  "분당미금점",
    "유앤목동":  "목동점",
    "유앤하남미사": "하남미사점",
    "유앤경기광주": "경기광주점",
    "유앤화성봉담": "화성봉담점",
}

# Place-specific overrides: "XXX유앤아이" → branch name
PLACE_SPECIAL = {
    "미사유앤아이":    "하남미사점",
    "시흥배곧유앤아이": "시흥배곧점",
    "분당미금유앤아이": "분당미금점",
    "경기광주유앤아이": "경기광주점",
    "화성봉담유앤아이": "화성봉담점",
    "인천검단유앤아이": "인천검단점",
}

# Webpage: "유앤아이의원 검단점" → "인천검단점"
WEBPAGE_SPECIAL = {
    "검단점":   "인천검단점",
    "하남미사점": "하남미사점",
    "서면점":   None,  # 부산 서면 — not a separate evt_branch yet
}


def map_blog(branch_name: str, by_name: dict, by_short: dict):
    """Return evt_branch_id for a blog_posts.branch_name, or None."""
    name = (branch_name or "").strip()

    # Empty
    if not name:
        return None

    # Pure numeric or starts with digit → NULL
    if re.match(r"^\d", name):
        return None

    # Non-유앤아이 check (clinic names that are not our branches)
    if is_non_yuanai_blog(name):
        return None

    # Exact match against evt_branches.name
    if name in by_name:
        return by_name[name]

    # Special cases: "유앤XXX" (exact key) → known branch name
    if name in BLOG_SPECIAL:
        return by_name.get(BLOG_SPECIAL[name])

    # For all "유앤..." names: extract the leading Korean syllable run after "유앤"
    # and use that as the branch keyword.
    # This handles ALL suffix patterns:
    #   "유앤강남 최적1"         → core = "강남"
    #   "유앤강남 최적10"        → core = "강남"
    #   "유앤창원3"              → core = "창원"  (trailing digit stripped by regex)
    #   "유앤목동 1"             → core = "목동"
    #   "유앤하남미사 최적1"     → core = "하남미사"
    #   "유앤산본 10 "서브2""   → core = "산본"
    #   "유앤광교 12_최적1"      → core = "광교"
    #   "유앤의정부 14 (삭제..)" → core = "의정부"
    #   "유앤부평8_10`"          → core = "부평"
    if name.startswith("유앤"):
        # Extract consecutive Korean chars right after "유앤"
        # Korean Unicode block: AC00–D7A3 (가–힣) plus Jamo and Compat Jamo
        m = re.match(r"^유앤([\uAC00-\uD7A3\u3130-\u318F\uFFA0-\uFFDC]+)", name)
        if m:
            core = m.group(1)  # e.g. "강남", "하남미사", "왕십리"

            # Check BLOG_SPECIAL first (multi-syllable keys like "유앤검단"→"인천검단점")
            yuanai_key = "유앤" + core
            if yuanai_key in BLOG_SPECIAL:
                return by_name.get(BLOG_SPECIAL[yuanai_key])

            # Try "core점" as branch name
            candidate = core + "점"
            if candidate in by_name:
                return by_name[candidate]

            # Try short_name exact match
            if core in by_short:
                return by_short[core]

    # Nothing matched
    return None


def is_non_yuanai_blog(name: str) -> bool:
    """True if name clearly belongs to a non-유앤아이 clinic."""
    if not name:
        return False
    for prefix in NON_YUANAI_PREFIXES:
        if name.startswith(prefix):
            return True
    # Numeric-only, e.g. "6", "7"
    if re.match(r"^\d+$", name):
        return True
    return False


def resolve_blog(branch_name: str, by_name: dict, by_short: dict):
    """Entry-point resolver for blog_posts rows."""
    name = (branch_name or "").strip()
    if not name:
        return None
    if is_non_yuanai_blog(name):
        return None
    return map_blog(name, by_name, by_short)


def resolve_place(branch_name: str, by_name: dict, by_short: dict):
    """Map 'XXX유앤아이' → evt_branch_id."""
    name = (branch_name or "").strip()
    if not name:
        return None

    # Special overrides first
    if name in PLACE_SPECIAL:
        target = PLACE_SPECIAL[name]
        return by_name.get(target)

    # Pattern: "XXX유앤아이" → "XXX점"
    if name.endswith("유앤아이"):
        core = name[: -len("유앤아이")]  # e.g. "강남"
        candidate = core + "점"
        if candidate in by_name:
            return by_name[candidate]
        if core in by_short:
            return by_short[core]

    # Fallback exact
    if name in by_name:
        return by_name[name]

    return None


def resolve_webpage(branch_name: str, by_name: dict, by_short: dict):
    """Map '유앤아이의원 XXX점' → evt_branch_id."""
    name = (branch_name or "").strip()
    if not name:
        return None

    PREFIX = "유앤아이의원 "
    if name.startswith(PREFIX):
        suffix = name[len(PREFIX):]  # e.g. "강남점"
        # Check special overrides
        if suffix in WEBPAGE_SPECIAL:
            target = WEBPAGE_SPECIAL[suffix]
            return by_name.get(target) if target else None
        if suffix in by_name:
            return by_name[suffix]
        # try short_name (strip "점")
        core = suffix.rstrip("점")
        if core in by_short:
            return by_short[core]

    # Exact fallback
    if name in by_name:
        return by_name[name]

    return None


# ---------------------------------------------------------------------------
# Part D – Apply updates and print statistics
# ---------------------------------------------------------------------------

def update_table(conn, table: str, resolver, by_name: dict, by_short: dict):
    cur = conn.cursor()

    # Fetch all distinct branch_names
    cur.execute(f"SELECT DISTINCT branch_name FROM {table}")
    distinct_names = [r[0] for r in cur.fetchall()]

    # Build mapping
    mapping = {}  # branch_name -> evt_branch_id (may be None)
    for bn in distinct_names:
        mapping[bn] = resolver(bn, by_name, by_short)

    # Apply updates
    for bn, eid in mapping.items():
        if eid is not None:
            cur.execute(
                f"UPDATE {table} SET evt_branch_id = ? WHERE branch_name = ?",
                (eid, bn),
            )
        else:
            # Explicitly NULL (idempotent reset for re-runs)
            cur.execute(
                f"UPDATE {table} SET evt_branch_id = NULL WHERE branch_name = ?",
                (bn,),
            )
    conn.commit()

    # Stats
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE evt_branch_id IS NOT NULL")
    mapped = cur.fetchone()[0]
    unmapped = total - mapped

    return total, mapped, unmapped, mapping


def print_blog_details(conn, mapping: dict):
    """Show breakdown of unmapped blog posts."""
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
