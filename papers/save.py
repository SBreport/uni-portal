"""
논문 분석 결과를 DB에 저장하는 스크립트.
Claude Code 세션에서 분석 후 이 스크립트를 호출하여 저장.

사용법:
  python papers/save.py result.json
  python papers/save.py --check-duplicate "논문 제목 또는 DOI"
  python papers/save.py --list-devices
  python papers/save.py --match-technology "HIFU"
"""

import sys
import os
import json
import sqlite3
import hashlib
from datetime import datetime

# 프로젝트 루트 기준 경로
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "equipment.db")
sys.path.insert(0, PROJECT_ROOT)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def check_duplicate(title_or_doi: str):
    """DOI 또는 제목으로 중복 체크."""
    conn = get_conn()
    query = title_or_doi.strip()

    # DOI 체크
    if query.startswith("10."):
        row = conn.execute(
            "SELECT id, title_ko, doi FROM papers WHERE doi = ?", (query,)
        ).fetchone()
        if row:
            print(f"[중복] #{row['id']} — {row['title_ko']}")
            print(f"  DOI: {row['doi']}")
            conn.close()
            return True

    # 제목 체크
    rows = conn.execute(
        "SELECT id, title, title_ko FROM papers WHERE status != 'deleted'"
    ).fetchall()
    query_norm = query.lower().replace(" ", "")
    for r in rows:
        if query_norm in (r["title"] or "").lower().replace(" ", ""):
            print(f"[중복] #{r['id']} — {r['title_ko'] or r['title']}")
            conn.close()
            return True
        if query_norm in (r["title_ko"] or "").lower().replace(" ", ""):
            print(f"[중복] #{r['id']} — {r['title_ko']}")
            conn.close()
            return True

    print("[OK] 중복 없음")
    conn.close()
    return False


def list_devices(keyword: str = ""):
    """장비 목록 출력 (검색 가능)."""
    conn = get_conn()
    if keyword:
        rows = conn.execute(
            """SELECT id, name, category, aliases, mechanism
               FROM device_info
               WHERE name LIKE ? OR aliases LIKE ? OR mechanism LIKE ? OR category LIKE ?
               ORDER BY usage_count DESC, name""",
            (f"%{keyword}%",) * 4,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, category FROM device_info ORDER BY usage_count DESC, name"
        ).fetchall()

    for r in rows:
        print(f"  id={r['id']:3d} | {r['name']:20s} | {r['category']}")
    print(f"\n총 {len(rows)}건")
    conn.close()


def match_technology(keyword: str):
    """기술 키워드로 관련 장비 검색."""
    from equipment.matcher import match_by_technology

    results = match_by_technology(keyword)
    if results:
        print(f"'{keyword}' 기술 관련 장비 ({len(results)}건):")
        for r in results:
            print(f"  ✅ {r['name']} (id={r['id']})")
    else:
        print(f"'{keyword}' 관련 장비 없음")
    return results


def save_paper(json_path: str):
    """JSON 파일에서 논문 데이터를 읽어 DB에 저장."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 단일 객체면 리스트로 감싸기
    papers = data if isinstance(data, list) else [data]

    conn = get_conn()
    now = datetime.now().isoformat()
    created = 0

    for p in papers:
        # 중복 체크
        doi = p.get("doi", "")
        if doi:
            existing = conn.execute(
                "SELECT id FROM papers WHERE doi = ?", (doi,)
            ).fetchone()
            if existing:
                print(f"[SKIP] DOI 중복: {doi} (기존 #{existing['id']})")
                continue

        # papers 테이블 저장
        cursor = conn.execute(
            """INSERT INTO papers (
                device_info_id, treatment_id, doi, title, title_ko,
                authors, journal, pub_year, pub_date,
                abstract_summary, key_findings, keywords,
                evidence_level, study_type, sample_size,
                source_url, source_file, status,
                one_line_summary, research_purpose, study_design_detail,
                key_results, conclusion, quotable_stats, cautions, follow_up_period,
                file_hash, easy_summary, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                p.get("device_info_id"),
                p.get("treatment_id"),
                doi,
                p.get("title", ""),
                p.get("title_ko", ""),
                p.get("authors", ""),
                p.get("journal", ""),
                p.get("pub_year"),
                p.get("pub_date", ""),
                p.get("one_line_summary", ""),
                p.get("key_findings", ""),
                json.dumps(p.get("keywords", []), ensure_ascii=False),
                p.get("evidence_level", 0),
                p.get("study_type", ""),
                p.get("sample_size", ""),
                p.get("source_url", ""),
                p.get("source_file", ""),
                p.get("status", "draft"),
                p.get("one_line_summary", ""),
                p.get("research_purpose", ""),
                p.get("study_design_detail", ""),
                p.get("key_results", ""),
                p.get("conclusion", ""),
                json.dumps(p.get("quotable_stats", []), ensure_ascii=False),
                p.get("cautions", ""),
                p.get("follow_up_period", ""),
                p.get("file_hash", ""),
                p.get("easy_summary", ""),
                now,
                now,
            ),
        )
        paper_id = cursor.lastrowid

        # paper_devices 다대다 연결
        device_matches = p.get("device_matches", [])
        for dm in device_matches:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO paper_devices
                       (paper_id, device_info_id, match_type, match_keyword, is_verified, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        paper_id,
                        dm["device_info_id"],
                        dm.get("match_type", "direct"),
                        dm.get("match_keyword", ""),
                        dm.get("is_verified", 1),
                        now,
                    ),
                )
            except Exception as e:
                print(f"  [연결 오류] {e}")

        direct_count = sum(1 for m in device_matches if m.get("match_type") == "direct")
        tech_count = sum(1 for m in device_matches if m.get("match_type") == "technology")
        print(
            f"[저장] #{paper_id} | {p.get('title_ko', '')[:50]} | "
            f"장비 직접:{direct_count} 기술:{tech_count}"
        )
        created += 1

    conn.commit()
    conn.close()
    print(f"\n총 {created}건 저장 완료")
    return created


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    if sys.argv[1] == "--check-duplicate":
        check_duplicate(sys.argv[2] if len(sys.argv) > 2 else "")
    elif sys.argv[1] == "--list-devices":
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        list_devices(keyword)
    elif sys.argv[1] == "--match-technology":
        match_technology(sys.argv[2] if len(sys.argv) > 2 else "")
    else:
        save_paper(sys.argv[1])


if __name__ == "__main__":
    main()
