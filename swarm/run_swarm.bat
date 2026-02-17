@echo off
REM GSTD Swarm Client — Windows launcher for network participation
REM Usage:
REM   set GSTD_API_KEY=your_key
REM   set GSTD_WALLET=EQ...
REM   run_swarm.bat
REM
REM Or: run_swarm.bat --api-key KEY --wallet EQ...

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python required. Install from https://www.python.org/downloads/
    exit /b 1
)

REM Create venv if missing
if not exist ".venv" (
    echo [*] Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM Install dependencies
pip install -q requests websocket-client 2>nul

REM Run
python swarm_client.py %*