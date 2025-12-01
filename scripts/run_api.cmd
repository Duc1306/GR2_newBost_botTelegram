@echo off
setlocal ENABLEDELAYEDEXPANSION
REM Run FastAPI dev server
set ROOT=%~dp0\..
cd /d %ROOT%
set PYTHONPATH=%ROOT%
call venv\Scripts\activate.bat
uvicorn src.api.main:app --reload --port 8000
endlocal
