"""
SQLite DB 읽기/쓰기 모듈
- publish/data.py 와 동일한 인터페이스 제공
- load_data(), apply_photo_status(), apply_filters()
- save_photo_changes(), update_equipment() 등 쓰기 기능 추가
"""

import sqlite3
import os
import re
import pandas as pd

try:
    import streamlit as st
    _cache = st.cache_data
except (ImportError, ModuleNotFoundError):
    st = None
    _cache = lambda **kw: lambda f: f  # no-op decorator

from config import PHOTO_YES, DEVICE_ALIASES

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")


def _get_conn():
    """SQLite 연결 반환 (WAL 모드)"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def clean_device_name(name):
    if pd.isna(name):
        return ""
    name = str(name).strip()
    cleaned = re.sub(r"^\d+\.?\s+", "", name)
    return cleaned.strip()


def get_device_group(clean_name):
    lower = clean_name.lower()
    for group, patterns in DEVICE_ALIASES.items():
        for pattern in patterns:
            if pattern.lower() in lower:
                return group
    return clean_name


@_cache(ttl=300)
def load_data():
    """SQLite에서 장비 데이터 로드 → DataFrame 반환"""
    try:
        conn = _get_conn()
        query = """
            SELECT
                e.id        AS 순번,
                b.name      AS 지점명,
                COALESCE(c.name, '') AS 카테고리,
                e.name      AS 기기명,
                e.quantity   AS 수량,
                e.note       AS 비고,
                CASE WHEN e.photo_status = 1 THEN 'O' ELSE '' END AS 사진
            FROM equipment e
            JOIN branches b ON e.branch_id = b.id
            LEFT JOIN categories c ON e.category_id = c.id
            ORDER BY b.name, e.id
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        # 빈 문자열 정리
        for col in ["지점명", "카테고리", "기기명"]:
            df[col] = df[col].astype(str).str.strip()
        df["비고"] = df["비고"].fillna("").astype(str).str.strip().replace("nan", "")
        df["사진"] = df["사진"].fillna("").astype(str).str.strip()

        if "수량" in df.columns:
            df["수량"] = pd.to_numeric(df["수량"], errors="coerce").fillna(0).astype(int)

        # 기기명 정규화 + 그룹핑
        df["기기명_원본"] = df["기기명"]
        df["기기명"] = df["기기명_원본"].apply(clean_device_name)
        df["장비그룹"] = df["기기명"].apply(get_device_group)

        return df

    except Exception as e:
        if st:
            st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
            st.info("DB 파일을 확인해주세요.")
        return pd.DataFrame(
            columns=["순번", "지점명", "카테고리", "기기명", "기기명_원본", "장비그룹", "수량", "비고", "사진"]
        )


def apply_photo_status(df):
    """사진유무 컬럼 추가"""
    df = df.copy()
    df["사진유무"] = df["사진"].apply(
        lambda x: "있음" if str(x).strip() in PHOTO_YES else "없음"
    )
    return df


def apply_filters(df, branches, categories, search, photo_filter):
    """필터 적용"""
    filtered = df.copy()

    if branches:
        filtered = filtered[filtered["지점명"].isin(branches)]

    if categories:
        filtered = filtered[filtered["카테고리"].isin(categories)]

    if search:
        mask = (
            filtered["기기명"].str.contains(search, case=False, na=False)
            | filtered["장비그룹"].str.contains(search, case=False, na=False)
            | filtered["비고"].str.contains(search, case=False, na=False)
        )
        filtered = filtered[mask]

    if photo_filter == "사진 없음만":
        filtered = filtered[filtered["사진유무"] == "없음"]
    elif photo_filter == "사진 있음만":
        filtered = filtered[filtered["사진유무"] == "있음"]

    return filtered


# ============================================================
# 쓰기 기능 (NAS 전용)
# ============================================================

def save_photo_changes(changes):
    """
    사진 상태 일괄 업데이트
    changes: list of (equipment_id, new_photo_status)
    returns: (성공 건수, 에러 목록)
    """
    conn = _get_conn()
    c = conn.cursor()
    ok = 0
    errors = []

    for eq_id, photo_val in changes:
        try:
            status = 1 if str(photo_val).strip() in PHOTO_YES else 0
            c.execute(
                "UPDATE equipment SET photo_status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, eq_id),
            )
            ok += 1
        except Exception as e:
            errors.append(f"ID {eq_id}: {e}")

    conn.commit()
    conn.close()
    return ok, errors


def update_equipment(eq_id, **fields):
    """
    장비 개별 필드 업데이트
    fields: quantity, note, photo_status, category_id 등
    """
    if not fields:
        return
    conn = _get_conn()
    c = conn.cursor()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [eq_id]
    c.execute(
        f"UPDATE equipment SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        values,
    )
    conn.commit()
    conn.close()


def get_sync_log(limit=10):
    """최근 동기화 로그 조회"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM sync_log ORDER BY synced_at DESC LIMIT ?", (limit,)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_branches():
    """전체 지점 목록"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name FROM branches ORDER BY name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_branch_name(branch_id):
    """branch_id로 지점명 조회. 없으면 None."""
    if branch_id is None:
        return None
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT name FROM branches WHERE id = ?", (branch_id,))
    row = c.fetchone()
    conn.close()
    return row["name"] if row else None


def get_categories():
    """전체 카테고리 목록"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


# ============================================================
# 시술/장비 정보 사전 (device_info)
# ============================================================

def _ensure_device_info_table():
    """device_info 테이블이 없으면 생성 (자동 마이그레이션)"""
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS device_info (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        category    TEXT DEFAULT '',
        summary     TEXT DEFAULT '',
        target      TEXT DEFAULT '',
        mechanism   TEXT DEFAULT '',
        note        TEXT DEFAULT '',
        aliases     TEXT DEFAULT '',
        usage_count INTEGER DEFAULT 0,
        is_verified INTEGER DEFAULT 0,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


def get_all_device_info():
    """전체 시술 정보 목록 조회"""
    _ensure_device_info_table()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM device_info ORDER BY usage_count DESC, name")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_device_info_by_name(name):
    """이름으로 시술 정보 조회 (정확 매칭)"""
    _ensure_device_info_table()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM device_info WHERE name = ?", (name,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


@_cache(ttl=300)
def search_device_info(keyword):
    """키워드로 시술 정보 검색 (이름 + aliases 부분 매칭)"""
    _ensure_device_info_table()
    conn = _get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM device_info WHERE name LIKE ? OR aliases LIKE ? ORDER BY usage_count DESC",
        (f"%{keyword}%", f"%{keyword}%"),
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def _is_hangul(ch):
    """한글 완성형 음절인지 확인"""
    return '\uAC00' <= ch <= '\uD7A3'


def _is_safe_substring(short, long_str):
    """short가 long_str의 부분문자열일 때, 경계가 안전한지 확인.

    한글 바로 뒤에 한글이 이어지면 다른 단어일 가능성 높음 (울쎄라 ⊂ 울쎄라피).
    영문/숫자/공백이 이어지면 모델 변형일 가능성 높음 (써마지 ⊂ 써마지FLX).
    """
    idx = long_str.find(short)
    if idx < 0:
        return False

    # 앞쪽 경계: short 앞에 한글이 붙어있으면 위험
    if idx > 0 and _is_hangul(long_str[idx - 1]) and _is_hangul(short[0]):
        return False

    # 뒤쪽 경계: short 뒤에 한글이 바로 이어지면 위험
    end_idx = idx + len(short)
    if end_idx < len(long_str) and _is_hangul(long_str[end_idx]) and _is_hangul(short[-1]):
        return False

    return True


@_cache(ttl=300)
def find_matching_devices(equip_name):
    """장비명으로 관련 시술 정보를 양방향 부분 매칭으로 찾기.

    매칭 규칙 (우선순위):
    1. 정확 매칭: DB name == equip_name
    2. 포함 매칭: equip_name이 DB name을 포함 (써마지FLX → 써마지)
    3. 역방향 매칭: DB name이 equip_name을 포함 (써마지 검색 → 써마지FLX)
    4. aliases 매칭: DB aliases 중 하나가 부분 매칭

    한글 경계 규칙: 부분 매칭 시 경계에 한글이 이어지면 스킵
    (울쎄라 ≠ 울쎄라피, 써마지 = 써마지FLX)
    """
    _ensure_device_info_table()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM device_info ORDER BY usage_count DESC, name")
    all_rows = [dict(r) for r in c.fetchall()]
    conn.close()

    equip_lower = equip_name.lower().strip()
    if not equip_lower:
        return []

    exact = []
    contains = []  # equip_name contains DB name
    reverse = []   # DB name contains equip_name
    alias_match = []

    for row in all_rows:
        db_name_lower = row["name"].lower().strip()
        # 1. 정확 매칭
        if db_name_lower == equip_lower:
            exact.append(row)
            continue
        # 2. 장비명이 DB 시술명을 포함 (써마지FLX → 써마지)
        if len(db_name_lower) >= 2 and db_name_lower in equip_lower:
            if _is_safe_substring(db_name_lower, equip_lower):
                contains.append(row)
            continue
        # 3. DB 시술명이 장비명을 포함 (써마지 → 써마지FLX)
        if len(equip_lower) >= 2 and equip_lower in db_name_lower:
            if _is_safe_substring(equip_lower, db_name_lower):
                reverse.append(row)
            continue
        # 4. aliases 매칭
        aliases_str = (row.get("aliases") or "").lower()
        if aliases_str:
            for alias in aliases_str.split(","):
                alias = alias.strip()
                if not alias:
                    continue
                if alias in equip_lower or equip_lower in alias:
                    alias_match.append(row)
                    break

    # 중복 제거하면서 우선순위 유지
    seen = set()
    result = []
    for row in exact + contains + reverse + alias_match:
        if row["name"] not in seen:
            seen.add(row["name"])
            result.append(row)
    return result


def upsert_device_info(name, category="", summary="", target="", mechanism="", note="", aliases="", usage_count=0, is_verified=0):
    """시술 정보 추가 또는 업데이트 (upsert)"""
    _ensure_device_info_table()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT id FROM device_info WHERE name = ?", (name,))
    existing = c.fetchone()
    if existing:
        c.execute("""
            UPDATE device_info SET category=?, summary=?, target=?, mechanism=?, note=?,
                aliases=?, usage_count=?, is_verified=?, updated_at=CURRENT_TIMESTAMP
            WHERE name=?
        """, (category, summary, target, mechanism, note, aliases, usage_count, is_verified, name))
    else:
        c.execute("""
            INSERT INTO device_info (name, category, summary, target, mechanism, note, aliases, usage_count, is_verified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, category, summary, target, mechanism, note, aliases, usage_count, is_verified))
    conn.commit()
    conn.close()


def delete_device_info(name):
    """시술 정보 삭제"""
    _ensure_device_info_table()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM device_info WHERE name = ?", (name,))
    conn.commit()
    conn.close()


def seed_device_info_from_json():
    """data/device_master.json의 장비 데이터를 DB로 이관 (기존 데이터 있으면 업데이트)"""
    import json, os
    _ensure_device_info_table()
    master_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "data", "device_master.json")
    if not os.path.exists(master_path):
        return

    with open(master_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    devices = data.get("devices", [])
    for dev in devices:
        aliases_str = ", ".join(dev.get("aliases", []))
        is_verified = 1 if dev.get("is_verified", False) else 0
        upsert_device_info(
            name=dev["name"],
            category=dev.get("category", ""),
            summary=dev.get("summary", ""),
            target=dev.get("target", ""),
            mechanism=dev.get("mechanism", ""),
            note=dev.get("note", ""),
            aliases=aliases_str,
            is_verified=is_verified,
        )


# 하위 호환: 기존 호출부가 있을 경우 대비
seed_device_info_from_config = seed_device_info_from_json


def update_device_usage_counts():
    """장비 테이블 기준으로 각 시술의 사용 빈도(보유 지점 수) 업데이트"""
    _ensure_device_info_table()
    conn = _get_conn()
    c = conn.cursor()

    c.execute("SELECT id, name, aliases FROM device_info")
    devices = c.fetchall()

    for device in devices:
        dev_name = device["name"]
        aliases = device["aliases"].split(", ") if device["aliases"] else []
        keywords = [dev_name] + aliases

        total = 0
        for kw in keywords:
            if len(kw) >= 2:
                c.execute("SELECT COUNT(*) FROM equipment WHERE name LIKE ?", (f"%{kw}%",))
                total += c.fetchone()[0]

        c.execute("UPDATE device_info SET usage_count = ? WHERE id = ?", (total, device["id"]))

    conn.commit()
    conn.close()
