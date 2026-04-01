"""논문/연구자료 API 라우터.

SQL 로직은 papers/queries.py에 위임. 라우터는 요청/응답만 담당.
"""

import json
import sys
import subprocess
import os
import time as _time
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from datetime import datetime

from api.models import PaperCreate, PaperUpdate
from papers.queries import (
    get_devices_summary, get_study_types, list_papers, get_paper,
    create_paper, update_paper, delete_paper,
    papers_by_device, papers_by_treatment,
    bulk_create, check_duplicate,
)

router = APIRouter(prefix="/papers", tags=["papers"])

# PaperCreate에 없는 키 목록 (paper_analyzer.py 출력에 포함되는 메타 키)
_EXTRA_KEYS = {
    "device_name", "treatment_name", "_evidence_reason", "_related_devices",
    "_skipped", "_skip_reason", "_file", "file_hash",
}
_PAPER_FIELDS = set(PaperCreate.model_fields.keys())


# ── 필터 드롭다운용 ──
@router.get("/devices-summary")
def papers_devices_summary_api():
    return get_devices_summary()


@router.get("/study-types")
def papers_study_types_api():
    return get_study_types()


# ── 목록 조회 ──
@router.get("")
def list_papers_api(
    device_info_id: Optional[int] = None,
    treatment_id: Optional[int] = None,
    status: Optional[str] = None,
    evidence_level: Optional[int] = None,
    evidence_min: Optional[int] = None,
    study_type: Optional[str] = None,
    q: Optional[str] = None,
):
    return list_papers(
        device_info_id=device_info_id, treatment_id=treatment_id,
        status=status, evidence_level=evidence_level, evidence_min=evidence_min,
        study_type=study_type, q=q,
    )


# ── 단건 조회 ──
@router.get("/{paper_id}")
def get_paper_api(paper_id: int):
    result = get_paper(paper_id)
    if not result:
        raise HTTPException(404, "논문을 찾을 수 없습니다")
    return result


# ── 생성 ──
@router.post("")
def create_paper_api(data: PaperCreate):
    paper_id = create_paper(data)
    return {"id": paper_id, "message": "논문이 등록되었습니다"}


# ── 수정 ──
@router.patch("/{paper_id}")
def update_paper_api(paper_id: int, data: PaperUpdate):
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        return {"message": "변경 사항 없음"}
    if not update_paper(paper_id, updates):
        raise HTTPException(404, "논문을 찾을 수 없습니다")
    return {"message": "논문이 수정되었습니다"}


# ── 삭제 ──
@router.delete("/{paper_id}")
def delete_paper_api(paper_id: int):
    if not delete_paper(paper_id):
        raise HTTPException(404, "논문을 찾을 수 없습니다")
    return {"message": "논문이 삭제되었습니다"}


# ── 장비별 논문 조회 ──
@router.get("/by-device/{device_info_id}")
def papers_by_device_api(device_info_id: int):
    return papers_by_device(device_info_id)


# ── 시술별 논문 조회 ──
@router.get("/by-treatment/{treatment_id}")
def papers_by_treatment_api(treatment_id: int):
    return papers_by_treatment(treatment_id)


# ── 일괄 등록 ──
@router.post("/bulk")
def bulk_create_papers_api(papers: list[PaperCreate]):
    created = bulk_create(papers)
    return {"created": created, "message": f"{created}건 논문이 등록되었습니다"}


# ── 폴더 분석 실행 ──
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

    pdf_files = list(folder.glob("*.pdf"))
    if not pdf_files:
        raise HTTPException(400, f"폴더에 PDF 파일이 없습니다: {req.folder_path}")

    project_root = Path(__file__).resolve().parent.parent.parent
    analyzer_path = project_root / "papers" / "analyzer.py"
    if not analyzer_path.exists():
        raise HTTPException(500, "papers/analyzer.py를 찾을 수 없습니다")

    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = req.api_key

    cmd = [sys.executable, str(analyzer_path), "--dir", str(folder), "--no-docx", "--no-xlsx"]
    if req.dry_run:
        cmd.append("--dry-run")

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600, cwd=str(project_root))
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "분석 시간 초과 (10분). 파일 수를 줄여서 다시 시도해주세요.")

    stdout = result.stdout
    stderr = result.stderr

    results_dir = project_root / "paper_results"
    json_files = sorted(results_dir.glob("papers_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    latest_json = None
    paper_count = 0

    if json_files:
        latest = json_files[0]
        if _time.time() - latest.stat().st_mtime < 30:
            latest_json = str(latest)
            with open(latest, "r", encoding="utf-8") as f:
                papers_data = json.load(f)
                paper_count = len([p for p in papers_data if not p.get("_skipped")])

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


# ── 폴더 스캔 ──
@router.post("/scan-folder")
def scan_folder(data: dict):
    folder = Path(data.get("folder_path", ""))
    if not folder.exists():
        raise HTTPException(400, f"폴더가 존재하지 않습니다: {folder}")
    if not folder.is_dir():
        raise HTTPException(400, f"디렉토리가 아닙니다: {folder}")

    pdf_files = sorted(folder.glob("*.pdf"))
    return {
        "folder": str(folder),
        "pdf_count": len(pdf_files),
        "files": [f.name for f in pdf_files[:50]],
        "has_more": len(pdf_files) > 50,
    }


@router.post("/list-dirs")
def list_dirs(data: dict):
    folder = Path(data.get("folder_path", ""))
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(400, f"폴더가 존재하지 않습니다: {folder}")

    dirs = []
    try:
        for item in sorted(folder.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                pdf_count = len(list(item.glob("*.pdf")))
                dirs.append({"name": item.name, "path": str(item), "pdf_count": pdf_count})
    except PermissionError:
        raise HTTPException(403, "폴더 접근 권한이 없습니다.")

    return {
        "parent": str(folder),
        "dirs": dirs,
        "pdf_count": len(list(folder.glob("*.pdf"))),
    }


# ── JSON 파일 업로드 ──
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

    if isinstance(raw_data, dict):
        raw_data = [raw_data]
    if not isinstance(raw_data, list):
        raise HTTPException(400, "JSON은 배열 또는 단일 객체여야 합니다")

    inserted = 0
    duplicates = []
    errors = []

    for idx, item in enumerate(raw_data):
        if item.get("_skipped"):
            continue

        cleaned = {k: v for k, v in item.items() if k in _PAPER_FIELDS}
        if not cleaned.get("title"):
            errors.append({"index": idx, "error": "제목(title) 누락"})
            continue

        dup = check_duplicate(cleaned)
        if dup:
            duplicates.append(dup)
            continue

        try:
            data = PaperCreate(**cleaned)
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})
            continue

        try:
            create_paper(data)
            inserted += 1
        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    return {
        "inserted": inserted,
        "duplicates": duplicates,
        "errors": errors,
        "message": f"{inserted}건 등록, {len(duplicates)}건 중복 건너뜀"
            + (f", {len(errors)}건 오류" if errors else ""),
    }
