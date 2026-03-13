"""
Google Sheets → SQLite 동기화 모듈

동기화 규칙 (데이터 안전):
  1. DB 자동 백업 후 동기화 시작
  2. Sheets에 있고 DB에 없는 행 → 새로 추가
  3. Sheets에 있고 DB에도 있고 내용 동일 → 스킵
  4. Sheets에 있고 DB에도 있고 내용 다름 → 로그만 남김 (덮어쓰지 않음)
  5. DB에만 있는 행 (내부 추가분) → 유지
"""

import sqlite3
import pandas as pd
import shutil
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")
BACKUP_DIR = os.path.join(DB_DIR, "backups")

# 사진 있음 판정 값
PHOTO_YES = {"0", "0.0", "1", "1.0", "o", "O", "ㅇ", "있음", "v", "완료", "y", "yes"}

# braw CSV URL (Google Sheets 공개 CSV)
CSV_URL = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vT7kB-eQbBWxfLRB4mCoCfw-2nz7J2QhA5xmiwSxer2U8IPuNdqnm_"
    "-TR2i-BGqwpuoUeW6y8RzRdXV/pub"
    "?gid=1543424723&single=true&output=csv"
)


def backup_db():
    """동기화 전 DB 백업"""
    if not os.path.exists(DB_PATH):
        return None

    os.makedirs(BACKUP_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H%M")
    backup_path = os.path.join(BACKUP_DIR, f"equipment_{today}.db")
    shutil.copy2(DB_PATH, backup_path)

    # 7일 이상 된 백업 삭제
    cutoff = datetime.now().timestamp() - (7 * 86400)
    for f in os.listdir(BACKUP_DIR):
        fpath = os.path.join(BACKUP_DIR, f)
        if os.path.getmtime(fpath) < cutoff:
            os.remove(fpath)

    return backup_path


def fetch_sheets_data():
    """Google Sheets CSV 데이터 가져오기"""
    df = pd.read_csv(CSV_URL, header=1)

    expected_cols = ["순번", "지점명", "카테고리", "기기명", "수량", "비고"]
    available = [c for c in expected_cols if c in df.columns]

    if len(available) < 4:
        cols = df.columns.tolist()
        use_count = min(len(cols), 7)
        df = df.iloc[:, :use_count]
        if use_count == 7:
            df.columns = expected_cols + ["사진"]
        else:
            df.columns = expected_cols[:use_count]
    else:
        if "사진" in df.columns:
            df = df[available + ["사진"]]
        else:
            df = df[available]

    df = df.dropna(subset=["지점명"])

    for col in ["지점명", "카테고리", "기기명"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    if "비고" in df.columns:
        df["비고"] = df["비고"].fillna("").astype(str).str.strip().replace("nan", "")
    else:
        df["비고"] = ""

    if "사진" not in df.columns:
        df["사진"] = ""
    else:
        df["사진"] = df["사진"].fillna("").astype(str).str.strip().replace("nan", "")

    if "수량" in df.columns:
        df["수량"] = pd.to_numeric(df["수량"], errors="coerce").fillna(0).astype(int)

    return df


def get_or_create_branch(cursor, name):
    """지점 조회 또는 생성, ID 반환"""
    cursor.execute("SELECT id FROM branches WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO branches (name) VALUES (?)", (name,))
    return cursor.lastrowid


def get_or_create_category(cursor, name):
    """카테고리 조회 또는 생성, ID 반환"""
    cursor.execute("SELECT id FROM categories WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    return cursor.lastrowid


def sync_from_sheets():
    """Google Sheets → SQLite 동기화 실행"""
    # 1. 백업
    backup_path = backup_db()
    if backup_path:
        print(f"백업 완료: {backup_path}")

    # 2. Sheets 데이터 가져오기
    print("Google Sheets 데이터 가져오는 중...")
    df = fetch_sheets_data()
    print(f"Sheets에서 {len(df)}건 로드 완료")

    # 3. DB 연결
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    added = 0
    skipped = 0
    conflicts = 0
    conflict_details = []

    for _, row in df.iterrows():
        branch_name = str(row["지점명"]).strip()
        category_name = str(row.get("카테고리", "")).strip()
        device_name = str(row.get("기기명", "")).strip()
        quantity = int(row.get("수량", 1))
        note = str(row.get("비고", "")).strip()
        photo_raw = str(row.get("사진", "")).strip()
        photo_status = 1 if photo_raw in PHOTO_YES else 0

        if not branch_name or not device_name or device_name == "nan":
            continue

        # 지점/카테고리 가져오기 또는 생성
        branch_id = get_or_create_branch(c, branch_name)
        category_id = get_or_create_category(c, category_name) if category_name and category_name != "nan" else None

        # DB에 같은 행이 있는지 확인 (지점 + 기기명으로 매칭)
        c.execute("""
            SELECT id, quantity, photo_status, note, category_id
            FROM equipment
            WHERE branch_id = ? AND name = ?
        """, (branch_id, device_name))
        existing = c.fetchone()

        if existing is None:
            # 신규 행 → 추가
            c.execute("""
                INSERT INTO equipment
                    (branch_id, category_id, name, name_original, quantity, photo_status, note, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'sheets')
            """, (branch_id, category_id, device_name, device_name, quantity, photo_status, note))
            added += 1
        else:
            # 기존 행 → 내용 비교
            db_qty, db_photo, db_note, db_cat_id = existing[1], existing[2], existing[3], existing[4]
            if (db_qty == quantity and db_photo == photo_status
                    and (db_note or "") == note and db_cat_id == category_id):
                skipped += 1
            else:
                # 내용 다름 → 덮어쓰지 않고 로그만 남김
                conflicts += 1
                conflict_details.append(
                    f"{branch_name}/{device_name}: "
                    f"DB({db_qty},{db_photo},{db_note}) vs Sheets({quantity},{photo_status},{note})"
                )

    # 4. 동기화 로그 기록
    detail_text = "\n".join(conflict_details[:50]) if conflict_details else None
    c.execute("""
        INSERT INTO sync_log (sync_type, added, skipped, conflicts, detail)
        VALUES (?, ?, ?, ?, ?)
    """, ("sheets_to_db", added, skipped, conflicts, detail_text))

    conn.commit()
    conn.close()

    # 5. 결과 출력
    print(f"\n동기화 완료:")
    print(f"  추가: {added}건")
    print(f"  스킵: {skipped}건 (동일)")
    print(f"  충돌: {conflicts}건 (로그만 기록, 덮어쓰지 않음)")

    if conflict_details:
        print(f"\n충돌 상세 (상위 10건):")
        for detail in conflict_details[:10]:
            print(f"  - {detail}")

    return {"added": added, "skipped": skipped, "conflicts": conflicts}


if __name__ == "__main__":
    sync_from_sheets()
