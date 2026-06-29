@echo off
title GRE-SRS frontend :5173
cd /d "%~dp0frontend"
echo [frontend] starting... open http://localhost:5173
echo [frontend] close this window to stop the frontend.
echo.
call npm run dev
echo.
echo [frontend] stopped.
pause
