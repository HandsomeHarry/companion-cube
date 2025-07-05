@echo off
setlocal enabledelayedexpansion

echo Setting up LLM for Companion Cube...
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Navigate to project root
cd /d "%PROJECT_ROOT%"
echo Project root: %CD%

echo.
echo Installing Python dependencies...
cd "%PROJECT_ROOT%\src\CompanionCube.LlmBridge\Python"

REM Check for Python and pip
set "PYTHON_CMD="
set "PIP_CMD="

python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
) else (
    python3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=python3"
    ) else (
        echo ❌ Python not found. Please install Python 3.8+ first.
        cd /d "%PROJECT_ROOT%"
        pause
        exit /b 1
    )
)

pip --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PIP_CMD=pip"
) else (
    pip3 --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PIP_CMD=pip3"
    ) else (
        echo ❌ pip not found. Please install pip first.
        cd /d "%PROJECT_ROOT%"
        pause
        exit /b 1
    )
)

echo Using !PYTHON_CMD! and !PIP_CMD!
!PIP_CMD! install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Failed to install Python dependencies!
    cd /d "%PROJECT_ROOT%"
    pause
    exit /b 1
)

echo.
echo Creating models directory...
if not exist "models" mkdir models

echo.
echo Downloading mistral-7b model...
!PYTHON_CMD! download_model.py --model mistral-7b --output .\models

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ LLM setup completed successfully!
    echo.
    echo The AI model is ready for use.
    echo Model location: src\CompanionCube.LlmBridge\Python\models\mistral-7b.gguf
    echo.
    echo To test the LLM server:
    echo   scripts\test-llm.bat
) else (
    echo.
    echo ❌ LLM setup failed!
    echo Check your internet connection and try again.
    cd /d "%PROJECT_ROOT%"
    pause
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
pause