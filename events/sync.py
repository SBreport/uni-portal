"""이벤트 데이터 수집 파이프라인 오케스트레이터.

사용법:
  CLI: python -m events.sync --year 2026 --start-month 3 --end-month 4
  API: POST /api/events/sync
"""

import argparse
import os
import re
import sqlite3
from datetime import datetime

from shared.db import get_conn, EQUIPMENT_DB

# 지점명 별칭 매핑 (시트 탭 이름 → DB 이름)
BRANCH_ALIAS = {
    "홍대신촌점": "홍대점",
}


def _get_conn():
    return get_conn(EQUIPMENT_DB)


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

    from events.parser import parse_branch_sheet, validate_parsed_events
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
        resolved_name = BRANCH_ALIAS.get(tab_name, tab_name)
        branch_id = get_evt_branch_id(conn, resolved_name)
        if branch_id is None:
            # "강남점" → "강남" 매핑 시도
            branch_id = get_evt_branch_id(conn, re.sub(r"점$", "", resolved_name))
        if branch_id is None:
            errors.append(f"{tab_name}: DB에 지점 없음")
            continue

        try:
            events = parse_branch_sheet(rows, tab_name)
            if not events:
                continue

            validation = validate_events(events, tab_name)
            parse_issues = validate_parsed_events(events)
            if parse_issues:
                for issue in parse_issues:
                    errors.append(f"{tab_name}: {issue['event']} — {issue['issue']}")

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


def _extract_sheet_id(url: str):
    """Google Sheets URL에서 시트 ID를 추출."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None


def _process_branch_data(branch_data: dict, year: int, start_month: int, end_month: int, source_url: str = "") -> dict:
    """공통 처리 로직: 지점별 raw 데이터 → DB 저장."""
    from events.parser import parse_branch_sheet, validate_parsed_events
    from events.normalizer import CategoryNormalizer, ComponentParser
    from events.db import (
        ensure_period,
        get_evt_branch_id,
        insert_events,
        create_ingestion_log,
        update_ingestion_log,
    )

    label = f"{str(year)[-2:]}.{start_month}~{end_month}"
    conn = _get_conn()
    period_id = ensure_period(conn, year, start_month, end_month, label, source_url=source_url)
    log_id = create_ingestion_log(conn, period_id)

    cat_normalizer = CategoryNormalizer()
    comp_parser = ComponentParser()

    total_items = 0
    processed = 0
    errors = []

    for tab_name, rows in branch_data.items():
        branch_id = get_evt_branch_id(conn, tab_name)
        if branch_id is None:
            branch_id = get_evt_branch_id(conn, re.sub(r"점$", "", tab_name))
        if branch_id is None:
            errors.append(f"{tab_name}: DB에 지점 없음")
            continue

        try:
            events = parse_branch_sheet(rows, tab_name)
            if not events:
                continue

            parse_issues = validate_parsed_events(events)
            if parse_issues:
                for issue in parse_issues:
                    errors.append(f"{tab_name}: {issue['event']} — {issue['issue']}")

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

    unmapped = cat_normalizer.get_unmapped()
    if unmapped:
        cat_normalizer.save_review_queue()
        print(f"  미매핑 카테고리 {len(unmapped)}건 → review_queue.json 저장")

    status = "completed" if not errors else "completed_with_errors"
    error_log = [{"error": e} for e in errors] if errors else None
    update_ingestion_log(conn, log_id, status, processed, total_items, error_log)
    conn.close()

    return {"processed": processed, "total_items": total_items, "errors": errors}


def _read_excel_to_branch_data(content, skip_tabs=None) -> dict:
    """Excel 바이트(또는 BytesIO) → {탭이름: [[셀값, ...], ...]} 딕셔너리."""
    import pandas as pd
    from io import BytesIO

    if skip_tabs is None:
        skip_tabs = {"지점 목차", "파일생성목록", "raw", "목차", "Sheet1", "요약", "목록"}

    buf = BytesIO(content) if isinstance(content, bytes) else content
    try:
        excel = pd.ExcelFile(buf)
    except Exception as e:
        raise ValueError(f"파일 읽기 실패: {e}")

    branch_data = {}
    for sheet_name in excel.sheet_names:
        if sheet_name.strip() in skip_tabs:
            continue
        try:
            df = pd.read_excel(excel, sheet_name=sheet_name, header=None)
            rows = df.fillna("").astype(str).values.tolist()
            if rows and len(rows) > 2:
                branch_data[sheet_name.strip()] = rows
        except Exception:
            continue

    return branch_data


def run_event_sync_from_url(url: str, year: int, start_month: int, end_month: int) -> dict:
    """Google Sheets URL에서 이벤트 데이터를 읽어 DB에 저장.

    공개 시트의 경우 xlsx export를 통해 데이터를 가져옵니다.
    """
    from urllib.request import urlopen, Request
    from urllib.error import URLError

    sheet_id = _extract_sheet_id(url)
    if not sheet_id:
        return {"processed": 0, "total_items": 0, "errors": ["유효한 Google Sheets URL이 아닙니다."]}

    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    print(f"이벤트 수집 (URL): {export_url}")

    try:
        req = Request(export_url, headers={"User-Agent": "uni-portal/1.0"})
        resp = urlopen(req, timeout=60)
        content = resp.read()
    except URLError as e:
        return {"processed": 0, "total_items": 0,
                "errors": [f"시트 다운로드 실패 (공개 설정을 확인하세요): {e}"]}
    except Exception as e:
        return {"processed": 0, "total_items": 0, "errors": [f"시트 다운로드 실패: {e}"]}

    try:
        branch_data = _read_excel_to_branch_data(content)
    except ValueError as e:
        return {"processed": 0, "total_items": 0, "errors": [str(e)]}

    if not branch_data:
        return {"processed": 0, "total_items": 0, "errors": ["읽을 수 있는 지점 시트가 없습니다."]}

    print(f"  읽은 지점 수: {len(branch_data)} ({', '.join(branch_data.keys())})")
    return _process_branch_data(branch_data, year, start_month, end_month, source_url=url)


def run_event_sync_from_file(file_bytes: bytes, year: int, start_month: int, end_month: int) -> dict:
    """업로드된 Excel 파일에서 이벤트 데이터를 읽어 DB에 저장."""
    print("이벤트 수집 (파일 업로드)")

    try:
        branch_data = _read_excel_to_branch_data(file_bytes)
    except ValueError as e:
        return {"processed": 0, "total_items": 0, "errors": [str(e)]}

    if not branch_data:
        return {"processed": 0, "total_items": 0, "errors": ["읽을 수 있는 지점 시트가 없습니다."]}

    print(f"  읽은 지점 수: {len(branch_data)} ({', '.join(branch_data.keys())})")
    return _process_branch_data(branch_data, year, start_month, end_month, source_url="file_upload")


def main():
    parser = argparse.ArgumentParser(description="유앤아이의원 이벤트 데이터 수집")
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--start-month", type=int, required=True)
    parser.add_argument("--end-month", type=int, required=True)
    args = parser.parse_args()

    run_event_sync(args.year, args.start_month, args.end_month)


if __name__ == "__main__":
    main()
