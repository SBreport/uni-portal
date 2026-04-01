"""논문(papers) 쿼리 모듈.

equipment.db의 papers / device_info / evt_treatments 테이블 조회.
"""

from shared.db import get_conn, EQUIPMENT_DB, now_str


def _conn():
    return get_conn(EQUIPMENT_DB)


# ── 연구유형 대분류 매핑 ──

STUDY_TYPE_MAP = {
    "RCT": ["RCT", "Randomized", "무작위", "이중맹검", "단맹검", "split-face", "split-body", "intraindividual"],
    "코호트/관찰연구": ["코호트", "cohort", "관찰", "observ", "전향적", "후향적", "prospective", "retrospective", "pilot"],
    "증례보고/시리즈": ["증례", "case", "Case"],
    "체계적문헌고찰": ["체계적", "systematic", "메타분석", "meta-analy"],
    "기초연구": ["기초", "basic", "in vitro", "ex vivo", "동물", "animal", "전임상", "체외", "실험"],
    "리뷰/가이드라인": ["리뷰", "review", "Review", "종설", "guideline", "해설", "commentary", "narrative"],
    "설문/기타": ["설문", "survey", "quasi", "비교실험", "기술 비교"],
}


def classify_study_type(raw: str) -> str:
    if not raw:
        return "기타"
    for category, keywords in STUDY_TYPE_MAP.items():
        for kw in keywords:
            if kw.lower() in raw.lower():
                return category
    return "기타"


# ── 장비 목록 (필터 드롭다운용) ──

def get_devices_summary() -> list:
    conn = _conn()
    try:
        rows = conn.execute("""
            SELECT d.id, d.name, COUNT(p.id) AS paper_count
            FROM device_info d
            INNER JOIN papers p ON p.device_info_id = d.id
            GROUP BY d.id, d.name
            ORDER BY paper_count DESC, d.name
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── 연구유형 목록 ──

def get_study_types() -> list:
    conn = _conn()
    try:
        rows = conn.execute("""
            SELECT study_type FROM papers
            WHERE study_type IS NOT NULL AND study_type != ''
        """).fetchall()
    finally:
        conn.close()

    counts: dict[str, int] = {}
    for r in rows:
        cat = classify_study_type(r[0])
        counts[cat] = counts.get(cat, 0) + 1

    result = [{"study_type": k, "cnt": v} for k, v in counts.items()]
    result.sort(key=lambda x: -x["cnt"])
    return result


# ── 목록 조회 ──

_BASE_SELECT = """
    SELECT p.*,
           d.name AS device_name,
           t.name AS treatment_name,
           t.brand AS treatment_brand
    FROM papers p
    LEFT JOIN device_info d ON d.id = p.device_info_id
    LEFT JOIN evt_treatments t ON t.id = p.treatment_id
"""


def list_papers(*, device_info_id=None, treatment_id=None, status=None,
                evidence_level=None, evidence_min=None, study_type=None, q=None) -> list:
    conn = _conn()
    try:
        sql = _BASE_SELECT + " WHERE 1=1"
        params = []

        if device_info_id:
            sql += " AND p.device_info_id = ?"
            params.append(device_info_id)
        if treatment_id:
            sql += " AND p.treatment_id = ?"
            params.append(treatment_id)
        if status:
            sql += " AND p.status = ?"
            params.append(status)
        if evidence_level is not None:
            sql += " AND p.evidence_level = ?"
            params.append(evidence_level)
        if evidence_min is not None:
            sql += " AND p.evidence_level >= ?"
            params.append(evidence_min)
        if study_type:
            keywords = STUDY_TYPE_MAP.get(study_type, [])
            if keywords:
                like_clauses = " OR ".join("p.study_type LIKE ?" for _ in keywords)
                sql += f" AND ({like_clauses})"
                params.extend(f"%{kw}%" for kw in keywords)
            else:
                sql += " AND p.study_type = ?"
                params.append(study_type)
        if q:
            sql += """ AND (p.title LIKE ? OR p.title_ko LIKE ? OR p.authors LIKE ?
                            OR p.key_findings LIKE ? OR p.one_line_summary LIKE ?
                            OR p.keywords LIKE ? OR d.name LIKE ? OR d.aliases LIKE ?)"""
            like = f"%{q}%"
            params.extend([like] * 8)

        sql += " ORDER BY p.pub_year DESC, p.created_at DESC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── 단건 조회 ──

def get_paper(paper_id: int) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute(_BASE_SELECT + " WHERE p.id = ?", (paper_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ── 생성 ──

_INSERT_SQL = """
    INSERT INTO papers (
        device_info_id, treatment_id, doi, title, title_ko,
        authors, journal, pub_year, pub_date,
        abstract_summary, key_findings, keywords,
        evidence_level, study_type, sample_size,
        source_url, source_file, status,
        one_line_summary, research_purpose, study_design_detail,
        key_results, conclusion, quotable_stats, cautions, follow_up_period,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _paper_values(data, now: str) -> tuple:
    return (
        data.device_info_id, data.treatment_id, data.doi, data.title, data.title_ko,
        data.authors, data.journal, data.pub_year, data.pub_date,
        data.abstract_summary, data.key_findings, data.keywords,
        data.evidence_level, data.study_type, data.sample_size,
        data.source_url, data.source_file, data.status,
        data.one_line_summary, data.research_purpose, data.study_design_detail,
        data.key_results, data.conclusion, data.quotable_stats, data.cautions, data.follow_up_period,
        now, now,
    )


def create_paper(data) -> int:
    conn = _conn()
    try:
        now = now_str()
        cur = conn.execute(_INSERT_SQL, _paper_values(data, now))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ── 수정 ──

def update_paper(paper_id: int, updates: dict) -> bool:
    conn = _conn()
    try:
        existing = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if not existing:
            return False
        if not updates:
            return True

        updates["updated_at"] = now_str()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [paper_id]
        conn.execute(f"UPDATE papers SET {set_clause} WHERE id = ?", values)
        conn.commit()
        return True
    finally:
        conn.close()


# ── 삭제 ──

def delete_paper(paper_id: int) -> bool:
    conn = _conn()
    try:
        existing = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# ── 장비/시술별 조회 ──

_DETAIL_COLS = """id, title, title_ko, authors, journal, pub_year,
    abstract_summary, key_findings, evidence_level, study_type, source_url,
    one_line_summary, research_purpose, study_design_detail,
    key_results, conclusion, quotable_stats, cautions, follow_up_period"""


def papers_by_device(device_info_id: int) -> list:
    conn = _conn()
    try:
        rows = conn.execute(f"""
            SELECT {_DETAIL_COLS} FROM papers
            WHERE device_info_id = ? AND status != 'deleted'
            ORDER BY evidence_level DESC, pub_year DESC
        """, (device_info_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def papers_by_treatment(treatment_id: int) -> list:
    conn = _conn()
    try:
        rows = conn.execute(f"""
            SELECT {_DETAIL_COLS} FROM papers
            WHERE treatment_id = ? AND status != 'deleted'
            ORDER BY evidence_level DESC, pub_year DESC
        """, (treatment_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ── 일괄 등록 ──

def bulk_create(papers_data: list) -> int:
    conn = _conn()
    try:
        now = now_str()
        created = 0
        for data in papers_data:
            conn.execute(_INSERT_SQL, _paper_values(data, now))
            created += 1
        conn.commit()
        return created
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── 중복 체크 ──

def check_duplicate(paper: dict) -> dict | None:
    conn = _conn()
    try:
        doi = paper.get("doi", "").strip()
        if doi:
            row = conn.execute(
                "SELECT id, title_ko, title FROM papers WHERE doi = ? AND status != 'deleted'",
                (doi,)
            ).fetchone()
            if row:
                return {"title": row["title_ko"] or row["title"], "reason": f"DOI 중복: {doi}"}

        title = paper.get("title", "").strip()
        if title:
            row = conn.execute(
                "SELECT id, title_ko, title FROM papers WHERE title = ? AND status != 'deleted'",
                (title,)
            ).fetchone()
            if row:
                return {"title": row["title_ko"] or row["title"], "reason": "제목 동일"}

        return None
    finally:
        conn.close()
