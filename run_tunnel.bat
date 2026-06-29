@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  Cloudflare Tunnel - public HTTPS URL for your phone
echo ============================================
echo.

where cloudflared >nul 2>nul
if errorlevel 1 (
  echo cloudflared is not installed yet. Install it once, then run this again:
  echo.
  echo   Recommended:  winget install --id Cloudflare.cloudflared
  echo.
  echo   Or download cloudflared-windows-amd64.exe from
  echo   https://github.com/cloudflare/cloudflared/releases
  echo   rename it to cloudflared.exe and put it in this folder.
  echo.
  pause & exit /b 1
)

echo Make sure phone.bat is ALREADY running (port 8000) in another window.
echo.
echo Starting tunnel. A https URL like https://something.trycloudflare.com
echo will appear below - open THAT url on your phone (works on any network).
echo Note: this free URL changes every time you start the tunnel.
echo Close this window to stop the tunnel.
echo ============================================
echo.
cloudflared tunnel --url http://localhost:8000
echo.
echo [tunnel stopped]
pause
