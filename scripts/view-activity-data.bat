@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo    ActivityWatch Data Viewer
echo ================================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Navigate to project root
cd /d "%PROJECT_ROOT%"
echo Project root: %CD%

echo.
echo Checking ActivityWatch connection...
curl -s http://localhost:5600/api/0/info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ ActivityWatch not detected.
    echo.
    echo Please ensure ActivityWatch is running:
    echo 1. Start ActivityWatch application
    echo 2. Wait for it to appear in system tray
    echo 3. Verify it's accessible at: http://localhost:5600
    echo.
    pause
    exit /b 1
)

echo ✅ ActivityWatch is running!

echo.
echo Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    python3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=python3"
    ) else (
        echo ❌ Python not found. Please install Python 3.8+ first.
        pause
        exit /b 1
    )
)

echo ✅ Python found: !PYTHON_CMD!

echo.
echo Installing required packages...
!PYTHON_CMD! -m pip install requests >nul 2>&1

echo.
echo ================================================================
echo Fetching ActivityWatch Data...
echo ================================================================
echo.

REM Run the ActivityWatch reader script
!PYTHON_CMD! "%PROJECT_ROOT%\scripts\activity_watch_reader.py"

echo.
echo ================================================================
echo.
echo Press any key to exit...
pause >nul