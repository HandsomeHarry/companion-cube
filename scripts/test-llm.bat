@echo off
setlocal enabledelayedexpansion

echo Testing LLM Server...
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Navigate to project root
cd /d "%PROJECT_ROOT%"
echo Project root: %CD%

echo.
echo Starting LLM server (this may take a few moments)...
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

REM Start server in background
start "LLM Server" cmd /c "%PYTHON_CMD% llm_server.py --model .\models\mistral-7b.gguf --port 5678"

echo.
echo Waiting for server to start...
timeout /t 10 /nobreak >nul

REM Test health endpoint
echo.
echo Testing health endpoint...
curl -X GET http://localhost:5678/health
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Health check passed!
) else (
    echo.
    echo ❌ Health check failed!
    taskkill /f /im python.exe /fi "WINDOWTITLE eq LLM Server*" >nul 2>&1
    cd /d "%PROJECT_ROOT%"
    pause
    exit /b 1
)

echo.
echo Testing text generation...
curl -X POST http://localhost:5678/generate -H "Content-Type: application/json" -d "{\"prompt\": \"The user is using Visual Studio Code to edit a Python file. What task are they doing?\", \"max_tokens\": 20}"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Text generation test passed!
) else (
    echo.
    echo ❌ Text generation test failed!
)

echo.
echo ✅ LLM test completed!
echo.
echo If you see successful responses above, the LLM is working correctly.
echo Press any key to stop the LLM server and exit.

cd /d "%PROJECT_ROOT%"
pause

REM Stop the LLM server
taskkill /f /im python.exe /fi "WINDOWTITLE eq LLM Server*" >nul 2>&1