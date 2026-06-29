@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo    Push to GitHub
echo ============================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git not installed: https://git-scm.com/download/win
  pause & exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  echo [ERROR] This folder is not a git repo yet. Run git_init.bat first.
  pause & exit /b 1
)

echo Staging all changes...
git add -A

echo Committing (ok if it says "nothing to commit")...
git commit -m "Tools 2 and 3, vocab autofill, dedup, TTS, browse, Docker deploy" 1>nul 2>nul

echo.
echo === Safety check: no secrets / db tracked (should say OK) ===
git ls-files | findstr /R /C:"\.env$" /C:"\.db$" >nul && (
  echo [WARNING] a .env or .db is tracked - stop and tell me before pushing.
) || (
  echo [OK] no real .env or database files are tracked.
)
echo.

echo First create an EMPTY repo on github.com (no README), then paste its URL below.
echo Example: https://github.com/yourname/toefl-gre-app.git
set /p URL="Repo URL: "
if "%URL%"=="" ( echo No URL entered. & pause & exit /b 1 )

git remote remove origin 1>nul 2>nul
git remote add origin %URL%
git branch -M main

echo.
echo Pushing... (a browser/login window may pop up the first time)
git push -u origin main

echo.
echo Done. Refresh your GitHub repo page to confirm the files are there.
echo (backend\.env, the database and node_modules are intentionally NOT uploaded.)
pause
