"""
블로그 게시글 CSV 임포트 스크립트

노션에서 내보낸 CSV를 blog_posts 테이블에 임포트.
- 다중 URL은 개별 행으로 분리
- 중복 체크: platform + blog_id + post_number
- 동기화 로그 기록 (blog_sync_log)

사용법:
  python blog/import_csv.py data/blog/파일명.csv
  python blog/import_csv.py data/blog/파일명.csv --channel br
  python blog/import_csv.py data/blog/파일명.csv --dry-run
"""

import csv
import os
import re
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blog.enrich import enrich_row

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "equipment.db")

# 최적블로그 키워드 → blog_channel='opt'
OPTIMAL_KEYWORDS = ["최적", "NB", "준최", "배포", "알선"]


def parse_url(url: str) -> dict:
    """URL에서 platform, blog_id, post_number 추출"""
    url = url.strip()
    if not url:
        return {"platform": "", "blog_id": "", "post_number": "", "url": ""}

    # blog.naver.com/ID/글번호
    m = re.match(r"https?://blog\.naver\.com/([^/?\s]+)/(\d+)", url)
    if m:
        return {"platform": "blog", "blog_id": m.group(1), "post_number": m.group(2), "url": url}

    # blog.naver.com/PostView.naver?blogId=...&logNo=...
    m = re.match(r"https?://blog\.naver\.com/PostView\.naver\?.*blogId=([^&]+).*logNo=(\d+)", url)
    if m:
        return {"platform": "blog", "blog_id": m.group(1), "post_number": m.group(2), "url": url}

    # blog.naver.com/ID (글번호 없음)
    m = re.match(r"https?://blog\.naver\.com/([^/?\s]+)/?$", url)
    if m:
        return {"platform": "blog", "blog_id": m.group(1), "post_number": "", "url": url}

    # cafe.naver.com/카페ID/글번호
    m = re.match(r"https?://cafe\.naver\.com/([^/?\s]+)/(\d+)", url)
    if m:
        return {"platform": "cafe", "blog_id": m.group(1), "post_number": m.group(2), "url": url}

    # cafe.naver.com/ArticleRead.nhn?clubid=...&articleid=...
    m = re.match(r"https?://cafe\.naver\.com/ArticleRead\.nhn\?.*clubid=(\d+).*articleid=(\d+)", url)
    if m:
        return {"platform": "cafe", "blog_id": f"club_{m.group(1)}", "post_number": m.group(2), "url": url}

    # 기타
    return {"platform": "other", "blog_id": "", "post_number": "", "url": url}


def split_urls(url_field: str) -> list:
    """콤마/공백으로 구분된 다중 URL을 분리"""
    if not url_field:
        return []
    # 콤마, 공백, 줄바꿈으로 분리
    urls = re.split(r"[,\s]+", url_field.strip())
    return [u.strip() for u in urls if u.strip().startswith("http")]


def classify_channel(post_type: str) -> tuple:
    """종류 필드에서 blog_channel과 channel_name 판별"""
    types = [t.strip() for t in post_type.split(",")]
    for t in types:
        if any(kw in t for kw in OPTIMAL_KEYWORDS):
            return "opt", t
    return "br", ""


def normalize_date(date_str: str) -> str:
    """날짜 형식 통일: 2026/03/24 → 2026-03-24"""
    if not date_str:
        return ""
    return date_str.strip().replace("/", "-")


def import_csv(csv_path: str, default_channel: str = "", dry_run: bool = False):
    """CSV 파일을 blog_posts 테이블에 임포트"""
    csv_path = os.path.abspath(csv_path)

    if not os.path.exists(csv_path):
        print(f"[오류] 파일 없음: {csv_path}")
        return

    # CSV 수정 시각 (= 노션 내보내기 시점)
    csv_mtime = datetime.fromtimestamp(os.path.getmtime(csv_path))
    csv_mtime_str = csv_mtime.strftime("%Y-%m-%d %H:%M:%S")

    print(f"CSV 파일: {Path(csv_path).name}")
    print(f"CSV 수정일시 (노션 내보내기): {csv_mtime_str}")
    print(f"{'='*60}")

    # CSV 읽기
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"총 행 수: {len(rows)}")

    # DB 연결
    conn = sqlite3.connect(os.path.abspath(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    imported = 0
    skipped_dup = 0
    skipped_empty = 0
    errors = 0

    for i, row in enumerate(rows):
        # BOM 처리
        content_number = row.get("\ufeff콘텐츠 번호", row.get("콘텐츠 번호", "")).strip()
        title = row.get("제목", "").strip()
        keyword = row.get("키워드", "").strip()
        tags = row.get("관련 태그", "").strip()
        post_type = row.get("종류", "").strip()
        author = row.get("담당자", "").strip()
        published_at = normalize_date(row.get("발행 일자", ""))
        deadline_at = normalize_date(row.get("원고마감일", ""))
        status = row.get("진행 상황", "").strip()
        project = row.get("프로젝트", "").strip()
        exposure_rank = row.get("노출순위", "").strip()
        note = row.get("비고", "").strip()
        backup_url = row.get("백업블로그 링크", "").strip()
        main_url_field = row.get("메인블로그 링크", "").strip()

        # 채널 분류
        channel, channel_name = classify_channel(post_type)
        if default_channel:
            channel = default_channel

        # URL 분리
        urls = split_urls(main_url_field)

        # URL이 없으면 1건으로 저장 (미발행/예약)
        if not urls:
            urls_parsed = [{"platform": "", "blog_id": "", "post_number": "", "url": ""}]
        else:
            urls_parsed = [parse_url(u) for u in urls]

        # 각 URL별로 행 생성
        for url_info in urls_parsed:
            platform = url_info["platform"]
            blog_id = url_info["blog_id"]
            post_number = url_info["post_number"]
            published_url = url_info["url"]

            # 유효성: 최소한 키워드나 제목이 있어야
            if not keyword and not title and not content_number:
                skipped_empty += 1
                continue

            # 중복 체크 (URL 있는 경우만)
            if platform and blog_id and post_number:
                existing = conn.execute(
                    "SELECT id FROM blog_posts WHERE platform=? AND blog_id=? AND post_number=?",
                    (platform, blog_id, post_number)
                ).fetchone()
                if existing:
                    skipped_dup += 1
                    continue

            if dry_run:
                imported += 1
                continue

            # 가공 컬럼 생성
            enriched = enrich_row({
                "content_number": content_number,
                "post_type": post_type,
                "project": project,
                "status": status,
                "title": title,
                "keyword": keyword,
                "author": author,
            })

            try:
                conn.execute("""
                    INSERT INTO blog_posts (
                        content_number, title, keyword, tags, post_type,
                        blog_channel, blog_id, post_number, platform,
                        published_url, backup_url, author, published_at,
                        deadline_at, status, project, exposure_rank, note,
                        branch_name, slot_number, post_type_main, post_type_sub,
                        project_month, project_branch, status_clean, clean_title,
                        author_main, author_sub, needs_review
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    content_number, title, keyword, tags, post_type,
                    channel, blog_id, post_number, platform,
                    published_url, backup_url, author, published_at,
                    deadline_at, status, project, exposure_rank, note,
                    enriched["branch_name"], enriched["slot_number"],
                    enriched["post_type_main"], enriched["post_type_sub"],
                    enriched["project_month"], enriched["project_branch"],
                    enriched["status_clean"], enriched["clean_title"],
                    enriched["author_main"], enriched["author_sub"],
                    enriched["needs_review"],
                ))
                imported += 1
            except sqlite3.IntegrityError:
                skipped_dup += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"  [오류] 행 {i+1}: {e}")

        # 진행 표시
        if (i + 1) % 2000 == 0:
            print(f"  진행: {i+1}/{len(rows)} 처리됨...")

    if not dry_run:
        # 동기화 로그 기록
        conn.execute("""
            INSERT INTO blog_sync_log (filename, csv_modified_at, total_rows, imported_rows, skipped_rows, blog_channel)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (Path(csv_path).name, csv_mtime_str, len(rows), imported, skipped_dup + skipped_empty, default_channel or "mixed"))

        conn.commit()

    conn.close()

    # 결과 출력
    print(f"\n{'='*60}")
    print(f"임포트 {'(dry-run)' if dry_run else '완료'}")
    print(f"  성공: {imported}건")
    print(f"  중복 스킵: {skipped_dup}건")
    print(f"  빈값 스킵: {skipped_empty}건")
    print(f"  오류: {errors}건")
    print(f"  CSV 기준일시: {csv_mtime_str}")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="노션 CSV → blog_posts DB 임포트")
    parser.add_argument("csv_file", help="CSV 파일 경로")
    parser.add_argument("--channel", default="", help="강제 채널 지정 (br/opt)")
    parser.add_argument("--dry-run", action="store_true", help="DB 저장 없이 시뮬레이션")
    args = parser.parse_args()

    import_csv(args.csv_file, default_channel=args.channel, dry_run=args.dry_run)
