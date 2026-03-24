"""논문/연구자료 API 라우터."""

import json
import sys
import sqlite3
import subprocess
import os
import time as _time
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime

from api.models import PaperCreate, PaperUpdate

router = APIRouter(prefix="/papers", tags=["papers"])

DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── 논문에 연결된 장비 목록 (필터 드롭다운용) ──
@router.get("/devices-summary")
def papers_devices_summary():
    """논문이 1건 이상 연결된 장비 목록과 논문 수를 반환."""
    conn = _conn()
    rows = conn.execute("""
        SELECT d.id, d.name, COUNT(p.id) AS paper_count
        FROM device_info d
        INNER JOIN papers p ON p.device_info_id = d.id
        GROUP BY d.id, d.name
        ORDER BY paper_count DESC, d.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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


def _classify_study_type(raw: str) -> str:
    if not raw:
        return "기타"
    for category, keywords in STUDY_TYPE_MAP.items():
        for kw in keywords:
            if kw.lower() in raw.lower():
                return category
    return "기타"


# ── 연구유형 목록 (필터 드롭다운용) ──
@router.get("/study-types")
def papers_study_types():
    """DB의 연구유형을 대분류로 그루핑하여 반환."""
    conn = _conn()
    rows = conn.execute("""
        SELECT study_type FROM papers
        WHERE study_type IS NOT NULL AND study_type != ''
    """).fetchall()
    conn.close()

    counts: dict[str, int] = {}
    for r in rows:
        cat = _classify_study_type(r[0])
        counts[cat] = counts.get(cat, 0) + 1

    result = [{"study_type": k, "cnt": v} for k, v in counts.items()]
    result.sort(key=lambda x: -x["cnt"])
    return result


# ── 목록 조회 ──
@router.get("")
def list_papers(
    device_info_id: Optional[int] = None,
    treatment_id: Optional[int] = None,
    status: Optional[str] = None,
    evidence_level: Optional[int] = None,
    evidence_min: Optional[int] = None,
    study_type: Optional[str] = None,
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
    if evidence_level is not None:
        sql += " AND p.evidence_level = ?"
        params.append(evidence_level)
    if evidence_min is not None:
        sql += " AND p.evidence_level >= ?"
        params.append(evidence_min)
    if study_type:
        # 대분류 카테고리로 필터링
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
        params.extend([like, like, like, like, like, like, like, like])

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


# ── 폴더 분석 실행 (로컬 paper_analyzer.py 호출) ──
class AnalyzeDirRequest(BaseModel):
    folder_path: str
    api_key: str
    dry_run: bool = False


@router.post("/analyze-dir")
def analyze_directory(req: AnalyzeDirRequest):
    """로컬 폴더의 PDF를 paper_analyzer.py로 일괄 분석."""
    folder = Path(req.folder_path)
    if not folder.exists():
        raise HTTPException(400, f"폴더가 존재하지 않습니다: {req.folder_path}")
    if not folder.is_dir():
        raise HTTPException(400, f"디렉토리가 아닙니다: {req.folder_path}")

    # PDF 파일 개수 확인
    pdf_files = list(folder.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(400, f"폴더에 PDF 파일이 없습니다: {req.folder_path}")

    # paper_analyzer.py 경로
    project_root = Path(__file__).resolve().parent.parent.parent
    analyzer_path = project_root / "papers" / "analyzer.py"
    if not analyzer_path.exists():
        raise HTTPException(500, "papers/analyzer.py를 찾을 수 없습니다")

    # 환경변수에 API 키 설정
    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = req.api_key

    # 명령어 구성
    cmd = [sys.executable, str(analyzer_path), "--dir", str(folder), "--no-docx", "--no-xlsx"]
    if req.dry_run:
        cmd.append("--dry-run")

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,  # 10분 타임아웃
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "분석 시간 초과 (10분). 파일 수를 줄여서 다시 시도해주세요.")

    # 결과 파싱
    stdout = result.stdout
    stderr = result.stderr

    # 분석 결과 JSON 파일 찾기 (가장 최근 생성된 것)
    results_dir = project_root / "paper_results"
    json_files = sorted(results_dir.glob("papers_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    latest_json = None
    paper_count = 0

    if json_files:
        latest = json_files[0]
        # 방금 생성된 파일인지 확인 (30초 이내)
        if _time.time() - latest.stat().st_mtime < 30:
            latest_json = str(latest)
            with open(latest, "r", encoding="utf-8") as f:
                papers = json.load(f)
                paper_count = len([p for p in papers if not p.get("_skipped")])

    # stdout에서 결과 요약 추출
    lines = stdout.strip().split("\n") if stdout else []
    summary_lines = [l for l in lines if any(k in l for k in ["성공:", "중복", "실패:", "분석 완료"])]

    return {
        "success": result.returncode == 0,
        "pdf_count": len(pdf_files),
        "analyzed": paper_count,
        "json_file": latest_json,
        "summary": summary_lines[-5:] if summary_lines else [],
        "stdout_tail": "\n".join(lines[-20:]) if lines else "",
        "stderr": stderr[:500] if stderr else "",
    }


# ── 폴더 스캔 (PDF 파일 목록 확인) ──
@router.post("/scan-folder")
def scan_folder(data: dict):
    """폴더 경로를 입력받아 PDF 파일 목록과 개수를 반환."""
    folder = Path(data.get("folder_path", ""))
    if not folder.exists():
        raise HTTPException(400, f"폴더가 존재하지 않습니다: {folder}")
    if not folder.is_dir():
        raise HTTPException(400, f"디렉토리가 아닙니다: {folder}")

    pdf_files = sorted(folder.glob("*.pdf"))
    return {
        "folder": str(folder),
        "pdf_count": len(pdf_files),
        "files": [f.name for f in pdf_files[:50]],  # 최대 50개만 반환
        "has_more": len(pdf_files) > 50,
    }


@router.post("/list-dirs")
def list_dirs(data: dict):
    """폴더 경로의 하위 디렉토리 목록 반환. 폴더 탐색기용."""
    folder = Path(data.get("folder_path", ""))
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(400, f"폴더가 존재하지 않습니다: {folder}")

    dirs = []
    try:
        for item in sorted(folder.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                pdf_count = len(list(item.glob("*.pdf")))
                dirs.append({
                    "name": item.name,
                    "path": str(item),
                    "pdf_count": pdf_count,
                })
    except PermissionError:
        raise HTTPException(403, "폴더 접근 권한이 없습니다.")

    return {
        "parent": str(folder),
        "dirs": dirs,
        "pdf_count": len(list(folder.glob("*.pdf"))),
    }


# ── JSON 파일 업로드 (로컬 분석 결과 일괄 등록) ──
# PaperCreate에 없는 키 목록 (paper_analyzer.py 출력에 포함되는 메타 키)
_EXTRA_KEYS = {
    "device_name", "treatment_name", "_evidence_reason", "_related_devices",
    "_skipped", "_skip_reason", "_file", "file_hash",
}
# PaperCreate 필드 목록
_PAPER_FIELDS = set(PaperCreate.model_fields.keys())


def _check_duplicate(conn, paper: dict) -> dict | None:
    """DOI 또는 제목으로 중복 체크."""
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


@router.post("/upload-json")
async def upload_json(file: UploadFile = File(...)):
    """로컬 paper_analyzer.py 분석 결과 JSON을 업로드하여 일괄 등록."""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(400, "JSON 파일만 업로드 가능합니다")

    content = await file.read()
    try:
        raw_data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"JSON 파싱 오류: {e}")

    # 리스트가 아니면 리스트로 감싸기
    if isinstance(raw_data, dict):
        raw_data = [raw_data]
    if not isinstance(raw_data, list):
        raise HTTPException(400, "JSON은 배열 또는 단일 객체여야 합니다")

    conn = _conn()
    now = datetime.now().isoformat()
    inserted = 0
    duplicates = []
    errors = []

    for idx, item in enumerate(raw_data):
        # _skipped 항목 건너뛰기 (paper_analyzer가 스킵한 항목)
        if item.get("_skipped"):
            continue

        # PaperCreate에 없는 키 제거
        cleaned = {k: v for k, v in item.items() if k in _PAPER_FIELDS}

        # 필수 필드 확인
        if not cleaned.get("title"):
            errors.append({"index": idx, "error": "제목(title) 누락"})
            continue

        # 중복 체크
        dup = _check_duplicate(conn, cleaned)
        if dup:
            duplicates.append(dup)
            continue

        # PaperCreate 검증
        try:
            data = PaperCreate(**cleaned)
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})
            continue

        # INSERT
        try:
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
            inserted += 1
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    conn.commit()
    conn.close()

    return {
        "inserted": inserted,
        "duplicates": duplicates,
        "errors": errors,
        "message": f"{inserted}건 등록, {len(duplicates)}건 중복 건너뜀"
            + (f", {len(errors)}건 오류" if errors else ""),
    }
