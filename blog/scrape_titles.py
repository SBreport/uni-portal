"""
블로그 제목 스크래핑 모듈

제목이 없는 게시글의 published_url에서 <title> 태그를 추출하여
scraped_title 컬럼에 저장합니다.

사용:
  - CLI: python blog/scrape_titles.py [--limit 100] [--delay 0.3]
  - API: POST /blog/scrape-titles (SyncSettings에서 호출)
"""

import re
import html as html_mod
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
# "xxx님의 블로그" 채널명 패턴 (실제 제목이 아님)
_BLOG_CHANNEL_NAME = re.compile(r"^[a-zA-Z0-9_]+님의 블로그$")


def _fetch_html(url: str, timeout: int = 10) -> Optional[str]:
    """URL에서 HTML을 가져옴. Content-Type charset을 자동 감지."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    resp = urllib.request.urlopen(req, timeout=timeout)
    raw = resp.read()
    # Content-Type 헤더에서 charset 감지
    content_type = resp.headers.get("Content-Type", "")
    charset_m = re.search(r"charset=([^\s;]+)", content_type, re.IGNORECASE)
    charset = charset_m.group(1).strip() if charset_m else "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")


def _clean_title(title: str) -> Optional[str]:
    """제목 정제: HTML 엔티티 디코딩, 네이버 접미사 제거, 채널명 필터, 빈 값 처리."""
    title = html_mod.unescape(title)  # &lt; → <, &amp; → &
    title = _NAVER_SUFFIX.sub("", title)
    title = _NAVER_CAFE_SUFFIX.sub("", title)
    title = title.strip()
    if not title or title in ("네이버 블로그", "네이버 카페"):
        return None
    # "xxx님의 블로그" 채널명은 실제 제목이 아님
    if _BLOG_CHANNEL_NAME.match(title):
        return None
    return title


def _extract_og_title(html: str) -> Optional[str]:
    """HTML에서 og:title 메타 태그 추출."""
    m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(r'content=["\']([^"\']+)["\']\s+property=["\']og:title["\']', html)
    return m.group(1).strip() if m else None


def extract_title_from_url(url: str, timeout: int = 10) -> Optional[str]:
    """URL에서 게시글 제목을 추출. 네이버 블로그는 PostView에서 og:title 우선 사용."""
    try:
        # 네이버 카페: 로그인 없이 게시글 제목 접근 불가 (SPA + 인증 필요)
        if "cafe.naver.com" in url:
            return None

        # 네이버 블로그: PostView iframe URL에서 og:title 추출
        m_blog = re.match(r"https?://blog\.naver\.com/([^/]+)/(\d+)", url)
        if m_blog:
            blog_id, log_no = m_blog.group(1), m_blog.group(2)
            postview_url = f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"
            html = _fetch_html(postview_url, timeout)
            if html:
                og = _extract_og_title(html)
                if og:
                    return _clean_title(og)
                # og:title 없으면 <title> fallback
                m_t = re.search(r"<title>([^<]+)</title>", html)
                if m_t:
                    return _clean_title(m_t.group(1).strip())

        # 일반 URL: <title> 태그 → og:title 순서
        html = _fetch_html(url, timeout)
        if not html:
            return None

        # og:title 우선
        og = _extract_og_title(html)
        if og:
            cleaned = _clean_title(og)
            if cleaned:
                return cleaned

        # <title> fallback
        m = re.search(r"<title>([^<]+)</title>", html)
        if not m:
            return None
        return _clean_title(m.group(1).strip())

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

        # 카페 URL은 스크래핑 불가 → keyword를 대체 제목으로 사용
        is_cafe = "cafe.naver.com" in url
        if is_cafe:
            keyword = (row["keyword"] or "").strip()
            scraped_val = "(카페-수집불가)"
            clean_val = keyword if keyword else ""
            conn.execute(
                "UPDATE blog_posts SET scraped_title = ?, clean_title = ?, needs_review = ? WHERE id = ?",
                (scraped_val, clean_val, 0 if clean_val else 1, row["id"]),
            )
            result["skipped"] += 1
            # 카페는 HTTP 요청하지 않으므로 delay 불필요
            if progress_callback and (i + 1) % 10 == 0:
                progress_callback(i + 1, total, clean_val or scraped_val)
            if (i + 1) % 100 == 0:
                conn.commit()
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
