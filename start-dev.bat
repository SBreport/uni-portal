@echo off
chcp 65001 >nul 2>&1
echo ========================================
echo   uni-portal DEV SERVER
echo ========================================
echo.

cd /d %~dp0

echo [1/2] Backend (FastAPI :8002)...
start "uni-api" cmd /k "cd /d %~dp0 && python -m uvicorn api.main:app --port 8002 --reload"

timeout /t 2 /nobreak >nul

echo [2/2] Frontend (Vite :5173)...
start "uni-frontend" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo   waiting for servers...
timeout /t 8 /nobreak >nul

echo.
echo ========================================
echo.
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8002
echo   API Docs : http://localhost:8002/api/docs
echo.
echo ========================================

start http://localhost:5173
pause
