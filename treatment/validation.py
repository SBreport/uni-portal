"""데이터 검증 리포트 — 시술/장비/콘텐츠 정합성 체크."""

from shared.db import get_conn, EQUIPMENT_DB


def get_validation_report() -> dict:
    """전체 데이터 정합성 검증 리포트."""
    conn = get_conn(EQUIPMENT_DB)
    try:
        report = {
            "unmatched_device_catalog": [],
            "unmatched_cafe_equipment": [],
            "orphan_papers": [],
            "summary": {}
        }

        # 1. treatment_catalog에서 item_type='device'인데 device_id가 NULL인 항목
        rows = conn.execute("""
            SELECT id, category, item_name, display_name
            FROM treatment_catalog
            WHERE item_type = 'device' AND device_id IS NULL AND is_active = 1
        """).fetchall()
        report["unmatched_device_catalog"] = [dict(r) for r in rows]

        # 2. cafe_articles에서 equipment_name이 device_info에 매칭 안 되는 항목
        # cafe_articles is in cafe.db, need to ATTACH
        try:
            import os
            cafe_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cafe.db")
            if os.path.exists(cafe_db):
                conn.execute(f"ATTACH DATABASE '{cafe_db}' AS cafe_db")
                rows = conn.execute("""
                    SELECT ca.id, ca.equipment_name, ca.title
                    FROM cafe_db.cafe_articles ca
                    WHERE ca.equipment_name != ''
                    AND ca.equipment_name IS NOT NULL
                    AND ca.equipment_name NOT IN (SELECT name FROM device_info)
                    AND ca.equipment_name NOT IN (SELECT aliases FROM device_info WHERE aliases != '')
                    LIMIT 50
                """).fetchall()
                report["unmatched_cafe_equipment"] = [dict(r) for r in rows]
                conn.execute("DETACH DATABASE cafe_db")
        except Exception:
            # cafe.db가 없거나 접근 불가 시 건너뜀
            pass

        # 3. papers에서 device_info_id가 NULL인 항목
        rows = conn.execute("""
            SELECT id, title, title_ko
            FROM papers
            WHERE device_info_id IS NULL AND status != 'deleted'
        """).fetchall()
        report["orphan_papers"] = [dict(r) for r in rows]

        # 4. 요약 통계
        tc_total = conn.execute("SELECT COUNT(*) FROM treatment_catalog WHERE is_active = 1").fetchone()[0]
        tc_device = conn.execute("SELECT COUNT(*) FROM treatment_catalog WHERE item_type = 'device' AND is_active = 1").fetchone()[0]
        tc_matched = conn.execute("SELECT COUNT(*) FROM treatment_catalog WHERE item_type = 'device' AND device_id IS NOT NULL AND is_active = 1").fetchone()[0]
        papers_total = conn.execute("SELECT COUNT(*) FROM papers WHERE status != 'deleted'").fetchone()[0]
        papers_linked = conn.execute("SELECT COUNT(*) FROM papers WHERE device_info_id IS NOT NULL AND status != 'deleted'").fetchone()[0]

        report["summary"] = {
            "catalog_total": tc_total,
            "catalog_devices": tc_device,
            "catalog_devices_matched": tc_matched,
            "catalog_match_rate": round(tc_matched / tc_device * 100, 1) if tc_device > 0 else 0,
            "papers_total": papers_total,
            "papers_linked": papers_linked,
            "papers_link_rate": round(papers_linked / papers_total * 100, 1) if papers_total > 0 else 0,
            "unmatched_device_count": len(report["unmatched_device_catalog"]),
            "unmatched_cafe_count": len(report["unmatched_cafe_equipment"]),
            "orphan_papers_count": len(report["orphan_papers"]),
        }

        return report
    finally:
        conn.close()
