@echo off
cd /d "%~dp0backend"
echo ============================================
echo  Fill the GRE vocab deck to 1000 words (Claude)
echo ============================================
echo  - Runs from the backend folder so it writes to the SAME database the app uses.
echo  - Needs ANTHROPIC_API_KEY in backend\.env (already set).
echo  - You can press Ctrl+C anytime and run again later; saved words persist (auto de-dup).
echo.
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] Backend venv not found. Run start.bat once first to set it up.
  pause & exit /b 1
)
".venv\Scripts\python.exe" "..\seed\generate_vocab.py" --target 1000 --batch 25
echo.
echo Done. Open the app "Vocab" tab to browse; new words appear in daily
echo up to your daily new-card limit.
pause
