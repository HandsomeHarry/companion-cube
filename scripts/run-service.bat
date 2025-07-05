@echo off
setlocal enabledelayedexpansion

echo Starting Companion Cube Service...
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Navigate to project root
cd /d "%PROJECT_ROOT%"
echo Project root: %CD%

echo.
echo Checking if LLM server is running...
curl -s http://localhost:5678/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ LLM server not detected. Starting it now...
    echo This may take a few moments...
    
    REM Change to Python directory
    cd "%PROJECT_ROOT%\src\CompanionCube.LlmBridge\Python"
    
    REM Check for Python command
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
    
    REM Start LLM server in background
    start "LLM Server" cmd /c "!PYTHON_CMD! llm_server.py --model .\models\mistral-7b.gguf --port 5678"
    cd /d "%PROJECT_ROOT%"
    
    echo Waiting for LLM server to start...
    timeout /t 10 /nobreak >nul
    
    REM Check if server started successfully
    curl -s http://localhost:5678/health >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo ❌ Failed to start LLM server
        taskkill /f /im python.exe /fi "WINDOWTITLE eq LLM Server*" >nul 2>&1
        pause
        exit /b 1
    )
    echo ✅ LLM server started successfully
)

echo.
echo Starting Companion Cube Service...
cd "%PROJECT_ROOT%\src\CompanionCube.Service"
dotnet run --configuration Release

pause