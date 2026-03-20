"""FastAPI 메인 앱.

기존 Streamlit 앱과 병행 운영 — 동일 DB(equipment.db)를 공유.
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
from api.routers import auth, users, cafe, equipment, events

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(cafe.router, prefix="/cafe", tags=["Cafe"])
app.include_router(equipment.router, prefix="/equipment", tags=["Equipment"])
app.include_router(events.router, prefix="/events", tags=["Events"])


@app.get("/health")
async def health():
    return {"status": "ok"}
