"""시술 카탈로그 DB 모듈."""
import sqlite3
from shared.db import get_conn, EQUIPMENT_DB


def list_catalog(item_type=None, category=None, search=None):
    """카탈로그 목록 조회."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT * FROM treatment_catalog WHERE is_active = 1"
        params = []
        if item_type:
            sql += " AND item_type = ?"
            params.append(item_type)
        if category:
            sql += " AND category = ?"
            params.append(category)
        if search:
            sql += " AND (item_name LIKE ? OR display_name LIKE ? OR sub_option LIKE ?)"
            params.extend([f"%{search}%"] * 3)
        sql += " ORDER BY category, sort_order, item_name"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def get_catalog_item(item_id):
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute("SELECT * FROM treatment_catalog WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_catalog_item(data: dict):
    conn = get_conn(EQUIPMENT_DB)
    try:
        # 장비명 정제
        from equipment.db import normalize_device_name
        item_name = normalize_device_name(data["item_name"])
        display_name = data["display_name"]
        if data.get("sub_option"):
            display_name = f"{item_name} {data['sub_option']}"
        else:
            display_name = normalize_device_name(display_name)

        # Auto device_id matching for device type
        device_id = data.get("device_id")
        if data.get("item_type") == "device" and not device_id:
            device_id = auto_match_device(item_name)

        c = conn.execute(
            """INSERT INTO treatment_catalog
               (item_type, category, item_name, sub_option, display_name, device_id, description, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["item_type"], data["category"], item_name,
             data.get("sub_option"), display_name,
             device_id, data.get("description", ""), data.get("sort_order", 0))
        )
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def update_catalog_item(item_id, data: dict):
    conn = get_conn(EQUIPMENT_DB)
    try:
        sets = []
        params = []
        for k in ("item_type", "category", "item_name", "sub_option", "display_name", "device_id", "description", "sort_order", "is_active"):
            if k in data and data[k] is not None:
                sets.append(f"{k} = ?")
                params.append(data[k])
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(item_id)
        conn.execute(f"UPDATE treatment_catalog SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        return True
    finally:
        conn.close()


def delete_catalog_item(item_id):
    conn = get_conn(EQUIPMENT_DB)
    try:
        conn.execute("UPDATE treatment_catalog SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def auto_match_device(name: str):
    """장비 이름으로 device_info 자동 매칭."""
    try:
        from equipment.matcher import match_single
        dev_id, _ = match_single(name)
        return dev_id
    except Exception:
        return None


def batch_auto_match():
    """device 타입 항목 전체 자동 매칭."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("SELECT id, item_name FROM treatment_catalog WHERE item_type = 'device' AND device_id IS NULL AND is_active = 1").fetchall()
        matched = 0
        for row in rows:
            dev_id = auto_match_device(row["item_name"])
            if dev_id:
                conn.execute("UPDATE treatment_catalog SET device_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (dev_id, row["id"]))
                matched += 1
        conn.commit()
        return {"total": len(rows), "matched": matched}
    finally:
        conn.close()


def get_categories():
    """카탈로그 카테고리 목록."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute("SELECT DISTINCT category FROM treatment_catalog WHERE is_active = 1 ORDER BY category").fetchall()
        return [r["category"] for r in rows]
    finally:
        conn.close()
