@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo    Git backup - first commit
echo ============================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed.
  echo Install "Git for Windows": https://git-scm.com/download/win
  echo Then run this again.
  echo.
  pause & exit /b 1
)

REM If this folder is not a valid repo but has a leftover/broken .git, reset it.
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
  if exist ".git" (
    echo Found an incomplete .git folder, removing it for a clean start...
    rmdir /s /q ".git"
  )
  echo Initializing new repository...
  git init -b main >nul 2>nul
  if errorlevel 1 (
    git init >nul
    git branch -M main
  )
)

git config user.name "G"
git config user.email "jtravel0802@gmail.com"

git add -A

echo.
echo === Sensitive-file guard (the next line should say OK) ===
git ls-files | findstr /R /C:"\.env$" /C:"\.db$" >nul && (
  echo [WARNING] An .env or .db file is about to be committed^! Check the list below and fix .gitignore before continuing.
) || (
  echo [OK] No real .env or database files are tracked. ^(.env.example is fine.^)
)

echo.
echo === Files staged for the first commit ===
git status --short

echo.
git commit -m "Phase 1: GRE vocab SRS - backend, frontend, launch scripts" >nul
if errorlevel 1 (
  echo [INFO] Nothing to commit, or commit failed. See messages above.
) else (
  echo [DONE] First commit created.
)

echo.
echo === History ===
git log --oneline

echo.
echo ============================================
echo  To back up to GitHub later:
echo   1) Create a new EMPTY repo on github.com (no README).
echo   2) Run these two lines here (replace YOURNAME):
echo        git remote add origin https://github.com/YOURNAME/toefl-gre-app.git
echo        git push -u origin main
echo ============================================
echo.
pause
