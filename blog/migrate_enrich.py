"""
블로그 데이터 가공 마이그레이션 스크립트

기존 blog_posts 16,448건을 일괄 가공하여 가공 컬럼을 채운다.
blog_accounts 테이블도 초기 데이터를 생성한다.

사용법:
  python blog/migrate_enrich.py
  python blog/migrate_enrich.py --dry-run
"""

import os
import sys
import sqlite3

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog.enrich import enrich_row

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "equipment.db")


def migrate(dry_run: bool = False):
    db_path = os.path.abspath(DB_PATH)
    if not os.path.exists(db_path):
        print(f"[오류] DB 없음: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 스키마 확인: 가공 컬럼이 있는지
    cols = {row[1] for row in conn.execute("PRAGMA table_info(blog_posts)").fetchall()}
    if "branch_name" not in cols:
        print("[오류] 가공 컬럼이 없습니다. 먼저 init_db.py를 실행하세요.")
        print("  python init_db.py")
        conn.close()
        return

    # 전체 행 조회 (가공에 필요한 컬럼만)
    rows = conn.execute("""
        SELECT id, content_number, post_type, project, status, title, keyword, author
        FROM blog_posts
    """).fetchall()

    total = len(rows)
    print(f"총 {total}건 가공 시작... {'(dry-run)' if dry_run else ''}")

    updated = 0
    review_count = 0

    for i, row in enumerate(rows):
        row_dict = dict(row)
        enriched = enrich_row(row_dict)

        if enriched["needs_review"]:
            review_count += 1

        if not dry_run:
            conn.execute("""
                UPDATE blog_posts SET
                    branch_name = ?,
                    slot_number = ?,
                    post_type_main = ?,
                    post_type_sub = ?,
                    project_month = ?,
                    project_branch = ?,
                    status_clean = ?,
                    clean_title = ?,
                    author_main = ?,
                    author_sub = ?,
                    needs_review = ?
                WHERE id = ?
            """, (
                enriched["branch_name"],
                enriched["slot_number"],
                enriched["post_type_main"],
                enriched["post_type_sub"],
                enriched["project_month"],
                enriched["project_branch"],
                enriched["status_clean"],
                enriched["clean_title"],
                enriched["author_main"],
                enriched["author_sub"],
                enriched["needs_review"],
                row_dict["id"],
            ))

        updated += 1

        if (i + 1) % 5000 == 0:
            print(f"  진행: {i+1}/{total}")
            if not dry_run:
                conn.commit()

    if not dry_run:
        conn.commit()

    print(f"\n가공 완료: {updated}건 업데이트")
    print(f"검토 필요(needs_review=1): {review_count}건")

    # ── blog_accounts 초기 생성 ──
    print("\nblog_accounts 초기 데이터 생성...")
    accounts = conn.execute("""
        SELECT blog_id, blog_channel, COUNT(*) as cnt
        FROM blog_posts
        WHERE blog_id != ''
        GROUP BY blog_id
    """).fetchall()

    inserted = 0
    for acc in accounts:
        if not dry_run:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO blog_accounts (blog_id, channel)
                    VALUES (?, ?)
                """, (acc["blog_id"], acc["blog_channel"]))
                inserted += 1
            except Exception:
                pass

    if not dry_run:
        conn.commit()

    acc_total = conn.execute("SELECT COUNT(*) FROM blog_accounts").fetchone()[0]
    print(f"blog_accounts: {acc_total}건 (신규 {inserted}건)")

    # ── 결과 요약 ──
    print(f"\n{'='*60}")
    print("가공 결과 샘플:")
    samples = conn.execute("""
        SELECT branch_name, slot_number, post_type_main, post_type_sub,
               project_month, project_branch, status_clean,
               SUBSTR(clean_title, 1, 30) as title_preview,
               author_main, author_sub, needs_review
        FROM blog_posts WHERE branch_name != '' LIMIT 5
    """).fetchall()
    for s in samples:
        print(f"  지점={s['branch_name']} 슬롯={s['slot_number']} "
              f"종류={s['post_type_main']} 월={s['project_month']} "
              f"상태={s['status_clean']} 검토={s['needs_review']}")
        print(f"    제목: {s['title_preview']}...")
        print(f"    담당: {s['author_main']}" + (f" / {s['author_sub']}" if s['author_sub'] else ""))

    # 통계
    stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN needs_review = 1 THEN 1 ELSE 0 END) as review,
            SUM(CASE WHEN branch_name != '' THEN 1 ELSE 0 END) as has_branch,
            SUM(CASE WHEN post_type_main != '' THEN 1 ELSE 0 END) as has_type,
            SUM(CASE WHEN project_month != '' THEN 1 ELSE 0 END) as has_month,
            SUM(CASE WHEN author_main != '' THEN 1 ELSE 0 END) as has_author
        FROM blog_posts
    """).fetchone()

    print(f"\n통계:")
    print(f"  전체: {stats['total']}건")
    print(f"  지점 파싱: {stats['has_branch']}건")
    print(f"  종류 파싱: {stats['has_type']}건")
    print(f"  프로젝트월: {stats['has_month']}건")
    print(f"  담당자 분리: {stats['has_author']}건")
    print(f"  검토 필요: {stats['review']}건")
    print(f"{'='*60}")

    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="블로그 데이터 가공 마이그레이션")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 시뮬레이션")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
