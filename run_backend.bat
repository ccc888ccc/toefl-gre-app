@echo off
title GRE-SRS backend :8000
cd /d "%~dp0backend"
echo [backend] starting... API docs: http://localhost:8000/docs
echo [backend] close this window to stop the backend.
echo.
call ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
echo [backend] stopped.
pause
