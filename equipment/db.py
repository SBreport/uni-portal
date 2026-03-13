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
import streamlit as st

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


@st.cache_data(ttl=300)
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
