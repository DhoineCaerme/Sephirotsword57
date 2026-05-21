@echo off
REM ─────────────────────────────────────────────────────────────────────────
REM Sephirotsword57 :: first-time setup for Windows
REM
REM This creates the venv, installs dependencies, and validates the setup.
REM Run this ONCE after cloning the repo.
REM
REM Usage:
REM   setup.bat
REM ─────────────────────────────────────────────────────────────────────────

echo.
echo ============================================================
echo   SEPHIROTSWORD57 :: FIRST-TIME SETUP
echo ============================================================
echo.

REM Check Python version
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.11 is required but was not found.
    echo Install from: https://www.python.org/downloads/release/python-3119/
    exit /b 1
)

REM Create venv
if not exist venv (
    echo [1/4] Creating virtual environment with Python 3.11...
    py -3.11 -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        exit /b 1
    )
) else (
    echo [1/4] venv already exists, skipping creation.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
echo [2/4] Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo [3/4] Installing dependencies (this takes a few minutes)...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    exit /b 1
)

REM Create outputs dir
if not exist outputs (
    mkdir outputs
)

REM Run validation
echo.
echo [4/4] Validating setup...
python scripts\validate_setup.py

echo.
echo ============================================================
echo   SETUP COMPLETE
echo ============================================================
echo.
echo Next steps:
echo   1. Make sure your .env file has GEMINI_API_KEY or GROQ_API_KEY
echo   2. Run:  run.bat        (launches the UI)
echo   3. Or:   run.bat demo   (runs a quick CLI demo)
echo.