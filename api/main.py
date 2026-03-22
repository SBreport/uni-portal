"""FastAPI 메인 앱.

Vue.js 프론트엔드와 연동 — SQLite DB(equipment.db) 사용.
"""

import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 DB 테이블 보장."""
    from init_db import init_db
    init_db()
    yield


app = FastAPI(
    title="유앤아이의원 통합 관리 API",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api",
)

# CORS — Vue.js 개발 서버 및 프로덕션 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from api.routers import auth, users, cafe, equipment, events, papers

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(cafe.router, prefix="/cafe", tags=["Cafe"])
app.include_router(equipment.router, prefix="/equipment", tags=["Equipment"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(papers.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/dashboard")
async def dashboard():
    """HOME 대시보드 — 전체 현황 요약."""
    import sqlite3, os
    db_path = os.path.join(PROJECT_ROOT, "data", "equipment.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 지점 수
    branch_count = conn.execute("SELECT COUNT(*) FROM branches").fetchone()[0]

    # 장비 현황
    equip_total = conn.execute("SELECT COUNT(*) FROM equipment").fetchone()[0]
    equip_photo = conn.execute("SELECT COUNT(*) FROM equipment WHERE photo_status = 1").fetchone()[0]

    # 이벤트 현황 (현재 기간)
    evt_row = conn.execute("""
        SELECT p.label, COUNT(i.id) as cnt
        FROM evt_periods p JOIN evt_items i ON i.event_period_id = p.id
        WHERE p.is_current = 1 GROUP BY p.id
    """).fetchone()
    evt_label = evt_row["label"] if evt_row else "-"
    evt_count = evt_row["cnt"] if evt_row else 0

    # 카페 현황 (현재 기간)
    cafe_row = conn.execute("""
        SELECT p.label,
               COUNT(a.id) as total,
               SUM(CASE WHEN a.status = '발행완료' THEN 1 ELSE 0 END) as published,
               SUM(CASE WHEN a.status = '작성대기' THEN 1 ELSE 0 END) as pending
        FROM cafe_periods p
        JOIN cafe_branch_periods bp ON bp.cafe_period_id = p.id
        JOIN cafe_articles a ON a.branch_period_id = bp.id
        WHERE p.is_current = 1 GROUP BY p.id
    """).fetchone()
    cafe_label = cafe_row["label"] if cafe_row else "-"
    cafe_total = cafe_row["total"] if cafe_row else 0
    cafe_published = cafe_row["published"] if cafe_row else 0
    cafe_pending = cafe_row["pending"] if cafe_row else 0

    # 시술사전
    dict_total = conn.execute("SELECT COUNT(*) FROM device_info").fetchone()[0]
    dict_verified = conn.execute("SELECT COUNT(*) FROM device_info WHERE is_verified = 1").fetchone()[0]

    # 최근 동기화
    recent_syncs = [dict(r) for r in conn.execute(
        "SELECT sync_type, added, skipped, conflicts, synced_at FROM sync_log ORDER BY synced_at DESC LIMIT 5"
    ).fetchall()]

    conn.close()

    return {
        "branches": branch_count,
        "equipment": {"total": equip_total, "photo_done": equip_photo},
        "events": {"label": evt_label, "count": evt_count},
        "cafe": {"label": cafe_label, "total": cafe_total, "published": cafe_published, "pending": cafe_pending},
        "dictionary": {"total": dict_total, "verified": dict_verified},
        "recent_syncs": recent_syncs,
    }
