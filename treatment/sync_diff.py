"""이벤트 동기화 후 신규/삭제 항목 감지 + 미태깅 항목 자동 추천.

동기화 → extract_tags → sync_diff 순으로 실행.
"""

import sqlite3
import logging
from datetime import datetime
from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)


def detect_diff_and_recommend():
    """신규/삭제 감지 + 미태깅 항목에 자동 태그 추천.

    Returns:
        {
            "new_items": [...],       # 이번 동기화에서 새로 나타난 시술명
            "removed_items": [...],   # 이전에 있었는데 사라진 시술명
            "untagged_recommended": [...],  # 미태깅인데 자동 추천 가능한 것
            "untagged_unknown": [...],      # 완전 미태깅 (추천 불가)
        }
    """
    conn = get_conn(EQUIPMENT_DB)
    conn.row_factory = sqlite3.Row

    # ── 테이블 생성 ──
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS encyclopedia_pending (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL CHECK(action IN ('new','removed','recommend')),
            source_name TEXT NOT NULL,
            raw_category TEXT DEFAULT '',
            recommended_tags TEXT DEFAULT '',
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','dismissed')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_ep_status ON encyclopedia_pending(status);

        CREATE TABLE IF NOT EXISTS encyclopedia_snapshot (
            source_name TEXT NOT NULL,
            raw_category TEXT DEFAULT '',
            snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ── 1. 현재 evt_items 시술명 목록 ──
    current = conn.execute("""
        SELECT DISTINCT raw_event_name, raw_category
        FROM evt_items
        WHERE raw_event_name IS NOT NULL AND raw_event_name != ''
    """).fetchall()
    current_set = {(r["raw_event_name"], r["raw_category"] or "") for r in current}

    # ── 2. 이전 스냅샷과 비교 ──
    prev = conn.execute("SELECT source_name, raw_category FROM encyclopedia_snapshot").fetchall()
    prev_set = {(r["source_name"], r["raw_category"] or "") for r in prev}

    new_items = current_set - prev_set
    removed_items = prev_set - current_set

    # ── 3. 스냅샷 갱신 ──
    conn.execute("DELETE FROM encyclopedia_snapshot")
    for name, cat in current_set:
        conn.execute(
            "INSERT INTO encyclopedia_snapshot (source_name, raw_category) VALUES (?, ?)",
            (name, cat)
        )

    # ── 4. 미태깅 항목 찾기 ──
    tagged_names = set(r[0] for r in conn.execute(
        "SELECT DISTINCT source_name FROM treatment_body_tags WHERE source = 'evt_items'"
    ).fetchall())

    all_names = set(r[0] for r in current)
    untagged = all_names - tagged_names

    # ── 5. 미태깅 항목에 자동 추천 ──
    # 카테고리 → 목적 매핑 (이벤트 raw_category에서 추론)
    CATEGORY_PURPOSE_MAP = {
        "스킨부스터": "보습/광채",
        "보톡스": "축소/윤곽",
        "보톡스/윤곽": "축소/윤곽",
        "필러": "볼륨",
        "색소": "색소/미백",
        "기미": "색소/미백",
        "스킨케어": "필링/각질",
        "여드름": "여드름/모공",
        "제모": "제모",
        "비만": "체형/다이어트",
        "다이어트": "체형/다이어트",
        "활력주사": "활력주사",
        "윤곽": "축소/윤곽",
        "리프팅": "탄력/리프팅",
        "레이저리프팅": "탄력/리프팅",
        "레이저 리프팅": "탄력/리프팅",
        "실리프팅": "탄력/리프팅",
        "쁘띠": "볼륨",
    }

    # 기존 태깅된 장비/재료 사전 (이름 → 태그)
    known_equip = {}
    for r in conn.execute("""
        SELECT DISTINCT tag_value, tag_type FROM treatment_body_tags
        WHERE tag_type IN ('equipment', 'material')
    """).fetchall():
        known_equip[r["tag_value"]] = r["tag_type"]

    recommended = []
    unknown = []

    for name in untagged:
        # 이 시술명의 카테고리 가져오기
        cat_row = conn.execute(
            "SELECT raw_category FROM evt_items WHERE raw_event_name = ? LIMIT 1",
            (name,)
        ).fetchone()
        raw_cat = cat_row["raw_category"] if cat_row else ""

        tags = []

        # 카테고리에서 목적 추론
        for cat_key, purpose in CATEGORY_PURPOSE_MAP.items():
            if cat_key in (raw_cat or ""):
                tags.append(f"목적:{purpose}")
                break

        # 시술명에서 알려진 장비/재료 매칭
        for eq_name, eq_type in known_equip.items():
            if eq_name.lower() in name.lower():
                label = "장비" if eq_type == "equipment" else "재료"
                tags.append(f"{label}:{eq_name}")

        if tags:
            recommended.append({
                "name": name,
                "raw_category": raw_cat,
                "recommended_tags": ", ".join(tags),
            })
        else:
            unknown.append({"name": name, "raw_category": raw_cat})

    # ── 6. pending 테이블에 기록 ──
    # 기존 pending 중 resolved 안 된 것 정리
    now = datetime.now().isoformat()

    for name, cat in new_items:
        conn.execute("""
            INSERT INTO encyclopedia_pending (action, source_name, raw_category, status, created_at)
            VALUES ('new', ?, ?, 'pending', ?)
        """, (name, cat, now))

    for name, cat in removed_items:
        conn.execute("""
            INSERT INTO encyclopedia_pending (action, source_name, raw_category, status, created_at)
            VALUES ('removed', ?, ?, 'pending', ?)
        """, (name, cat, now))

    for item in recommended:
        conn.execute("""
            INSERT INTO encyclopedia_pending (action, source_name, raw_category, recommended_tags, status, created_at)
            VALUES ('recommend', ?, ?, ?, 'pending', ?)
        """, (item["name"], item["raw_category"], item["recommended_tags"], now))

    conn.commit()
    conn.close()

    result = {
        "ok": True,
        "new_items": len(new_items),
        "removed_items": len(removed_items),
        "untagged_recommended": len(recommended),
        "untagged_unknown": len(unknown),
    }
    logger.info(f"[sync_diff] {result}")
    return result


def approve_pending(pending_id: int):
    """pending 항목을 승인 → 추천 태그를 treatment_body_tags에 반영."""
    from treatment.extract_tags import BODY_PARTS, PURPOSES, extract_tags_from_name, _load_equipment_names

    conn = get_conn(EQUIPMENT_DB)
    conn.row_factory = sqlite3.Row

    row = conn.execute("SELECT * FROM encyclopedia_pending WHERE id = ?", (pending_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "항목 없음"}

    if row["action"] == "recommend" and row["recommended_tags"]:
        # 추천 태그를 파싱해서 treatment_body_tags에 삽입
        name = row["source_name"]
        # source_id 찾기
        item_row = conn.execute(
            "SELECT MIN(id) as sid FROM evt_items WHERE raw_event_name = ?", (name,)
        ).fetchone()
        source_id = item_row["sid"] if item_row else 0

        for tag_str in row["recommended_tags"].split(", "):
            if ":" not in tag_str:
                continue
            tag_type_label, tag_value = tag_str.split(":", 1)
            tag_type_map = {"목적": "purpose", "장비": "equipment", "재료": "material", "부위": "body_part"}
            tag_type = tag_type_map.get(tag_type_label, "purpose")

            # 카테고리 결정
            tag_category = ""
            if tag_type == "purpose":
                tag_category = tag_value
            elif tag_type == "body_part":
                tag_category = BODY_PARTS.get(tag_value, "")
            elif tag_type in ("equipment", "material"):
                tag_category = tag_type_label

            conn.execute("""
                INSERT INTO treatment_body_tags (source, source_id, source_name, tag_type, tag_value, tag_category)
                VALUES ('evt_items', ?, ?, ?, ?, ?)
            """, (source_id, name, tag_type, tag_value, tag_category))

    conn.execute("""
        UPDATE encyclopedia_pending SET status = 'approved', resolved_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), pending_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def dismiss_pending(pending_id: int):
    """pending 항목 무시."""
    conn = get_conn(EQUIPMENT_DB)
    conn.execute("""
        UPDATE encyclopedia_pending SET status = 'dismissed', resolved_at = ? WHERE id = ?
    """, (datetime.now().isoformat(), pending_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def approve_all_recommended():
    """추천 태그가 있는 pending 항목 전체 일괄 승인."""
    conn = get_conn(EQUIPMENT_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT id FROM encyclopedia_pending
        WHERE action = 'recommend' AND status = 'pending'
    """).fetchall()
    conn.close()

    count = 0
    for r in rows:
        approve_pending(r["id"])
        count += 1

    return {"ok": True, "approved": count}
