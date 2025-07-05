@echo off
echo Testing LLM Server...

echo.
echo Starting LLM server (this may take a few moments)...
cd src\CompanionCube.LlmBridge\Python
start "LLM Server" cmd /k "python llm_server.py --model .\models\mistral-7b.gguf --port 5678"

echo.
echo Waiting for server to start...
timeout /t 10 /nobreak >nul

echo.
echo Testing health endpoint...
curl -X GET http://localhost:5678/health

echo.
echo Testing text generation...
curl -X POST http://localhost:5678/generate -H "Content-Type: application/json" -d "{\"prompt\": \"The user is using Visual Studio Code to edit a Python file. What task are they doing?\", \"max_tokens\": 20}"

echo.
echo ✅ LLM test completed!
echo.
echo If you see successful responses above, the LLM is working correctly.
echo You can close the LLM server window when done testing.

cd ..\..\..
pause