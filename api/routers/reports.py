"""주간 보고서 라우터 — Phase 2."""

from datetime import date, datetime, timedelta
from typing import Optional
from pathlib import Path
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import sqlite3
import json

from api.deps import get_current_user, require_role

# ── 이미지 업로드 설정 ──────────────────────────────────────────────────────────
UPLOAD_BASE = Path(__file__).resolve().parent.parent.parent / "data" / "uploads" / "reports"
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB
_VALID_SECTIONS = {"blogDistribution", "place", "website", "blogExposure", "related"}

router = APIRouter(prefix="/reports", tags=["Reports"])


def _validate_monday(week_start: str) -> date:
    """week_start가 월요일인지 검증하고 date 객체로 반환."""
    try:
        d = datetime.strptime(week_start, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "week_start 형식은 YYYY-MM-DD 이어야 합니다.")
    if d.weekday() != 0:  # 0 == Monday
        raise HTTPException(
            400,
            f"week_start는 월요일이어야 합니다 ({week_start}는 "
            f"{['월','화','수','목','금','토','일'][d.weekday()]}요일).",
        )
    return d


class CreateReportBody(BaseModel):
    week_start: str            # "YYYY-MM-DD" (월요일)
    title: Optional[str] = ""
    data: dict = {}            # MVP defaultState 구조 JSON


class UpdateReportBody(BaseModel):
    title: Optional[str] = None
    data: Optional[dict] = None


@router.get("/weekly")
async def list_weekly(
    user: dict = Depends(get_current_user),
    limit: Optional[int] = None,
):
    """주차 목록 (최신순). data는 제외."""
    from reports.db import list_reports
    return list_reports(limit=limit)


@router.get("/weekly/{week_start}")
async def get_weekly(
    week_start: str,
    user: dict = Depends(get_current_user),
):
    """특정 주차 보고서 조회."""
    _validate_monday(week_start)
    from reports.db import get_report
    report = get_report(week_start)
    if not report:
        raise HTTPException(404, f"{week_start} 주차 보고서가 없습니다.")
    return report


@router.post("/weekly")
async def create_weekly(
    body: CreateReportBody,
    user: dict = Depends(require_role("editor")),
):
    """신규 주간 보고서 생성 (editor+)."""
    monday = _validate_monday(body.week_start)
    sunday = monday + timedelta(days=6)
    from reports.db import create_report, update_report
    try:
        created = create_report(
            week_start=monday.isoformat(),
            week_end=sunday.isoformat(),
            title=body.title or "",
            data=body.data or {},
            created_by=None,  # JWT payload에 user id 없음 (username만 존재)
        )
    except sqlite3.IntegrityError:
        raise HTTPException(409, f"{monday.isoformat()} 주차 보고서가 이미 존재합니다.")

    # 생성 직후 자동 집계 (실패해도 보고서 생성은 유지)
    try:
        from reports.autofill import compute_autofill
        auto = compute_autofill(monday.isoformat(), sunday.isoformat())
        merged_data = _apply_autofill((created.get("data") or {}).copy(), auto)
        created = update_report(monday.isoformat(), None, merged_data)
    except Exception:
        pass
    return created


@router.put("/weekly/{week_start}")
async def update_weekly(
    week_start: str,
    body: UpdateReportBody,
    user: dict = Depends(require_role("editor")),
):
    """보고서 수정 (editor+)."""
    _validate_monday(week_start)
    from reports.db import update_report
    report = update_report(week_start, body.title, body.data)
    if not report:
        raise HTTPException(404, f"{week_start} 주차 보고서가 없습니다.")
    return report


@router.delete("/weekly/{week_start}")
async def delete_weekly(
    week_start: str,
    user: dict = Depends(require_role("admin")),
):
    """보고서 삭제 (admin 전용)."""
    _validate_monday(week_start)
    from reports.db import delete_report
    if not delete_report(week_start):
        raise HTTPException(404, f"{week_start} 주차 보고서가 없습니다.")
    return {"deleted": week_start}


# ── autofill 헬퍼 ─────────────────────────────────────────────────────────────

def _apply_autofill(data: dict, auto: dict) -> dict:
    """auto 값을 data_json에 병합. _override 필드는 건드리지 않음."""
    for section_key, section_auto in auto.items():
        section = data.setdefault(section_key, {})
        for field_key, auto_val in section_auto.items():
            section[field_key] = auto_val  # _auto 또는 auto_updated_at 저장
            if field_key.endswith("_auto"):
                base = field_key[:-5]  # "total_auto" → "total"
                override = section.get(f"{base}_override")
                # override가 None 또는 빈 문자열이면 auto 사용
                section[base] = override if (override is not None and override != "") else auto_val
    return data


@router.post("/weekly/{week_start}/autofill")
async def autofill_weekly(
    week_start: str,
    user: dict = Depends(require_role("editor")),
):
    """해당 주차 자동 집계값 계산 및 저장. _override 필드는 유지."""
    d = _validate_monday(week_start)
    week_end = (d + timedelta(days=6)).isoformat()

    from reports.db import get_report, update_report
    from reports.autofill import compute_autofill

    report = get_report(week_start)
    if not report:
        raise HTTPException(404, f"{week_start} 주차 보고서가 없습니다.")

    auto = compute_autofill(week_start, week_end)
    data = _apply_autofill(report["data"], auto)
    updated = update_report(week_start, None, data)
    return updated


# ── 이미지 업로드/삭제 ─────────────────────────────────────────────────────────

@router.post("/weekly/{week_start}/images")
async def upload_image(
    week_start: str,
    section: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role("editor")),
):
    """섹션별 이미지 업로드. 반환: {path, url, filename}"""
    _validate_monday(week_start)
    if section not in _VALID_SECTIONS:
        raise HTTPException(400, f"알 수 없는 섹션: {section}")

    # 확장자 검증
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"지원하지 않는 형식: {ext}")

    # 크기 검증
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"파일 크기 초과: {len(content)} > {MAX_SIZE}")

    # 저장
    target_dir = UPLOAD_BASE / week_start / section
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    target_path = target_dir / filename
    target_path.write_bytes(content)

    rel_path = f"reports/{week_start}/{section}/{filename}"
    return {
        "path": rel_path,
        "url": f"/uploads/{rel_path}",
        "filename": filename,
    }


@router.delete("/weekly/{week_start}/images")
async def delete_image(
    week_start: str,
    path: str,
    user: dict = Depends(require_role("editor")),
):
    """이미지 파일 삭제. path는 `reports/{week_start}/{section}/{filename}` 형식."""
    _validate_monday(week_start)
    # 경로 조작 방지
    if ".." in path or not path.startswith(f"reports/{week_start}/"):
        raise HTTPException(400, "잘못된 경로")
    target = UPLOAD_BASE.parent / path  # UPLOAD_BASE.parent = uploads/
    if not target.exists():
        raise HTTPException(404, "파일 없음")
    target.unlink()
    return {"deleted": path}


# ── 대시보드 헬퍼 ──────────────────────────────────────────────────────────────

def _safe_int(val) -> Optional[int]:
    """문자열/숫자를 int로 변환. 실패 시 None."""
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _extract_kpi_fields(data: dict) -> dict:
    """data_json 파싱 결과에서 대시보드 KPI 필드 5개 추출."""
    return {
        "blogDistribution": data.get("blogDistribution", {}),
        "place": data.get("place", {}),
        "website": data.get("website", {}),
        "blogExposure": data.get("blogExposure", {}),
        "related": data.get("related", {}),
    }


def _extract_trend_point(week_start: str, data: dict) -> dict:
    """data_json에서 추이 차트용 숫자 5개 추출."""
    bd = data.get("blogDistribution", {})
    pl = data.get("place", {})
    ws = data.get("website", {})
    be = data.get("blogExposure", {})
    re = data.get("related", {})
    return {
        "week_start": week_start,
        "blog_ranked": _safe_int(bd.get("ranked")),
        "place_occupied": _safe_int(pl.get("occupied")),
        "website_visible": _safe_int(ws.get("visible")),
        "blog_exposure_visible": _safe_int(be.get("visible")),
        "related_created": _safe_int(re.get("created")),
    }


def _get_realtime_place(conn, target_date: str) -> dict:
    """place_daily에서 특정 날짜 집계. 없으면 직전일 fallback."""
    def _query(d: str):
        rows = conn.execute(
            "SELECT is_exposed FROM place_daily WHERE date = ?",
            (d,)
        ).fetchall()
        return rows

    rows = _query(target_date)
    used_date = target_date

    if not rows:
        # 직전 날짜 fallback
        prev = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = _query(prev)
        used_date = prev if rows else target_date

    total = len(rows)
    success = sum(1 for r in rows if r["is_exposed"] == 1)
    fail = sum(1 for r in rows if r["is_exposed"] == 0)
    midal = total - success - fail

    return {
        "success": success,
        "fail": fail,
        "midal": midal,
        "total": total,
        "date": used_date,
    }


def _get_realtime_webpage(conn, target_date: str) -> dict:
    """webpage_daily에서 특정 날짜 집계. 없으면 직전일 fallback."""
    def _query(d: str):
        rows = conn.execute(
            "SELECT is_exposed FROM webpage_daily WHERE date = ?",
            (d,)
        ).fetchall()
        return rows

    rows = _query(target_date)
    used_date = target_date

    if not rows:
        prev = (datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = _query(prev)
        used_date = prev if rows else target_date

    total = len(rows)
    visible = sum(1 for r in rows if r["is_exposed"] == 1)
    fail = sum(1 for r in rows if r["is_exposed"] == 0)
    midal = total - visible - fail

    return {
        "visible": visible,
        "fail": fail,
        "midal": midal,
        "total": total,
        "date": used_date,
    }


@router.get("/public/{week_start}")
async def get_public_report(week_start: str):
    """주차 월요일 날짜 기반 공개 조회. 인증 없음. 영구 유효."""
    _validate_monday(week_start)
    from reports.db import get_report
    report = get_report(week_start)
    if not report:
        raise HTTPException(404, "보고서를 찾을 수 없습니다.")
    return report


@router.get("/dashboard")
async def get_dashboard(
    user: dict = Depends(get_current_user),
    weeks: int = 8,
):
    """대시보드 집계 데이터 반환."""
    from shared.db import get_conn, EQUIPMENT_DB

    conn = get_conn(EQUIPMENT_DB)
    try:
        # ── 1) weekly_kpis: 최근 2건 ──
        rows = conn.execute(
            """SELECT week_start, data_json
               FROM weekly_reports
               ORDER BY week_start DESC
               LIMIT 2""",
        ).fetchall()

        kpi_rows = []
        for r in rows:
            try:
                data = json.loads(r["data_json"] or "{}")
            except json.JSONDecodeError:
                data = {}
            entry = {"week_start": r["week_start"]}
            entry.update(_extract_kpi_fields(data))
            kpi_rows.append(entry)

        current = kpi_rows[0] if len(kpi_rows) >= 1 else None
        previous = kpi_rows[1] if len(kpi_rows) >= 2 else None

        weekly_kpis = {
            "current": current,
            "previous": previous,
            "has_current": current is not None,
            "has_previous": previous is not None,
        }

        # ── 2) weekly_trend: 최근 N주 오름차순 ──
        trend_rows = conn.execute(
            """SELECT week_start, data_json
               FROM weekly_reports
               ORDER BY week_start DESC
               LIMIT ?""",
            (weeks,),
        ).fetchall()

        weekly_trend = []
        for r in reversed(trend_rows):  # 오름차순 변환 (차트 X축용)
            try:
                data = json.loads(r["data_json"] or "{}")
            except json.JSONDecodeError:
                data = {}
            weekly_trend.append(_extract_trend_point(r["week_start"], data))

        # ── 3) realtime: 전일 기준 place/webpage 집계 ──
        # 화요일에 전주 월요일 데이터를 보는 운영 특성상 기준일은 '어제'.
        # 해당 일자 데이터가 없으면 헬퍼가 하루 더 이전으로 fallback.
        ref_str = (date.today() - timedelta(days=1)).isoformat()
        realtime = {
            "place": _get_realtime_place(conn, ref_str),
            "webpage": _get_realtime_webpage(conn, ref_str),
        }

        return {
            "weekly_kpis": weekly_kpis,
            "weekly_trend": weekly_trend,
            "realtime": realtime,
        }

    finally:
        conn.close()
