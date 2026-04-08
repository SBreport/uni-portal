"""FastAPI 메인 앱.

Vue.js 프론트엔드와 연동 — SQLite DB(equipment.db) 사용.
"""

import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from api.deps import get_current_user
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
from api.routers import auth, users, cafe, equipment, events, papers, blog, place, webpage, treatment_catalog, complaints, reports, branch_info, rank_checker, encyclopedia, branches, config, explorer

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
app.include_router(rank_checker.router)
app.include_router(encyclopedia.router)
app.include_router(branches.router)
app.include_router(config.router)
app.include_router(explorer.router, prefix="/explorer", tags=["Explorer"])


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/dashboard")
async def dashboard():
    """HOME 대시보드 — 전체 현황 요약."""
    from blog.post_queries import get_home_dashboard
    return get_home_dashboard()


@app.post("/daily-sync")
async def daily_sync_all(user: dict = Depends(get_current_user)):
    """일간 동기화 전체 실행 — 노션 + 플웹 스냅샷 + 제목 스크래핑."""
    from api.deps import ROLE_HIERARCHY
    if ROLE_HIERARCHY.get(user["role"], 0) < ROLE_HIERARCHY.get("admin", 3):
        from fastapi import HTTPException, status as st
        raise HTTPException(st.HTTP_403_FORBIDDEN, "관리자 권한 필요")

    results = {}

    # 1. 블로그 노션 동기화
    try:
        from blog.sync_notion import incremental_sync, NOTION_BLOG_DB_ID
        from blog.post_queries import get_notion_token
        token = get_notion_token()
        db_id = NOTION_BLOG_DB_ID
        if token and db_id:
            r = incremental_sync(token, db_id)
            results["blog_sync"] = {"ok": True, **r}
        else:
            results["blog_sync"] = {"ok": False, "message": "노션 토큰/DB ID 미설정"}
    except Exception as e:
        results["blog_sync"] = {"ok": False, "message": str(e)}

    # 2. 플레이스 스냅샷
    try:
        from place.daily_snapshot import take_snapshot as place_snap
        r = place_snap()
        results["place_snapshot"] = {"ok": True, **(r if isinstance(r, dict) else {"message": str(r)})}
    except Exception as e:
        results["place_snapshot"] = {"ok": False, "message": str(e)}

    # 3. 웹페이지 스냅샷
    try:
        from webpage.daily_snapshot import take_snapshot as web_snap
        r = web_snap()
        results["webpage_snapshot"] = {"ok": True, **(r if isinstance(r, dict) else {"message": str(r)})}
    except Exception as e:
        results["webpage_snapshot"] = {"ok": False, "message": str(e)}

    # 4. 블로그 제목 스크래핑 (새로 들어온 것만)
    try:
        from blog.scrape_titles import scrape_missing_titles
        r = scrape_missing_titles(limit=50, delay=0.2)
        results["title_scrape"] = {"ok": True, **r}
    except Exception as e:
        results["title_scrape"] = {"ok": False, "message": str(e)}

    return results
