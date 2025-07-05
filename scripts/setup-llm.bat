@echo off
echo Setting up LLM for Companion Cube...

echo.
echo Installing Python dependencies...
cd src\CompanionCube.LlmBridge\Python
pip install -r requirements.txt

echo.
echo Downloading lightweight model (phi-2-adhd)...
python download_model.py --model phi-2-adhd --output .\models

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ LLM setup completed successfully!
    echo.
    echo The AI model is ready for use.
    echo Model location: src\CompanionCube.LlmBridge\Python\models\phi-2-adhd.gguf
    echo.
    echo To test the LLM server:
    echo   scripts\test-llm.bat
) else (
    echo.
    echo ❌ LLM setup failed!
    echo Check your internet connection and try again.
)

cd ..\..\..
pause