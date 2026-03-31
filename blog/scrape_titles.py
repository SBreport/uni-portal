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


def _extract_meta(html: str, prop: str) -> Optional[str]:
    """HTML에서 특정 property/name의 meta content 추출."""
    # property="xxx" content="yyy"
    m = re.search(rf'<meta\s+[^>]*property=["\']{ re.escape(prop) }["\']\s+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(rf'<meta\s+content=["\']([^"\']+)["\']\s+[^>]*property=["\']{ re.escape(prop) }["\']', html)
    if not m:
        m = re.search(rf'<meta\s+[^>]*name=["\']{ re.escape(prop) }["\']\s+content=["\']([^"\']+)["\']', html)
    if not m:
        m = re.search(rf'<meta\s+content=["\']([^"\']+)["\']\s+[^>]*name=["\']{ re.escape(prop) }["\']', html)
    return html_mod.unescape(m.group(1).strip()) if m else None


def _extract_blog_profile(blog_id: str, timeout: int = 10) -> dict:
    """
    블로그 프로필(닉네임, 타이틀) 추출.

    전략:
    1. PostList.naver에서 <strong class="nick">닉네임</strong> + <span class="dsc">타이틀</span> 추출
    2. 실패 시 블로그 메인 og:title에서 타이틀만 폴백

    Returns:
        {"nickname": str, "title": str, "error": str}
        - error: 빈 문자열이면 성공, 아니면 실패 사유
    """
    result = {"nickname": "", "title": "", "error": ""}

    # 전략 1: PostList.naver — 가장 정확한 닉네임 소스
    try:
        postlist_url = f"https://blog.naver.com/PostList.naver?blogId={blog_id}"
        html = _fetch_html(postlist_url, timeout)
        if html:
            # <strong class="nick">닉네임</strong>
            m_nick = re.search(
                r'<strong\s+class=["\']nick["\'][^>]*>([^<{]+)</strong>',
                html,
            )
            if m_nick:
                nick = html_mod.unescape(m_nick.group(1).strip())
                if nick:
                    result["nickname"] = nick

            # <span class="dsc">블로그 타이틀</span>
            m_dsc = re.search(
                r'<span\s+class=["\']dsc["\'][^>]*>([^<]+)</span>',
                html,
            )
            if m_dsc:
                dsc = html_mod.unescape(m_dsc.group(1).strip())
                # {=blogName} 같은 템플릿 변수 제외
                if dsc and not dsc.startswith("{="):
                    result["title"] = dsc

            if result["nickname"]:
                return result
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["error"] = "(계정 차단)"
            return result
        if e.code == 403:
            result["error"] = "(비공개 블로그 전환)"
            return result
        result["error"] = f"(HTTP {e.code})"
        return result
    except urllib.error.URLError:
        result["error"] = "(접속 불가)"
        return result
    except Exception:
        pass

    # 전략 2: 블로그 메인 og:title 폴백 (닉네임이 아닌 타이틀만)
    try:
        main_url = f"https://blog.naver.com/{blog_id}"
        html = _fetch_html(main_url, timeout)
        if html:
            og_title = _extract_meta(html, "og:title")
            if og_title:
                cleaned = _NAVER_SUFFIX.sub("", og_title).strip()
                if cleaned and not _BLOG_CHANNEL_NAME.match(cleaned):
                    result["title"] = cleaned
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result["error"] = "(계정 차단)"
        elif e.code == 403:
            result["error"] = "(비공개 블로그 전환)"
        else:
            result["error"] = f"(HTTP {e.code})"
    except urllib.error.URLError:
        result["error"] = "(접속 불가)"
    except Exception:
        result["error"] = "(수집 실패)"

    if not result["nickname"] and not result["title"] and not result["error"]:
        result["error"] = "(닉네임 없음)"

    return result


def scrape_account_nicknames(
    force: bool = False,
    delay: float = 0.5,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    blog_accounts의 닉네임/타이틀을 수집.

    PostList.naver 페이지의 <strong class="nick"> 태그에서 닉네임을 추출합니다.
    실패 시 사유를 blog_nickname에 기록합니다 (예: "(블로그 없음)", "(접속 불가)").

    Args:
        force: True면 이미 수집된 계정도 재수집
        delay: 요청 간 대기(초)
        progress_callback: fn(current, total, message)
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 대상: 닉네임이 비어있거나, force=True면 에러 표시인 계정도 재수집
    if force:
        where = "channel != 'cafe'"
    else:
        where = """
            (blog_nickname = '' OR blog_nickname IS NULL
             OR blog_nickname LIKE '(%)')
            AND channel != 'cafe'
        """
    accounts = conn.execute(f"""
        SELECT blog_id, channel FROM blog_accounts WHERE {where}
    """).fetchall()

    total = len(accounts)
    result = {"total": total, "updated": 0, "failed": 0, "errors": {}}

    for i, acc in enumerate(accounts):
        blog_id = acc["blog_id"]
        profile = _extract_blog_profile(blog_id)

        nickname_val = profile["nickname"]
        title_val = profile["title"]

        if nickname_val:
            # 닉네임 수집 성공
            conn.execute("""
                UPDATE blog_accounts
                SET blog_nickname = ?,
                    blog_title = CASE WHEN ? != '' THEN ? ELSE blog_title END
                WHERE blog_id = ?
            """, (nickname_val, title_val, title_val, blog_id))
            result["updated"] += 1
            msg = f"{blog_id}: {nickname_val}"
        elif profile["error"]:
            # 실패 사유를 닉네임 필드에 기록
            conn.execute("""
                UPDATE blog_accounts
                SET blog_nickname = ?,
                    blog_title = CASE WHEN ? != '' THEN ? ELSE blog_title END
                WHERE blog_id = ?
            """, (profile["error"], title_val, title_val, blog_id))
            result["failed"] += 1
            result["errors"][blog_id] = profile["error"]
            msg = f"{blog_id}: {profile['error']}"
        else:
            # 닉네임 없지만 타이틀은 있을 수 있음
            error_msg = "(닉네임 없음)"
            conn.execute("""
                UPDATE blog_accounts
                SET blog_nickname = ?,
                    blog_title = CASE WHEN ? != '' THEN ? ELSE blog_title END
                WHERE blog_id = ?
            """, (error_msg, title_val, title_val, blog_id))
            result["failed"] += 1
            result["errors"][blog_id] = error_msg
            msg = f"{blog_id}: {error_msg}"

        if progress_callback:
            progress_callback(i + 1, total, msg)

        if (i + 1) % 20 == 0:
            conn.commit()

        if delay > 0 and i < total - 1:
            time.sleep(delay)

    conn.commit()
    conn.close()
    return result


def fix_url_titles(
    delay: float = 0.3,
    progress_callback: Optional[Callable] = None,
) -> dict:
    """
    needs_review=1이면서 title에 blog.naver.com URL이 포함된 글의
    실제 제목을 URL에서 스크래핑하여 clean_title을 갱신.

    대상: 노션 CSV에서 제목 필드에 하이퍼링크가 잘못 삽입된 케이스
    예: "https://blog.naver.com/xxx/123https://blog.naver.com/xxx/123"

    Returns:
        {total, fixed, failed, details: [{id, blog_id, url, title}]}
    """
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 대상: needs_review=1 AND title에 blog.naver.com URL 포함
    rows = conn.execute("""
        SELECT id, title, keyword, content_number, blog_id
        FROM blog_posts
        WHERE needs_review = 1
          AND title LIKE '%blog.naver.com/%'
    """).fetchall()

    total = len(rows)
    result = {"total": total, "fixed": 0, "failed": 0, "details": []}

    for i, row in enumerate(rows):
        raw_title = row["title"].strip()

        # URL 추출: blog.naver.com/{blogId}/{logNo} 패턴
        m = re.search(r"https?://blog\.naver\.com/([^/\s]+)/(\d+)", raw_title)
        if not m:
            result["failed"] += 1
            continue

        url = m.group(0)
        scraped = extract_title_from_url(url)

        if scraped and scraped != "(삭제됨)":
            conn.execute("""
                UPDATE blog_posts
                SET clean_title = ?, scraped_title = ?, needs_review = 0
                WHERE id = ?
            """, (scraped, scraped, row["id"]))
            result["fixed"] += 1
            result["details"].append({
                "id": row["id"],
                "blog_id": row["blog_id"],
                "url": url,
                "title": scraped,
            })
            msg = f"{row['blog_id']}: {scraped}"
        elif scraped == "(삭제됨)":
            # 삭제된 글은 keyword로 대체하되 review 유지
            keyword = (row["keyword"] or "").strip()
            conn.execute("""
                UPDATE blog_posts
                SET scraped_title = '(삭제됨)',
                    clean_title = CASE WHEN ? != '' THEN ? ELSE clean_title END
                WHERE id = ?
            """, (keyword, keyword, row["id"]))
            result["failed"] += 1
            msg = f"{row['blog_id']}: (삭제됨)"
        else:
            result["failed"] += 1
            msg = f"{row['blog_id']}: (추출 실패)"

        if progress_callback:
            progress_callback(i + 1, total, msg)

        if (i + 1) % 20 == 0:
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
