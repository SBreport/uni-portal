"""카페 마케팅 원고 데이터 — 구글 시트 1회성 가져오기.

사용법:
  CLI: python -m cafe.sync --year 2026 --month 3 --branch 동탄점
  Streamlit: from cafe.sync import run_cafe_import
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "cafe.db")

# 지점명 별칭 매핑 (시트 탭 이름 → DB 이름)
BRANCH_ALIAS = {
    "홍대신촌점": "홍대점",
}

# 시트에서 건너뛸 탭
SKIP_TABS = {"목차", "보유장비", "raw", "template"}


def run_cafe_import(year: int, month: int, branch_filter: str = "") -> dict:
    """카페 원고 시트에서 데이터를 가져와 DB에 저장.

    Args:
        year: 연도 (2026)
        month: 월 (1~12)
        branch_filter: 특정 지점만 가져오기 (예: "동탄점"). 빈 문자열이면 전체.

    Returns:
        {"processed": int, "total_articles": int, "errors": list}
    """
    # 지연 import
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return {"processed": 0, "total_articles": 0,
                "errors": ["gspread/google-auth 패키지가 설치되지 않았습니다."]}

    from events.db import get_evt_branch_id
    from cafe.db import (
        get_or_create_period,
        get_or_create_branch_period,
        update_branch_metadata,
        upsert_article,
        upsert_comment,
        create_sync_log,
        update_sync_log,
        load_cafe_articles,
    )

    # 환경변수에서 시트 ID
    cafe_sheet_id = os.environ.get("CAFE_SHEET_ID", "")
    credentials_file = os.environ.get(
        "GOOGLE_CREDENTIALS_FILE",
        os.path.join(os.path.dirname(__file__), "..", "credentials.json"),
    )
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    if not cafe_sheet_id:
        return {"processed": 0, "total_articles": 0,
                "errors": ["CAFE_SHEET_ID 환경변수가 설정되지 않았습니다."]}
    if not os.path.exists(credentials_file):
        return {"processed": 0, "total_articles": 0,
                "errors": [f"credentials.json을 찾을 수 없습니다: {credentials_file}"]}

    print(f"카페 원고 가져오기 시작: {year}년 {month}월")

    # 1. 기간 생성
    period_id = get_or_create_period(year, month)
    log_id = create_sync_log(period_id)

    # 2. 시트 읽기
    creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(cafe_sheet_id)
    worksheets = spreadsheet.worksheets()

    branch_data = {}
    for ws in worksheets:
        tab = ws.title.strip()
        if tab in SKIP_TABS:
            continue
        # 지점 필터
        if branch_filter and branch_filter not in tab:
            continue
        try:
            data = ws.get_all_values()
            if data and len(data) >= 5:
                branch_data[tab] = data
        except Exception as e:
            print(f"  시트 읽기 오류 ({tab}): {e}")

    print(f"  읽은 지점 수: {len(branch_data)}")

    # 3. 각 지점 처리
    import sqlite3
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row

    # evt_branches는 equipment.db에 있으므로 별도 연결
    equip_db = os.path.join(DB_DIR, "equipment.db")
    equip_conn = sqlite3.connect(equip_db, timeout=30)
    equip_conn.execute("PRAGMA journal_mode=WAL")
    equip_conn.row_factory = sqlite3.Row

    total_articles = 0
    processed = 0
    errors = []

    for tab_name, rows in branch_data.items():
        resolved = BRANCH_ALIAS.get(tab_name, tab_name)

        # evt_branches에서 지점 ID 찾기 (equipment.db)
        branch_id = get_evt_branch_id(equip_conn, resolved)
        if branch_id is None:
            branch_id = get_evt_branch_id(equip_conn, re.sub(r"점$", "", resolved))
        if branch_id is None:
            errors.append(f"{tab_name}: DB에 지점 없음")
            continue

        try:
            bp_id = get_or_create_branch_period(period_id, branch_id)

            # 헤더 메타데이터 파싱 (Row 1~3)
            meta = _parse_header_meta(rows)
            update_branch_metadata(bp_id, **meta)

            # 원고 파싱 (Row 5~24, 0-indexed: rows[4]~rows[23])
            count = 0
            for i in range(4, min(24, len(rows))):
                row = rows[i]
                if len(row) < 8:
                    continue

                # E열(idx 4)=순번
                order_str = row[4].strip() if len(row) > 4 else ""
                if not order_str or not order_str.isdigit():
                    continue

                article_order = int(order_str)
                article_id = upsert_article(
                    bp_id, article_order,
                    keyword=_safe_get(row, 1),       # B열
                    category=_safe_get(row, 2),       # C열
                    equipment_name=_safe_get(row, 3), # D열
                    photo_ref=_safe_get(row, 5),      # F열
                    title=_safe_get(row, 6),          # G열
                    body=_safe_get(row, 7),           # H열
                )

                # 댓글 3쌍: I/J, K/L, M/N (idx 8~13)
                for slot in range(1, 4):
                    c_idx = 6 + (slot * 2)     # 8, 10, 12
                    r_idx = c_idx + 1          # 9, 11, 13
                    comment = _safe_get(row, c_idx)
                    reply = _safe_get(row, r_idx)
                    if comment or reply:
                        upsert_comment(article_id, slot, comment, reply)

                # 본문이 있으면 상태를 '작성완료'로
                if _safe_get(row, 7):
                    from cafe.db import change_status
                    try:
                        change_status(article_id, "작성완료", changed_by="시트가져오기")
                    except Exception:
                        pass

                count += 1

            total_articles += count
            processed += 1
            print(f"  {tab_name}: {count}건 저장")

            # 캐시 초기화
            load_cafe_articles.clear()

        except Exception as e:
            errors.append(f"{tab_name}: {e}")
            print(f"  {tab_name}: 오류 - {e}")

    conn.close()
    equip_conn.close()

    # 4. 로그 업데이트
    status = "completed" if not errors else "completed_with_errors"
    error_json = json.dumps([{"error": e} for e in errors], ensure_ascii=False) if errors else None
    update_sync_log(log_id, status, processed, total_articles, error_json)

    result = {"processed": processed, "total_articles": total_articles, "errors": errors}
    print(f"가져오기 완료: {processed}개 지점, {total_articles}건")
    return result


def _parse_header_meta(rows: list) -> dict:
    """시트 Row 1~3에서 메타데이터 추출.

    시트 구조:
      Row 1 (idx 0): [지점명, '', '구분', '정보성', '후기성', '슈퍼세트', ...]
      Row 2 (idx 1): ['스마트 담당자', 이름, '발행건수', '1~10', '', 총건수, ...]
      Row 3 (idx 2): ['원고작가', 작가명, '진행상황', 정보성건수, 후기성건수, 슈퍼세트건수, ...]
    """
    meta = {}

    # Row 2 (idx 1): B열=담당자 이름, F열(idx 5)=발행건수
    if len(rows) > 1:
        r2 = rows[1]
        meta["smart_manager"] = _safe_get(r2, 1)   # B열: 실제 이름
        pub_str = _safe_get(r2, 5)
        if pub_str and pub_str.isdigit():
            meta["publish_count"] = int(pub_str)

    # Row 3 (idx 2): B열=작가명, D열=정보성건수, E열=후기성건수, F열=슈퍼세트건수
    if len(rows) > 2:
        r3 = rows[2]
        meta["writer"] = _safe_get(r3, 1)           # B열: 실제 작가명
        # 정보성/후기성/슈퍼세트 건수
        info_str = _safe_get(r3, 3)
        if info_str and info_str.isdigit():
            meta["review_count"] = int(_safe_get(r3, 4)) if _safe_get(r3, 4).isdigit() else 0
            meta["superset_count"] = int(_safe_get(r3, 5)) if _safe_get(r3, 5).isdigit() else 0
        meta["progress_note"] = _safe_get(r3, 7)    # H열: 지역 정보 등

    # 보고서/댓글침투/사진 링크 (Row 2: G~J열)
    if len(rows) > 1:
        r2 = rows[1]
        meta["report_link"] = _safe_get(r2, 6)        # G열: 보고서링크
        meta["comment_link"] = _safe_get(r2, 7)        # H열: 댓글침투 링크
        meta["photo_link"] = _safe_get(r2, 8)          # I열: 시술사진
        meta["general_photo_link"] = _safe_get(r2, 9)  # J열: 일반사진

    return meta


def _safe_get(row: list, idx: int) -> str:
    """리스트에서 안전하게 값 추출."""
    if idx < len(row):
        val = row[idx]
        return str(val).strip() if val else ""
    return ""


# ============================================================
# CLI 실행
# ============================================================
if __name__ == "__main__":
    # Windows 콘솔 인코딩 대응
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="카페 원고 시트 가져오기")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--branch", type=str, default="", help="특정 지점만 (예: 동탄점)")
    args = parser.parse_args()

    result = run_cafe_import(args.year, args.month, args.branch)
    if result["errors"]:
        print("오류:")
        for e in result["errors"]:
            print(f"  - {e}")
