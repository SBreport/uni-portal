#!/bin/bash

# DB 초기화 (테이블이 없으면 생성)
python init_db.py

# cron 데몬 시작 (백그라운드 — 매일 새벽 3시 동기화)
cron

# Streamlit 앱 실행
exec streamlit run app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
