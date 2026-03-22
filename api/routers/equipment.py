"""Equipment 라우터 — 보유장비 + 장비사전 (10개 엔드포인트)."""

from typing import Annotated, Optional
import math
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse


def _clean_df(df):
    if df is None:
        return []
    return [{k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
             for k, v in row.items()} for row in df.to_dict(orient="records")]

from api.deps import get_current_user, require_role
from api.models import EquipmentUpdate, PhotoChangeItem, DeviceInfoUpsert

from equipment.db import (
    load_data, get_branches, get_categories,
    update_equipment, save_photo_changes,
    get_all_device_info, search_device_info, find_matching_devices,
    upsert_device_info, delete_device_info,
)

router = APIRouter()
_branch = require_role("branch")
_editor = require_role("editor")


# ── 장비 목록 ──
@router.get("")
async def get_equipment(
    user: Annotated[dict, Depends(get_current_user)],
    branch: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    df = load_data()
    if df.empty:
        return []

    # 컬럼명 정규화 (DB 쿼리가 '지점명', '순번'을 반환하므로)
    rename_map = {}
    if "지점명" in df.columns and "지점" not in df.columns:
        rename_map["지점명"] = "지점"
    if "순번" in df.columns and "id" not in df.columns:
        rename_map["순번"] = "id"
    if rename_map:
        df = df.rename(columns=rename_map)

    # 사진 값 정규화 ('O' → '있음')
    if "사진" in df.columns:
        df["사진"] = df["사진"].apply(lambda x: "있음" if str(x).strip() in ("O", "o", "있음") else "")

    # 필터 적용
    if branch:
        df = df[df["지점"] == branch]
    if category:
        df = df[df["카테고리"] == category]
    if search:
        mask = df.apply(lambda r: search.lower() in str(r).lower(), axis=1)
        df = df[mask]
    return _clean_df(df)


@router.get("/branches")
async def get_branch_list(user: Annotated[dict, Depends(get_current_user)]):
    return get_branches()


@router.get("/categories")
async def get_category_list(user: Annotated[dict, Depends(get_current_user)]):
    return get_categories()


@router.patch("/{eq_id}")
async def patch_equipment(
    eq_id: int,
    req: EquipmentUpdate,
    user: Annotated[dict, Depends(_branch)],
):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if updates:
        update_equipment(eq_id, **updates)
    return {"ok": True}


@router.post("/photo-changes")
async def post_photo_changes(
    changes: list[PhotoChangeItem],
    user: Annotated[dict, Depends(_branch)],
):
    change_list = [(c.equipment_id, c.photo_status) for c in changes]
    ok, errors = save_photo_changes(change_list)
    return {"ok": ok, "errors": errors}


# ── 장비 사전 ──
@router.get("/device-info")
async def get_device_info_list(user: Annotated[dict, Depends(get_current_user)]):
    return get_all_device_info()


@router.get("/device-info/search")
async def search_devices(
    q: str = Query(...),
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    return search_device_info(q)


@router.get("/device-info/match")
async def match_devices(
    name: str = Query(...),
    user: Annotated[dict, Depends(get_current_user)] = None,
):
    return find_matching_devices(name)


@router.post("/device-info")
async def create_device_info(
    req: DeviceInfoUpsert,
    user: Annotated[dict, Depends(_editor)],
):
    upsert_device_info(
        name=req.name, category=req.category, summary=req.summary,
        target=req.target, mechanism=req.mechanism, note=req.note,
        aliases=req.aliases, is_verified=req.is_verified,
    )
    return {"ok": True}


@router.delete("/device-info/{name}")
async def remove_device_info(
    name: str,
    user: Annotated[dict, Depends(_editor)],
):
    delete_device_info(name)
    return {"ok": True}


# ── 동기화 (admin) ──
@router.post("/sync")
async def post_sync(
    user: Annotated[dict, Depends(require_role("admin"))],
):
    from equipment.sync import sync_from_sheets
    result = sync_from_sheets()
    return result


@router.post("/device-info/update-counts")
async def post_update_counts(
    user: Annotated[dict, Depends(_editor)],
):
    from equipment.db import update_device_usage_counts
    update_device_usage_counts()
    return {"ok": True}


@router.post("/device-info/sync-json")
async def post_sync_json(
    user: Annotated[dict, Depends(_editor)],
):
    from equipment.db import seed_device_info_from_json
    seed_device_info_from_json()
    return {"ok": True}


# ── DB 파일 관리 (admin 전용) ──

@router.get("/db-download")
async def download_db(user: Annotated[dict, Depends(require_role("admin"))]):
    """현재 서버 DB 파일 다운로드 (백업용)."""
    import os
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "equipment.db")
    db_path = os.path.abspath(db_path)
    if not os.path.exists(db_path):
        raise HTTPException(404, "DB 파일 없음")
    return FileResponse(db_path, filename="equipment.db", media_type="application/octet-stream")


@router.post("/db-upload")
async def upload_db(
    file: UploadFile = File(...),
    user: Annotated[dict, Depends(require_role("admin"))] = None,
):
    """로컬 DB에서 장비/논문 데이터만 서버 DB에 병합.

    카페 원고, 이벤트, 사용자 등 기존 데이터는 건드리지 않음.
    병합 대상: device_info, papers, evt_treatments, evt_categories
    """
    import os, shutil, sqlite3, tempfile
    from datetime import datetime

    db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    db_dir = os.path.abspath(db_dir)
    server_db = os.path.join(db_dir, "equipment.db")

    # 1. 업로드 파일을 임시 파일로 저장
    content = await file.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.write(content)
    tmp.close()

    try:
        # 2. 서버 DB 자동 백업
        if os.path.exists(server_db):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(db_dir, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            shutil.copy2(server_db, os.path.join(backup_dir, f"equipment_{ts}.db"))

        # 3. 업로드 DB 열기 & 검증
        src = sqlite3.connect(tmp.name)
        src.row_factory = sqlite3.Row
        src_tables = [r[0] for r in src.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        # 4. 서버 DB 열기
        dst = sqlite3.connect(server_db)
        dst.row_factory = sqlite3.Row

        result = {"ok": True, "merged": {}}

        # 5. device_info 병합 (REPLACE — name 기준)
        if "device_info" in src_tables:
            rows = [dict(r) for r in src.execute("SELECT * FROM device_info").fetchall()]
            for r in rows:
                dst.execute("""
                    INSERT OR REPLACE INTO device_info
                    (id, name, category, summary, target, mechanism, note, aliases,
                     usage_count, is_verified, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (r["id"], r["name"], r.get("category"), r.get("summary"),
                      r.get("target"), r.get("mechanism"), r.get("note"),
                      r.get("aliases"), r.get("usage_count", 0),
                      r.get("is_verified", 0), r.get("created_at"), r.get("updated_at")))
            result["merged"]["device_info"] = len(rows)

        # 6. papers 병합 (REPLACE — id 기준)
        if "papers" in src_tables:
            rows = [dict(r) for r in src.execute("SELECT * FROM papers").fetchall()]
            # papers 컬럼 동적 처리
            if rows:
                cols = list(rows[0].keys())
                placeholders = ",".join(["?"] * len(cols))
                col_names = ",".join(cols)
                for r in rows:
                    vals = [r.get(c) for c in cols]
                    dst.execute(f"INSERT OR REPLACE INTO papers ({col_names}) VALUES ({placeholders})", vals)
            result["merged"]["papers"] = len(rows)

        dst.commit()

        # 7. 결과 집계
        di_count = dst.execute("SELECT COUNT(*) FROM device_info").fetchone()[0]
        paper_count = dst.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        cafe_count = dst.execute("SELECT COUNT(*) FROM cafe_articles").fetchone()[0]

        src.close()
        dst.close()

        result["device_info_count"] = di_count
        result["papers_count"] = paper_count
        result["cafe_articles_count"] = cafe_count
        result["message"] = f"장비 {result['merged'].get('device_info', 0)}건, 논문 {result['merged'].get('papers', 0)}건 병합 완료. 카페 원고 {cafe_count}건 유지."

    except Exception as e:
        import traceback
        return {"ok": False, "error": f"병합 실패: {str(e)}", "detail": traceback.format_exc()}
    finally:
        os.unlink(tmp.name)

    return result
