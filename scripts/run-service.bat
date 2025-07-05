@echo off
echo Starting Companion Cube Service...

echo.
echo Checking if LLM server is running...
curl -s http://localhost:5678/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️ LLM server not detected. Starting it now...
    echo This may take a few moments...
    start "LLM Server" cmd /k "cd src\CompanionCube.LlmBridge\Python && python llm_server.py --model .\models\phi-2-adhd.gguf --port 5678"
    
    echo Waiting for LLM server to start...
    timeout /t 10 /nobreak >nul
)

echo.
echo Starting Companion Cube Service...
cd src\CompanionCube.Service
dotnet run --configuration Release

pause