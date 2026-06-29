@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set "LOG=%~dp0start_log.txt"
echo GRE-SRS start %date% %time% > "%LOG%"
echo cwd=%cd% >> "%LOG%"

echo ============================================
echo    GRE Vocab SRS - launcher
echo ============================================
echo.

REM ---------- 1. Python ----------
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  set "MSG=Python not found. Install Python 3.10+ and tick 'Add Python to PATH'. https://www.python.org/downloads/"
  goto fail
)
echo [1/5] Python = !PY!
echo [1/5] Python=!PY! >> "%LOG%"

REM ---------- 2. npm ----------
where npm >nul 2>nul
if errorlevel 1 (
  set "MSG=npm not found. Install Node.js 18+. https://nodejs.org/"
  goto fail
)
echo [2/5] npm found
echo [2/5] npm ok >> "%LOG%"

REM ---------- 3. backend venv + deps ----------
REM Check fastapi is actually installed (not just that the venv folder exists),
REM so a half-finished setup gets repaired instead of skipped.
if exist "backend\.venv\Lib\site-packages\fastapi\__init__.py" goto backend_ready
echo [3/5] Backend setup: creating venv and installing deps...
echo [3/5] creating venv >> "%LOG%"
pushd backend
!PY! -m venv .venv  >> "%LOG%" 2>&1
".venv\Scripts\python.exe" -m pip install --upgrade pip  >> "%LOG%" 2>&1
".venv\Scripts\python.exe" -m pip install -r requirements.txt  >> "%LOG%" 2>&1
set "RC=!errorlevel!"
popd
if not "!RC!"=="0" (
  set "MSG=Backend dependency install failed. Open start_log.txt for details. To retry, delete backend\.venv and run again."
  goto fail
)
:backend_ready
echo [3/5] backend ready
echo [3/5] backend ready >> "%LOG%"

REM ---------- 4. .env ----------
if exist "backend\.env" goto env_ready
copy ".env.example" "backend\.env" >nul
echo [4/5] Created backend\.env (default user: admin). Edit it to change APP_PASSWORD and JWT_SECRET.
echo [4/5] created .env >> "%LOG%"
:env_ready

REM ---------- 5. frontend deps ----------
if exist "frontend\node_modules" goto frontend_ready
echo [5/5] First-time frontend setup: installing deps (this is the slow step)...
echo [5/5] npm install >> "%LOG%"
pushd frontend
call npm install  >> "%LOG%" 2>&1
set "RC=!errorlevel!"
popd
if not "!RC!"=="0" (
  set "MSG=Frontend dependency install failed. Open start_log.txt for details."
  goto fail
)
:frontend_ready
echo [5/5] frontend ready
echo [5/5] frontend ready >> "%LOG%"

REM ---------- launch services ----------
echo.
echo Launching two windows: backend (8000) and frontend (5173)...
echo launching >> "%LOG%"
start "GRE-SRS backend :8000" "%~dp0run_backend.bat"
start "GRE-SRS frontend :5173" "%~dp0run_frontend.bat"

echo Waiting a few seconds for the frontend to start...
timeout /t 6 >nul
start "" http://localhost:5173

echo.
echo ============================================
echo  Done. Browser should open http://localhost:5173
echo  Log in with the account in backend\.env (default user: admin).
echo.
echo  Phone on same Wi-Fi: run 'ipconfig', find your IPv4,
echo  then open http://YOUR_IP:5173 on the phone.
echo.
echo  To stop: close the two black service windows.
echo ============================================
echo.
echo This window can be closed. Press any key to exit (services keep running)...
pause >nul
goto :eof

:fail
echo.
echo ============================================
echo  [ERROR] !MSG!
echo ============================================
echo  (details in start_log.txt)
echo FAILED: !MSG! >> "%LOG%"
echo.
echo Press any key to close...
pause >nul
goto :eof
