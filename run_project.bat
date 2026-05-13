@echo off
title Fatek PLC Project Launcher

echo ==========================================
echo   Fatek PLC AI Assistant - Auto Launcher
echo ==========================================

:: 0. Check Port 8000
:: Check if any process is currently LISTENING on port 8000.
:: This ignores connections in TIME_WAIT status to avoid startup blocks.
netstat -ano | findstr :8000 | findstr LISTENING > nul

:: If errorlevel is 0, it means a match was found (port is occupied).
if %errorlevel% equ 0 (
    echo [Warning] Server is ALREADY running on port 8000.
    echo [Action] Please close the existing window first.
    echo.
    pause
    exit
)

:: 1. Virtual Environment Check
echo [Step 1/5] Checking Virtual Environment...
venv\Scripts\python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [Note] venv not found or incomplete. Initializing...
    python -m venv venv
) else (
    echo [OK] venv is ready.
)

:: 2. Activate Environment
echo [Step 2/5] Activating environment...
call venv\Scripts\activate
echo [OK] Virtual Environment Activated. Step 1/5 and Step 2/5 are completed.
echo.

:: 3. Install/Update Dependencies
echo [Step 3/5] Checking and installing dependencies...
pip install -r requirements.txt

:: Confirmation message after screen clearing
echo Virtual Environment Activated and Dependencies checked.
echo.

:: 4. Load Model
echo [Step 4/5] Loading AI Model...
lms load gemma-4-e4b-it-text-only
if %errorlevel% neq 0 (
    echo [Note] Could not load model via CLI.
) else (
    echo [OK] Model loaded.
)

:: 5. Start Server
echo [Step 5/5] Starting FastAPI backend in a new window...
echo ------------------------------------------
start cmd /k "uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for server to warm up
echo.
echo Waiting for server to initialize (10 seconds)...
timeout /t 20 /nobreak

:: 5. Open Dashboard
echo.
echo Opening Dashboard in your browser...
start http://localhost:8000

echo.
echo ==========================================
echo All systems are running. 
echo You can now access the RAG system from your iPad using Tailscale IP.
echo ==========================================
echo.
exit
