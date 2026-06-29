@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo    GRE Vocab SRS - phone mode (port 8000)
echo ============================================
echo.
echo Building frontend (one moment)...
pushd frontend
call npm run build
set "RC=%errorlevel%"
popd
if not "%RC%"=="0" (
  echo.
  echo [ERROR] Frontend build failed. Run start.bat once first to install deps.
  echo.
  pause & exit /b 1
)

echo.
echo ============================================
echo  Serving the app + API together on port 8000.
echo.
echo  SAME WI-FI: on this PC run 'ipconfig', find IPv4 (e.g. 192.168.1.23),
echo  then on your phone open:   http://YOUR_IP:8000
echo  (First time, allow Python through the Windows Firewall if it asks.)
echo.
echo  FROM ANYWHERE (HTTPS): open run_tunnel.bat in another window.
echo.
echo  Log in with the account in backend\.env (default user: admin).
echo  Close this window to stop.
echo ============================================
echo.
cd backend
call ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
echo [server stopped]
pause
