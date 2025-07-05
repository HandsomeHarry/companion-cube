@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo    Simple LLM Server Test
echo ================================================================
echo.

echo Testing LLM server at http://localhost:5678
echo.

echo 1. Testing health endpoint...
curl -s http://localhost:5678/health
set "HEALTH_STATUS=%ERRORLEVEL%"

echo.
echo.

if %HEALTH_STATUS% EQU 0 (
    echo ✅ Health check passed!
    echo.
    echo 2. Testing text generation...
    echo.
    curl -X POST http://localhost:5678/generate ^
         -H "Content-Type: application/json" ^
         -d "{\"prompt\": \"Hello, how are you?\", \"max_tokens\": 20, \"temperature\": 0.7}"
    
    if %ERRORLEVEL% EQU 0 (
        echo.
        echo.
        echo ✅ LLM server is working correctly!
    ) else (
        echo.
        echo.
        echo ❌ Text generation failed!
    )
) else (
    echo ❌ Health check failed!
    echo.
    echo The LLM server is not running or not responding.
    echo.
    echo To start the LLM server:
    echo   scripts\start-llm-server.bat
    echo.
    echo Make sure you have a model file in:
    echo   src\CompanionCube.LlmBridge\Python\models\
)

echo.
echo ================================================================
pause