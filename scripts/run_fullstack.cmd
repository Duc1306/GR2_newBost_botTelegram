@echo off
REM Run both FastAPI backend and Next.js frontend
echo ========================================
echo  Starting NewsBot Full Stack
echo ========================================
echo.

echo Starting FastAPI backend on port 8000...
start "FastAPI Backend" cmd /k "cd /d c:\Users\84328\botTele && venv\Scripts\activate && python -m uvicorn src.api.main:app --reload"

timeout /t 3 /nobreak >nul

echo Starting React frontend on port 3000...
cd /d c:\Users\84328\botTele\web
start "React Frontend" cmd /k "npm start"

echo.
echo ========================================
echo  Both servers starting...
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:3000
echo ========================================
pause
