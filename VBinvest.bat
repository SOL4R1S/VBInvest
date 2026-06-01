@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_BIN=.venv\Scripts\python.exe"
) else (
  set "PYTHON_BIN=python"
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Install Node.js, then run this launcher again.
  exit /b 1
)

if defined AI_API_KEY (
  "%PYTHON_BIN%" -m scripts.save_secret AI_API_KEY
  set "AI_API_KEY="
)
if defined OPENDART_API_KEY (
  "%PYTHON_BIN%" -m scripts.save_secret OPENDART_API_KEY
  set "OPENDART_API_KEY="
)

for /f %%p in ('"%PYTHON_BIN%" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()"') do set "API_PORT=%%p"
for /f %%p in ('"%PYTHON_BIN%" -c "import socket; s=socket.socket(); s.bind(('127.0.0.1', 0)); print(s.getsockname()[1]); s.close()"') do set "FRONTEND_PORT=%%p"

set "VBINVEST_API_BASE_URL=http://127.0.0.1:%API_PORT%"

start "VBinvest API" "%PYTHON_BIN%" -m uvicorn scripts.api:app --host 127.0.0.1 --port %API_PORT%
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:%FRONTEND_PORT%"

cd frontend
npx next dev -p %FRONTEND_PORT%
