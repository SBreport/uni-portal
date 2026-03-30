"""
블로그 제목 스크래핑 모듈

제목이 없는 게시글의 published_url에서 <title> 태그를 추출하여
scraped_title 컬럼에 저장합니다.

사용:
  - CLI: python blog/scrape_titles.py [--limit 100] [--delay 0.3]
  - API: POST /blog/scrape-titles (SyncSettings에서 호출)
"""

import re
import time
import sqlite3
import os
import sys
import urllib.request
from typing import Optional, Callable

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "equipment.db")

# 네이버 블로그 title 접미사 제거 패턴
_NAVER_SUFFIX = re.compile(r"\s*:\s*네이버 블로그$")
_NAVER_CAFE_SUFFIX = re.compile(r"\s*:\s*네이버 카페$")


def extract_title_from_url(url: str, timeout: int = 10) -> Optional[str]:
    """URL에서 <title> 태그를 추출하여 정제된 제목 반환."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        html = resp.read().decode("utf-8", errors="replace")

        m = re.search(r"<title>([^<]+)</title>", html)
        if not m:
            return None

        title = m.group(1).strip()
        # 네이버 접미사 제거
        title = _NAVER_SUFFIX.sub("", title)
        title = _NAVER_CAFE_SUFFIX.sub("", title)
        title = title.strip()

        if not title or title in ("네이버 블로그", "네이버 카페"):
            return None

        return title
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "(삭제됨)"
        return None
    except Exception:
        return None


def scrape_missing_titles(
    limit: int = 0,
    delay: float = 0.3,
    include_cafe: bool = False,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    제목이 없는 게시글의 URL에서 제목을 수집.

    Args:
        limit: 최대 처리 건수 (0=전체)
        delay: 요청 간 대기 시간(초)
        include_cafe: True면 카페 URL도 포함, False면 블로그만
        progress_callback: 진행률 콜백 fn(current, total, title)

    Returns:
        {total, scraped, failed, skipped, deleted}
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 대상: 원본 title 비어있고, URL 있고, scraped_title 아직 없는 건
    query = """
        SELECT id, published_url, keyword, content_number
        FROM blog_posts
        WHERE (title = '' OR title IS NULL)
          AND published_url != '' AND published_url IS NOT NULL
          AND (scraped_title = '' OR scraped_title IS NULL)
    """
    if not include_cafe:
        query += "  AND published_url NOT LIKE '%cafe.naver.com%'\n"
    if limit > 0:
        query += f" LIMIT {limit}"

    rows = conn.execute(query).fetchall()
    total = len(rows)

    result = {"total": total, "scraped": 0, "failed": 0, "skipped": 0, "deleted": 0}

    for i, row in enumerate(rows):
        url = row["published_url"].strip()
        if not url:
            result["skipped"] += 1
            continue

        title = extract_title_from_url(url)

        if title == "(삭제됨)":
            conn.execute(
                "UPDATE blog_posts SET scraped_title = ?, needs_review = 1 WHERE id = ?",
                (title, row["id"]),
            )
            result["deleted"] += 1
        elif title:
            # scraped_title 저장 + clean_title 갱신
            conn.execute(
                "UPDATE blog_posts SET scraped_title = ?, clean_title = ?, needs_review = 0 WHERE id = ?",
                (title, title, row["id"]),
            )
            result["scraped"] += 1
        else:
            result["failed"] += 1

        if progress_callback and (i + 1) % 10 == 0:
            progress_callback(i + 1, total, title or "(실패)")

        # 100건마다 커밋
        if (i + 1) % 100 == 0:
            conn.commit()

        if delay > 0 and i < total - 1:
            time.sleep(delay)

    conn.commit()
    conn.close()
    return result


def get_scrape_status() -> dict:
    """현재 스크래핑 대상 건수 조회 (블로그/카페 구분)."""
    conn = sqlite3.connect(DB_PATH)
    total_missing = conn.execute("""
        SELECT COUNT(*) FROM blog_posts
        WHERE (title = '' OR title IS NULL)
          AND published_url != '' AND published_url IS NOT NULL
    """).fetchone()[0]

    already_scraped = conn.execute("""
        SELECT COUNT(*) FROM blog_posts
        WHERE scraped_title != '' AND scraped_title IS NOT NULL
    """).fetchone()[0]

    remaining_blog = conn.execute("""
        SELECT COUNT(*) FROM blog_posts
        WHERE (title = '' OR title IS NULL)
          AND published_url != '' AND published_url IS NOT NULL
          AND (scraped_title = '' OR scraped_title IS NULL)
          AND published_url NOT LIKE '%cafe.naver.com%'
    """).fetchone()[0]

    remaining_cafe = conn.execute("""
        SELECT COUNT(*) FROM blog_posts
        WHERE (title = '' OR title IS NULL)
          AND published_url != '' AND published_url IS NOT NULL
          AND (scraped_title = '' OR scraped_title IS NULL)
          AND published_url LIKE '%cafe.naver.com%'
    """).fetchone()[0]

    conn.close()
    return {
        "total_missing": total_missing,
        "already_scraped": already_scraped,
        "remaining": remaining_blog + remaining_cafe,
        "remaining_blog": remaining_blog,
        "remaining_cafe": remaining_cafe,
    }


# CLI 실행
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="블로그 제목 스크래핑")
    parser.add_argument("--limit", type=int, default=0, help="최대 처리 건수 (0=전체)")
    parser.add_argument("--delay", type=float, default=0.3, help="요청 간 대기(초)")
    args = parser.parse_args()

    status = get_scrape_status()
    print(f"제목 누락: {status['total_missing']}건 / 수집 완료: {status['already_scraped']}건 / 남은 대상: {status['remaining']}건")

    if status["remaining"] == 0:
        print("수집할 대상이 없습니다.")
        sys.exit(0)

    def on_progress(current, total, title):
        safe = title[:50].encode("ascii", errors="replace").decode("ascii")
        print(f"  [{current}/{total}] {safe}")

    print(f"\n스크래핑 시작 (limit={args.limit or '전체'}, delay={args.delay}s)")
    result = scrape_missing_titles(
        limit=args.limit,
        delay=args.delay,
        progress_callback=on_progress,
    )
    print(f"\n완료: 수집 {result['scraped']}건 / 실패 {result['failed']}건 / 삭제 {result['deleted']}건 / 건너뜀 {result['skipped']}건")
