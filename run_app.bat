@echo off
setlocal

:: --- CONFIGURATION ---
set "VENV_DIR=.venv"
set "REQUIREMENTS=requirements.txt"
set "MAIN_SCRIPT=main.py"

echo ========================================================
echo       Financial Dashboard Launcher (Powered by uv)
echo ========================================================

:: 1. CHECK FOR PYTHON
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

:: 2. CHECK FOR UV (Install if missing)
call uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] 'uv' tool not found. Installing uv via pip...
    pip install uv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install uv.
        pause
        exit /b 1
    )
) else (
    echo [OK] uv is installed.
)

:: 3. CHECK VIRTUAL ENVIRONMENT
:: If it exists, jump straight to running the app
if exist "%VENV_DIR%" goto RUN_APP

:: --- INSTALLATION BLOCK (Only runs if .venv is missing) ---
echo [INFO] Virtual environment '%VENV_DIR%' not found. Creating...
call uv venv %VENV_DIR%

if exist "%REQUIREMENTS%" (
    echo [INFO] Installing dependencies from %REQUIREMENTS%...
    call uv pip install -r %REQUIREMENTS%
) else (
    echo [WARNING] %REQUIREMENTS% not found! 
    echo Installing default dependencies (nicegui, pandas, numpy, openpyxl)...
    call uv pip install nicegui pandas numpy openpyxl
)
echo [OK] Installation complete.

:: 4. RUN THE APP
:RUN_APP
echo.
echo [INFO] Starting Dashboard...
echo ========================================================

:: Use the python executable inside the venv
"%VENV_DIR%\Scripts\python.exe" %MAIN_SCRIPT%

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] The application crashed or closed unexpectedly.
    pause
)