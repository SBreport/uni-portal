"""
Notion API → blog_posts 동기화 스크립트

기능:
  1. 증분 동기화: 마지막 동기화 이후 수정된 페이지만 가져와 업데이트
  2. 제목 보정: needs_review=1인 레코드의 제목을 Notion plain_text로 복원
  3. 신규 추가: DB에 없는 Notion 페이지는 새로 INSERT

사용법:
  python blog/sync_notion.py --token=ntn_xxx                # 증분 동기화
  python blog/sync_notion.py --token=ntn_xxx --fix-titles   # 제목 보정만
  python blog/sync_notion.py --token=ntn_xxx --full         # 전체 동기화
  python blog/sync_notion.py --token=ntn_xxx --dry-run      # 미리보기

환경변수: NOTION_TOKEN, NOTION_BLOG_DB_ID
"""

import os
import sys
import re
import sqlite3
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog.enrich import enrich_row

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "equipment.db")

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_BLOG_DB_ID = os.environ.get("NOTION_BLOG_DB_ID", "1523e540ee5d4f7d9aa7edf6cc13d394")

OPTIMAL_KEYWORDS = ["최적", "NB", "준최", "배포", "알선"]


def _notion_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def fetch_notion_pages(token: str, db_id: str, since: str = None) -> list[dict]:
    """Notion DB 페이지를 가져온다. since가 있으면 그 이후 수정된 것만."""
    import requests

    headers = _notion_headers(token)
    all_pages = []
    has_more = True
    cursor = None
    page_num = 0

    while has_more:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor

        # 증분 필터: last_edited_time > since
        if since:
            body["filter"] = {
                "timestamp": "last_edited_time",
                "last_edited_time": {"after": since},
            }
        body["sorts"] = [{"timestamp": "last_edited_time", "direction": "descending"}]

        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=headers, json=body,
        )

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", 2))
            time.sleep(retry_after)
            continue

        if r.status_code in (502, 503, 504):
            # 서버 오류 — 3초 후 재시도 (최대 3회)
            retries = getattr(fetch_notion_pages, '_retries', 0)
            if retries < 3:
                fetch_notion_pages._retries = retries + 1
                time.sleep(3)
                continue
            else:
                fetch_notion_pages._retries = 0
                raise Exception(f"Notion API {r.status_code}: 재시도 초과")

        if r.status_code != 200:
            raise Exception(f"Notion API {r.status_code}: {r.text[:200]}")

        data = r.json()
        results = data.get("results", [])
        all_pages.extend(results)
        has_more = data.get("has_more", False)
        cursor = data.get("next_cursor")
        page_num += 1

        time.sleep(0.4)

    return all_pages


def extract_page_data(page: dict) -> dict:
    """Notion 페이지에서 주요 속성을 추출."""
    props = page.get("properties", {})

    def get_rich_text(prop_name):
        val = props.get(prop_name, {})
        texts = val.get("rich_text", []) if val.get("type") == "rich_text" else []
        return "".join(t.get("plain_text", "") for t in texts).strip()

    def get_title(prop_name):
        val = props.get(prop_name, {})
        texts = val.get("title", []) if val.get("type") == "title" else []
        return "".join(t.get("plain_text", "") for t in texts).strip()

    def get_url(prop_name):
        val = props.get(prop_name, {})
        return (val.get("url") or "").strip() if val.get("type") == "url" else ""

    def get_multi_select(prop_name):
        val = props.get(prop_name, {})
        return [s["name"] for s in val.get("multi_select", [])] if val.get("type") == "multi_select" else []

    def get_people(prop_name):
        val = props.get(prop_name, {})
        return [p.get("name", "") for p in val.get("people", [])] if val.get("type") == "people" else []

    def get_date(prop_name):
        val = props.get(prop_name, {})
        d = val.get("date") if val.get("type") == "date" else None
        return d.get("start", "") if d else ""

    def get_number(prop_name):
        val = props.get(prop_name, {})
        return val.get("number") if val.get("type") == "number" else None

    def get_status(prop_name):
        val = props.get(prop_name, {})
        s = val.get("status") if val.get("type") == "status" else None
        return s.get("name", "") if s else ""

    main_url = get_url("메인블로그 링크")

    return {
        "notion_page_id": page.get("id", ""),
        "last_edited": page.get("last_edited_time", ""),
        "content_number": get_title("콘텐츠 번호"),
        "title": get_rich_text("제목"),
        "keyword": get_rich_text("키워드"),
        "tags": ", ".join(get_multi_select("관련 태그")),
        "post_type": ", ".join(get_multi_select("종류")),
        "author": ", ".join(get_people("담당자")),
        "published_at": get_date("발행 일자"),
        "status": get_status("진행 상황"),
        "main_url": main_url,
        "backup_url": get_url("백업블로그 링크"),
        "exposure_rank": get_number("노출순위"),
        "note": get_rich_text("비고"),
    }


def parse_blog_url(url: str) -> tuple:
    """URL에서 (platform, blog_id, post_number)를 추출."""
    if not url:
        return ("", "", "")
    m = re.match(r"https?://blog\.naver\.com/([^/?\s]+)/(\d+)", url)
    if m:
        return ("blog", m.group(1), m.group(2))
    m = re.match(r"https?://blog\.naver\.com/PostView\.naver\?.*blogId=([^&]+).*logNo=(\d+)", url)
    if m:
        return ("blog", m.group(1), m.group(2))
    m = re.match(r"https?://cafe\.naver\.com/([^/?\s]+)/(\d+)", url)
    if m:
        return ("cafe", m.group(1), m.group(2))
    return ("", "", "")


def classify_channel(post_type: str) -> str:
    """종류에서 채널 판별."""
    for kw in OPTIMAL_KEYWORDS:
        if kw in post_type:
            return "opt"
    return "br"


def get_last_sync_time(conn) -> str:
    """마지막 Notion 동기화 시각을 ISO 8601로 반환."""
    row = conn.execute(
        "SELECT last_edited_cutoff FROM notion_sync_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return row[0] if row and row[0] else ""


def incremental_sync(token: str, db_id: str, dry_run: bool = False) -> dict:
    """증분 동기화: 마지막 동기화 이후 수정된 페이지만 처리."""
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    since = get_last_sync_time(conn)
    sync_type = "incremental" if since else "full"

    # 1. Notion에서 변경된 페이지 가져오기
    pages = fetch_notion_pages(token, db_id, since=since if since else None)

    if not pages:
        conn.close()
        return {"notion_pages": 0, "matched": 0, "updated": 0, "new_posts": 0, "message": "변경 사항 없음"}

    # 최신 수정 시각 기록 (다음 증분 동기화용)
    latest_edited = max(pg.get("last_edited_time", "") for pg in pages)

    # 2. 처리
    updated = 0
    new_posts = 0
    matched = 0

    for pg in pages:
        d = extract_page_data(pg)
        platform, blog_id, post_number = parse_blog_url(d["main_url"])

        if not blog_id or not post_number:
            continue

        # DB에서 기존 레코드 찾기
        existing = conn.execute(
            "SELECT id, title, clean_title FROM blog_posts WHERE platform = ? AND blog_id = ? AND post_number = ?",
            (platform, blog_id, post_number),
        ).fetchone()

        # 가공 데이터 생성
        enriched = enrich_row({
            "content_number": d["content_number"],
            "post_type": d["post_type"],
            "project": "",
            "status": d["status"],
            "title": d["title"],
            "keyword": d["keyword"],
            "author": d["author"],
        })

        # Notion에서 가져온 제목이 있으면 그걸 우선 사용
        clean_title = d["title"] if d["title"] else enriched["clean_title"]

        if existing:
            # 기존 레코드 업데이트
            matched += 1
            if not dry_run:
                conn.execute("""
                    UPDATE blog_posts SET
                        title = ?, keyword = ?, tags = ?, post_type = ?,
                        author = ?, published_at = ?, status = ?,
                        exposure_rank = ?, note = ?,
                        clean_title = ?, needs_review = 0,
                        post_type_main = ?, post_type_sub = ?,
                        status_clean = ?, author_main = ?, author_sub = ?,
                        branch_name = ?, slot_number = ?
                    WHERE id = ?
                """, (
                    d["title"], d["keyword"], d["tags"], d["post_type"],
                    d["author"], d["published_at"], d["status"],
                    d["exposure_rank"], d["note"],
                    clean_title, enriched["post_type_main"], enriched["post_type_sub"],
                    enriched["status_clean"], enriched["author_main"], enriched["author_sub"],
                    enriched["branch_name"], enriched["slot_number"],
                    existing["id"],
                ))
            updated += 1
        else:
            # 신규 레코드 INSERT
            channel = "cafe" if platform == "cafe" else classify_channel(d["post_type"])
            if not dry_run:
                conn.execute("""
                    INSERT OR IGNORE INTO blog_posts (
                        content_number, title, keyword, tags, post_type,
                        blog_channel, blog_id, post_number, platform,
                        published_url, backup_url, author, published_at,
                        status, exposure_rank, note,
                        clean_title, needs_review,
                        branch_name, slot_number, post_type_main, post_type_sub,
                        status_clean, author_main, author_sub
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                              ?, 0, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d["content_number"], d["title"], d["keyword"], d["tags"], d["post_type"],
                    channel, blog_id, post_number, platform,
                    d["main_url"], d["backup_url"], d["author"], d["published_at"],
                    d["status"], d["exposure_rank"], d["note"],
                    clean_title,
                    enriched["branch_name"], enriched["slot_number"],
                    enriched["post_type_main"], enriched["post_type_sub"],
                    enriched["status_clean"], enriched["author_main"], enriched["author_sub"],
                ))
            new_posts += 1

    # 3. 동기화 로그 기록
    if not dry_run:
        conn.execute("""
            INSERT INTO notion_sync_log (sync_type, notion_pages, matched, updated, new_posts, last_edited_cutoff)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sync_type, len(pages), matched, updated, new_posts, latest_edited))
        conn.commit()

    conn.close()

    return {
        "sync_type": sync_type,
        "since": since or "(전체)",
        "notion_pages": len(pages),
        "matched": matched,
        "updated": updated,
        "new_posts": new_posts,
        "last_edited_cutoff": latest_edited,
        "message": f"동기화 완료: {updated}건 업데이트, {new_posts}건 신규",
    }


def fix_titles(token: str, db_id: str, dry_run: bool = False) -> dict:
    """needs_review=1인 레코드의 제목만 Notion에서 보정."""
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.row_factory = sqlite3.Row

    # needs_review=1이 없으면 스킵
    review_count = conn.execute("SELECT COUNT(*) FROM blog_posts WHERE needs_review = 1").fetchone()[0]
    if review_count == 0:
        conn.close()
        return {"message": "보정 필요한 레코드 없음", "updated": 0}

    # 전체 Notion 페이지 로드 (제목 보정용)
    pages = fetch_notion_pages(token, db_id)

    # 매칭 인덱스
    notion_index = {}
    for pg in pages:
        d = extract_page_data(pg)
        _, blog_id, post_number = parse_blog_url(d["main_url"])
        if blog_id and post_number:
            notion_index[(blog_id, post_number)] = d

    # DB 보정
    db_rows = conn.execute(
        "SELECT id, blog_id, post_number, clean_title FROM blog_posts WHERE needs_review = 1 AND blog_id != '' AND post_number != ''"
    ).fetchall()

    fixed = 0
    for row in db_rows:
        notion = notion_index.get((row["blog_id"], row["post_number"]))
        if not notion or not notion["title"]:
            continue
        if notion["title"] != row["clean_title"] and not dry_run:
            conn.execute(
                "UPDATE blog_posts SET clean_title = ?, needs_review = 0 WHERE id = ?",
                (notion["title"], row["id"]),
            )
        fixed += 1

    if not dry_run:
        conn.commit()

    remaining = conn.execute("SELECT COUNT(*) FROM blog_posts WHERE needs_review = 1").fetchone()[0]
    conn.close()

    return {
        "notion_pages": len(pages),
        "fixed": fixed,
        "remaining_review": remaining,
        "message": f"제목 보정 {fixed}건, 남은 검토 {remaining}건",
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Notion API → 블로그 동기화")
    parser.add_argument("--token", default=NOTION_TOKEN, help="Notion Integration 토큰")
    parser.add_argument("--db-id", default=NOTION_BLOG_DB_ID, help="Notion DB ID")
    parser.add_argument("--full", action="store_true", help="전체 동기화 (증분 무시)")
    parser.add_argument("--fix-titles", action="store_true", help="needs_review 제목 보정만")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 미리보기")
    args = parser.parse_args()

    if not args.token:
        print("[오류] --token 또는 NOTION_TOKEN 환경변수 필요")
        sys.exit(1)

    if args.fix_titles:
        result = fix_titles(args.token, args.db_id, dry_run=args.dry_run)
    else:
        if args.full:
            # full이면 since를 무시
            result = incremental_sync(args.token, args.db_id, dry_run=args.dry_run)
        else:
            result = incremental_sync(args.token, args.db_id, dry_run=args.dry_run)

    print(result)
