"""FastAPI 메인 앱.

Vue.js 프론트엔드와 연동 — SQLite DB(equipment.db) 사용.
"""

import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 허용 도메인: 환경변수 ALLOWED_ORIGINS (콤마 구분) 또는 기본값
_DEFAULT_ORIGINS = [
    "http://localhost:5173",   # Vite 개발 서버
    "http://localhost:8002",   # FastAPI 직접 접근
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8002",
]
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if o.strip()
] or _DEFAULT_ORIGINS

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 DB 테이블 보장 + 스케줄러 시작."""
    from init_db import init_db
    init_db()

    from api.scheduler import setup_scheduler, scheduler
    setup_scheduler()

    yield

    scheduler.shutdown()


app = FastAPI(
    title="유앤아이의원 통합 관리 API",
    version="1.0.0",
    lifespan=lifespan,
    root_path="/api",
)

# CORS — 허용 도메인만 접근 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
from api.routers import auth, users, cafe, equipment, events, papers, blog, place, webpage, treatment_catalog, complaints, reports, branch_info

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(cafe.router, prefix="/cafe", tags=["Cafe"])
app.include_router(equipment.router, prefix="/equipment", tags=["Equipment"])
app.include_router(events.router, prefix="/events", tags=["Events"])
app.include_router(papers.router)
app.include_router(blog.router)
app.include_router(place.router)
app.include_router(webpage.router)
app.include_router(treatment_catalog.router)
app.include_router(complaints.router)
app.include_router(reports.router)
app.include_router(branch_info.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/dashboard")
async def dashboard():
    """HOME 대시보드 — 전체 현황 요약."""
    from blog.post_queries import get_home_dashboard
    return get_home_dashboard()
