"""민원 관리 DB 모듈."""
from shared.db import get_conn, EQUIPMENT_DB

ALLOWED_TRANSITIONS = {
    "received": ["processing"],
    "processing": ["resolved", "received"],
    "resolved": ["closed", "processing"],
    "closed": [],
}


def list_complaints(branch_id=None, status=None, page=1, per_page=50):
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT c.*, eb.name as branch_name FROM complaints c LEFT JOIN evt_branches eb ON c.branch_id = eb.id WHERE 1=1"
        params = []
        if branch_id:
            sql += " AND c.branch_id = ?"
            params.append(branch_id)
        if status:
            sql += " AND c.status = ?"
            params.append(status)
        sql += " ORDER BY c.created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def get_complaint(complaint_id):
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute(
            "SELECT c.*, eb.name as branch_name FROM complaints c LEFT JOIN evt_branches eb ON c.branch_id = eb.id WHERE c.id = ?",
            (complaint_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_complaint(data: dict):
    conn = get_conn(EQUIPMENT_DB)
    try:
        c = conn.execute(
            """INSERT INTO complaints (branch_id, title, content, category, severity, reported_by, assigned_to)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data["branch_id"], data["title"], data.get("content", ""),
             data.get("category", ""), data.get("severity", "normal"),
             data.get("reported_by", ""), data.get("assigned_to", ""))
        )
        conn.commit()
        return c.lastrowid
    finally:
        conn.close()


def update_complaint(complaint_id, data: dict):
    conn = get_conn(EQUIPMENT_DB)
    try:
        sets = []
        params = []
        for k in ("title", "content", "category", "severity", "assigned_to", "resolution"):
            if k in data and data[k] is not None:
                sets.append(f"{k} = ?")
                params.append(data[k])
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(complaint_id)
        conn.execute(f"UPDATE complaints SET {', '.join(sets)} WHERE id = ?", params)
        conn.commit()
        return True
    finally:
        conn.close()


def change_status(complaint_id, new_status, changed_by="", note=""):
    conn = get_conn(EQUIPMENT_DB)
    try:
        row = conn.execute("SELECT status FROM complaints WHERE id = ?", (complaint_id,)).fetchone()
        if not row:
            return False, "not found"
        old_status = row["status"]
        allowed = ALLOWED_TRANSITIONS.get(old_status, [])
        if new_status not in allowed:
            return False, f"'{old_status}' -> '{new_status}' transition not allowed"

        resolved_at = "CURRENT_TIMESTAMP" if new_status == "resolved" else "NULL"
        conn.execute(
            f"UPDATE complaints SET status = ?, updated_at = CURRENT_TIMESTAMP, resolved_at = {resolved_at} WHERE id = ?",
            (new_status, complaint_id)
        )
        conn.execute(
            "INSERT INTO complaint_logs (complaint_id, old_status, new_status, changed_by, note) VALUES (?, ?, ?, ?, ?)",
            (complaint_id, old_status, new_status, changed_by, note)
        )
        conn.commit()
        return True, "ok"
    finally:
        conn.close()


def get_complaint_logs(complaint_id):
    conn = get_conn(EQUIPMENT_DB)
    try:
        rows = conn.execute(
            "SELECT * FROM complaint_logs WHERE complaint_id = ? ORDER BY changed_at DESC",
            (complaint_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def count_complaints(branch_id=None):
    conn = get_conn(EQUIPMENT_DB)
    try:
        sql = "SELECT status, COUNT(*) as cnt FROM complaints"
        params = []
        if branch_id:
            sql += " WHERE branch_id = ?"
            params.append(branch_id)
        sql += " GROUP BY status"
        return {r["status"]: r["cnt"] for r in conn.execute(sql, params).fetchall()}
    finally:
        conn.close()
