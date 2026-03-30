"""
SQLite DB 읽기/쓰기 모듈
- load_data(), get_branches(), get_categories() 등
- save_photo_changes(), update_equipment() 등 쓰기 기능
"""

import sqlite3
import os
import re


from config import PHOTO_YES, DEVICE_ALIASES

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")


def _get_conn():
    """SQLite 연결 반환 (WAL 모드 + busy_timeout)"""
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row
    return conn


def clean_device_name(name):
    if not name:
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


def load_data():
    """SQLite에서 장비 데이터 로드 → list[dict] 반환"""
    try:
        conn = _get_conn()
        rows = conn.execute("""
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
        """).fetchall()
        conn.close()

        result = []
        for r in rows:
            d = dict(r)
            # 문자열 정리
            for col in ("지점명", "카테고리", "기기명"):
                d[col] = str(d.get(col) or "").strip()
            d["비고"] = str(d.get("비고") or "").strip()
            if d["비고"] == "nan":
                d["비고"] = ""
            d["사진"] = str(d.get("사진") or "").strip()
            d["수량"] = int(d["수량"]) if d.get("수량") else 0
            # 기기명 정규화 + 그룹핑
            d["기기명_원본"] = d["기기명"]
            d["기기명"] = clean_device_name(d["기기명_원본"])
            d["장비그룹"] = get_device_group(d["기기명"])
            result.append(d)

        return result

    except Exception as e:
        print(f"[EQUIPMENT DB ERROR] 데이터를 불러오는 중 오류: {e}")
        return []


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


def find_matching_devices(equip_name):
    """장비명으로 관련 시술 정보를 매칭. equipment.matcher 공용 엔진 사용."""
    _ensure_device_info_table()
    from equipment.matcher import match_devices
    result = match_devices(equip_name)
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
