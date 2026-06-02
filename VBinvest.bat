@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON_BIN=.venv\Scripts\python.exe"
) else (
  set "PYTHON_BIN=python"
)

if defined AI_API_KEY (
  "%PYTHON_BIN%" -m scripts.save_secret AI_API_KEY
  set "AI_API_KEY="
)

if defined OPENDART_API_KEY (
  "%PYTHON_BIN%" -m scripts.save_secret OPENDART_API_KEY
  set "OPENDART_API_KEY="
)

"%PYTHON_BIN%" -m scripts.launcher %*
if errorlevel 1 (
  echo [실패] VBinvest 실행에 실패했습니다. (Failed to run launcher)
  pause
  exit /b 1
)

exit /b 0
