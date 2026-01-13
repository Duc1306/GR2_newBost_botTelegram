@echo off
REM Run both FastAPI backend and Vite frontend
echo ========================================
echo  Starting NewsBot Full Stack
echo ========================================
echo.

echo Starting FastAPI backend on port 8000...
start "FastAPI Backend" cmd /k "cd /d c:\Users\84328\botTele && python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo Starting Vite frontend on port 5174...
cd /d c:\Users\84328\botTele\web
start "Vite Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo  Both servers starting...
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo ========================================
pause
