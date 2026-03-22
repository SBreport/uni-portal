"""논문/연구자료 API 라우터."""

import sqlite3
from typing import Optional
from fastapi import APIRouter, HTTPException
from datetime import datetime

from api.models import PaperCreate, PaperUpdate

router = APIRouter(prefix="/papers", tags=["papers"])

DB_PATH = "data/equipment.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 목록 조회 ──
@router.get("")
def list_papers(
    device_info_id: Optional[int] = None,
    treatment_id: Optional[int] = None,
    status: Optional[str] = None,
    q: Optional[str] = None,
):
    conn = _conn()
    sql = """
        SELECT p.*,
               d.name AS device_name,
               t.name AS treatment_name,
               t.brand AS treatment_brand
        FROM papers p
        LEFT JOIN device_info d ON d.id = p.device_info_id
        LEFT JOIN evt_treatments t ON t.id = p.treatment_id
        WHERE 1=1
    """
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
    if q:
        sql += " AND (p.title LIKE ? OR p.title_ko LIKE ? OR p.authors LIKE ? OR p.key_findings LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like, like])

    sql += " ORDER BY p.pub_year DESC, p.created_at DESC"

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── 단건 조회 ──
@router.get("/{paper_id}")
def get_paper(paper_id: int):
    conn = _conn()
    row = conn.execute("""
        SELECT p.*,
               d.name AS device_name,
               t.name AS treatment_name,
               t.brand AS treatment_brand
        FROM papers p
        LEFT JOIN device_info d ON d.id = p.device_info_id
        LEFT JOIN evt_treatments t ON t.id = p.treatment_id
        WHERE p.id = ?
    """, (paper_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "논문을 찾을 수 없습니다")
    return dict(row)


# ── 생성 ──
@router.post("")
def create_paper(data: PaperCreate):
    conn = _conn()
    now = datetime.now().isoformat()
    cur = conn.execute("""
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
    """, (
        data.device_info_id, data.treatment_id, data.doi, data.title, data.title_ko,
        data.authors, data.journal, data.pub_year, data.pub_date,
        data.abstract_summary, data.key_findings, data.keywords,
        data.evidence_level, data.study_type, data.sample_size,
        data.source_url, data.source_file, data.status,
        data.one_line_summary, data.research_purpose, data.study_design_detail,
        data.key_results, data.conclusion, data.quotable_stats, data.cautions, data.follow_up_period,
        now, now,
    ))
    conn.commit()
    paper_id = cur.lastrowid
    conn.close()
    return {"id": paper_id, "message": "논문이 등록되었습니다"}


# ── 수정 ──
@router.patch("/{paper_id}")
def update_paper(paper_id: int, data: PaperUpdate):
    conn = _conn()
    existing = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404, "논문을 찾을 수 없습니다")

    updates = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        updates[field] = value

    if not updates:
        conn.close()
        return {"message": "변경 사항 없음"}

    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [paper_id]

    conn.execute(f"UPDATE papers SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return {"message": "논문이 수정되었습니다"}


# ── 삭제 ──
@router.delete("/{paper_id}")
def delete_paper(paper_id: int):
    conn = _conn()
    existing = conn.execute("SELECT id FROM papers WHERE id = ?", (paper_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404, "논문을 찾을 수 없습니다")
    conn.execute("DELETE FROM papers WHERE id = ?", (paper_id,))
    conn.commit()
    conn.close()
    return {"message": "논문이 삭제되었습니다"}


# ── 장비별 논문 조회 (EquipmentView 연동용) ──
@router.get("/by-device/{device_info_id}")
def papers_by_device(device_info_id: int):
    conn = _conn()
    rows = conn.execute("""
        SELECT id, title, title_ko, authors, journal, pub_year,
               abstract_summary, key_findings, evidence_level, study_type, source_url,
               one_line_summary, research_purpose, study_design_detail,
               key_results, conclusion, quotable_stats, cautions, follow_up_period
        FROM papers
        WHERE device_info_id = ? AND status != 'deleted'
        ORDER BY evidence_level DESC, pub_year DESC
    """, (device_info_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── 시술별 논문 조회 ──
@router.get("/by-treatment/{treatment_id}")
def papers_by_treatment(treatment_id: int):
    conn = _conn()
    rows = conn.execute("""
        SELECT id, title, title_ko, authors, journal, pub_year,
               abstract_summary, key_findings, evidence_level, study_type, source_url,
               one_line_summary, research_purpose, study_design_detail,
               key_results, conclusion, quotable_stats, cautions, follow_up_period
        FROM papers
        WHERE treatment_id = ? AND status != 'deleted'
        ORDER BY evidence_level DESC, pub_year DESC
    """, (treatment_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── 일괄 등록 (외부 분석 프로그램 연동용) ──
@router.post("/bulk")
def bulk_create_papers(papers: list[PaperCreate]):
    conn = _conn()
    now = datetime.now().isoformat()
    created = 0
    for data in papers:
        conn.execute("""
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
        """, (
            data.device_info_id, data.treatment_id, data.doi, data.title, data.title_ko,
            data.authors, data.journal, data.pub_year, data.pub_date,
            data.abstract_summary, data.key_findings, data.keywords,
            data.evidence_level, data.study_type, data.sample_size,
            data.source_url, data.source_file, data.status,
            data.one_line_summary, data.research_purpose, data.study_design_detail,
            data.key_results, data.conclusion, data.quotable_stats, data.cautions, data.follow_up_period,
            now, now,
        ))
        created += 1
    conn.commit()
    conn.close()
    return {"created": created, "message": f"{created}건 논문이 등록되었습니다"}
