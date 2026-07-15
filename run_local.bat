@echo off
REM ============================================================
REM  NZF WW Knowledgebase - start locally on Windows
REM  Opens the app at http://localhost:8000
REM ============================================================
cd /d "%~dp0"

if not exist ".env" (
  echo.
  echo   No .env file found.
  echo   Please copy ".env.example" to ".env" and paste your client secret.
  echo.
  pause
  exit /b 1
)

if not exist "backend\.venv\Scripts\python.exe" (
  echo.
  echo   Python environment not found in backend\.venv
  echo.
  pause
  exit /b 1
)

echo.
echo   Starting NZF WW Knowledgebase at http://localhost:8000
echo   (Press Ctrl+C to stop.)
echo.
cd backend
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
