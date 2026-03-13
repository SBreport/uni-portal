"""이벤트 데이터 수집 파이프라인 오케스트레이터.

사용법:
  CLI: python -m events.sync --year 2026 --start-month 3 --end-month 4
  Streamlit: from events.sync import run_event_sync
"""

import argparse
import os
import re
import sqlite3
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def run_event_sync(year: int, start_month: int, end_month: int) -> dict:
    """이벤트 수집을 실행하고 결과 요약을 반환.

    Returns:
        {"processed": int, "total_items": int, "errors": list}
    """
    # 지연 import (gspread 미설치 환경에서도 다른 기능은 동작하도록)
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return {"processed": 0, "total_items": 0, "errors": ["gspread/google-auth 패키지가 설치되지 않았습니다."]}

    from events.parser import parse_branch_sheet
    from events.normalizer import CategoryNormalizer, ComponentParser
    from events.validators import validate_events
    from events.db import (
        ensure_period,
        get_evt_branch_id,
        insert_events,
        create_ingestion_log,
        update_ingestion_log,
    )

    # 설정
    event_sheet_id = os.environ.get("EVENT_SHEET_ID", "")
    credentials_file = os.environ.get(
        "GOOGLE_CREDENTIALS_FILE",
        os.path.join(os.path.dirname(__file__), "..", "credentials.json"),
    )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    if not event_sheet_id:
        return {"processed": 0, "total_items": 0, "errors": ["EVENT_SHEET_ID 환경변수가 설정되지 않았습니다."]}
    if not os.path.exists(credentials_file):
        return {"processed": 0, "total_items": 0, "errors": [f"credentials.json 파일을 찾을 수 없습니다: {credentials_file}"]}

    label = f"{str(year)[-2:]}.{start_month}~{end_month}"
    print(f"이벤트 수집 시작: {label}")

    # 1. DB 연결 + 기간 설정
    conn = _get_conn()
    period_id = ensure_period(
        conn, year, start_month, end_month, label,
        source_url=f"https://docs.google.com/spreadsheets/d/{event_sheet_id}",
    )
    log_id = create_ingestion_log(conn, period_id)

    # 2. Google Sheets 읽기
    creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(event_sheet_id)
    worksheets = spreadsheet.worksheets()
    skip_tabs = {"지점 목차", "파일생성목록", "raw"}

    branch_data = {}
    for ws in worksheets:
        if ws.title in skip_tabs:
            continue
        try:
            data = ws.get_all_values()
            if data:
                branch_data[ws.title] = data
        except Exception as e:
            print(f"  시트 읽기 오류 ({ws.title}): {e}")

    print(f"  읽은 지점 수: {len(branch_data)}")

    # 3. 정규화 도구 초기화
    cat_normalizer = CategoryNormalizer()
    comp_parser = ComponentParser()

    # 4. 각 지점 처리
    total_items = 0
    processed = 0
    errors = []

    for tab_name, rows in branch_data.items():
        branch_id = get_evt_branch_id(conn, tab_name)
        if branch_id is None:
            # "강남점" → "강남" 매핑 시도
            branch_id = get_evt_branch_id(conn, re.sub(r"점$", "", tab_name))
        if branch_id is None:
            errors.append(f"{tab_name}: DB에 지점 없음")
            continue

        try:
            events = parse_branch_sheet(rows, tab_name)
            if not events:
                continue

            validation = validate_events(events, tab_name)

            count = insert_events(
                conn, events, period_id, branch_id,
                category_resolver=cat_normalizer.normalize,
                component_parser=comp_parser,
            )

            total_items += count
            processed += 1
            print(f"  {tab_name}: {count}건 저장")

        except Exception as e:
            errors.append(f"{tab_name}: {e}")
            print(f"  {tab_name}: 오류 - {e}")

    # 5. 미매핑 카테고리 저장
    unmapped = cat_normalizer.get_unmapped()
    if unmapped:
        cat_normalizer.save_review_queue()
        print(f"  미매핑 카테고리 {len(unmapped)}건 → review_queue.json 저장")

    # 6. 수집 로그 업데이트
    status = "completed" if not errors else "completed_with_errors"
    error_log = [{"error": e} for e in errors] if errors else None
    update_ingestion_log(conn, log_id, status, processed, total_items, error_log)

    conn.close()

    result = {"processed": processed, "total_items": total_items, "errors": errors}
    print(f"수집 완료: {processed}개 지점, {total_items:,}건")
    return result


def main():
    parser = argparse.ArgumentParser(description="유앤아이의원 이벤트 데이터 수집")
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--start-month", type=int, required=True)
    parser.add_argument("--end-month", type=int, required=True)
    args = parser.parse_args()

    run_event_sync(args.year, args.start_month, args.end_month)


if __name__ == "__main__":
    main()
