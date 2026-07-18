"""Notion 블로그 DB 속성 진단 프로브.

2026-07-01부터 동기화가 전건 스킵되는 원인(속성명/타입 변경) 확정용.
최근 수정된 페이지 3건의 속성 이름·타입을 출력하고,
sync_notion.py가 기대하는 속성과 대조한다.

사용법 (운영 서버 또는 토큰 보유 환경):
  python scripts/notion_probe.py                  # app_settings 토큰 + env DB ID 사용
  python scripts/notion_probe.py --token=ntn_xxx --db-id=xxxx
"""

import argparse
import os
import sqlite3
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "equipment.db")

# sync_notion.extract_page_data가 기대하는 속성명 → 타입
EXPECTED = {
    "콘텐츠 번호": "title",
    "제목": "rich_text",
    "키워드": "rich_text",
    "관련 태그": "multi_select",
    "종류": "multi_select",
    "담당자": "people",
    "발행 일자": "date",
    "진행 상황": "status",
    "메인블로그 링크": "url",
    "백업블로그 링크": "url",
    "노출순위": "number",
    "비고": "rich_text",
}


def get_token_from_db() -> str | None:
    try:
        conn = sqlite3.connect(os.path.abspath(DB_PATH))
        row = conn.execute("SELECT value FROM app_settings WHERE key='notion_token'").fetchone()
        conn.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", default=None)
    parser.add_argument("--db-id", default=os.environ.get("NOTION_BLOG_DB_ID", ""))
    args = parser.parse_args()

    token = args.token or os.environ.get("NOTION_TOKEN") or get_token_from_db()
    if not token or not args.db_id:
        print("[오류] 토큰 또는 DB ID 없음. --token / --db-id 지정 필요")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    r = requests.post(
        f"https://api.notion.com/v1/databases/{args.db_id}/query",
        headers=headers,
        json={
            "page_size": 3,
            "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}],
        },
    )
    if r.status_code != 200:
        print(f"[오류] Notion API {r.status_code}: {r.text[:300]}")
        sys.exit(1)

    pages = r.json().get("results", [])
    if not pages:
        print("[결과] 페이지 0건 — DB ID가 다른 DB를 보고 있을 가능성")
        sys.exit(0)

    for i, pg in enumerate(pages, 1):
        props = pg.get("properties", {})
        print(f"\n=== 페이지 {i} (last_edited: {pg.get('last_edited_time')}) ===")
        print(f"{'속성명':<25} {'타입':<15} 기대와 비교")
        for name, val in sorted(props.items()):
            t = val.get("type", "?")
            if name in EXPECTED:
                mark = "OK" if EXPECTED[name] == t else f"타입 변경! 기대={EXPECTED[name]}"
            else:
                mark = "<- 신규/이름변경 속성"
            print(f"{name:<25} {t:<15} {mark}")
        missing = [n for n in EXPECTED if n not in props]
        if missing:
            print(f"\n[누락] sync가 기대하지만 없는 속성: {', '.join(missing)}")


if __name__ == "__main__":
    main()
