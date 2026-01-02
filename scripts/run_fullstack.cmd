@echo off
REM Run both FastAPI backend and Next.js frontend
echo ========================================
echo  Starting NewsBot Full Stack
echo ========================================
echo.

echo Starting FastAPI backend on port 8000...
start "FastAPI Backend" cmd /k "cd /d c:\Users\84328\botTele && venv\Scripts\activate && python -m uvicorn src.api.main:app --reload"

timeout /t 3 /nobreak >nul

echo Starting Vite frontend on port 5173...
cd /d c:\Users\84328\botTele\web
start "Vite Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo  Both servers starting...
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo ========================================
pause
