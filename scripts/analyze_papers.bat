@echo off
cd /d "%~dp0\.."

echo ========================================
echo   Paper Analyzer
echo ========================================
echo.

python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

echo.
echo Select folder method:
echo   [1] Type path
echo   [2] Browse folder
echo.
set /p "choice=Select (1 or 2): "

if "%choice%"=="2" (
    for /f "delims=" %%i in ('powershell -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.FolderBrowserDialog; if($d.ShowDialog() -eq 'OK'){$d.SelectedPath}"') do set "FOLDER=%%i"
) else (
    set /p "FOLDER=Folder path: "
)

if "%FOLDER%"=="" (
    echo ERROR: No folder selected
    pause
    exit /b 1
)

echo.
echo Folder: %FOLDER%
echo.

set /p "APIKEY=API Key (sk-ant-...): "
if "%APIKEY%"=="" (
    echo ERROR: No API key
    pause
    exit /b 1
)

set "ANTHROPIC_API_KEY=%APIKEY%"

echo.
echo   [1] Real analysis (save to DB)
echo   [2] Test mode (no save)
set /p "mode=Select (1 or 2): "

set "EXTRA="
if "%mode%"=="2" set "EXTRA=--dry-run"

echo.
echo Starting analysis...
echo.

python paper_analyzer.py --dir "%FOLDER%" %EXTRA%

echo.
echo Done! Results in: paper_results\
echo.
explorer "paper_results" 2>/dev/null
pause
