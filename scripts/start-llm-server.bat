@echo off
setlocal enabledelayedexpansion

echo ================================================================
echo    Companion Cube LLM Server Startup
echo ================================================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Navigate to project root
cd /d "%PROJECT_ROOT%"
echo Project root: %CD%

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
echo Checking Python dependencies...
cd "%PROJECT_ROOT%\src\CompanionCube.LlmBridge\Python"

echo Installing/updating dependencies...
!PYTHON_CMD! -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install dependencies!
    echo Please check the error above and ensure you have a working Python environment.
    pause
    exit /b 1
)

echo ✅ Dependencies installed

echo.
echo Checking for model files...
echo Looking for models in: %CD%\models\

if not exist "models" (
    echo ❌ Models directory not found!
    echo Creating models directory...
    mkdir models
)

REM Check for common model files
set "MODEL_FILE="
if exist "models\mistral-7b.gguf" (
    set "MODEL_FILE=models\mistral-7b.gguf"
    echo ✅ Found: mistral-7b.gguf
) else if exist "models\ring-lite.gguf" (
    set "MODEL_FILE=models\ring-lite.gguf"
    echo ✅ Found: ring-lite.gguf
) else if exist "models\phi-2-adhd.gguf" (
    set "MODEL_FILE=models\phi-2-adhd.gguf"
    echo ✅ Found: phi-2-adhd.gguf
) else (
    echo ❌ No model files found!
    echo.
    echo Available options:
    echo 1. Download a model manually:
    echo    - Download a GGUF model file (like mistral-7b.gguf)
    echo    - Place it in: %CD%\models\
    echo.
    echo 2. Run the setup script:
    echo    - scripts\setup-llm.bat (for mistral-7b)
    echo    - scripts\setup-ring-lite.bat (for phi-3.5-mini)
    echo.
    echo Models directory contents:
    dir models
    echo.
    pause
    exit /b 1
)

echo.
echo Using model: !MODEL_FILE!
echo Model size:
dir "!MODEL_FILE!"

echo.
echo ================================================================
echo Starting LLM Server...
echo ================================================================
echo.
echo Server will start on: http://localhost:5678
echo Health check URL: http://localhost:5678/health
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the server
!PYTHON_CMD! llm_server.py --model "!MODEL_FILE!" --port 5678 --host 127.0.0.1

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Server failed to start!
    echo.
    echo Common issues:
    echo 1. Model file is corrupted or incompatible
    echo 2. Not enough RAM (models need 4-8GB+)
    echo 3. Missing dependencies
    echo 4. Port 5678 is already in use
    echo.
    echo Try:
    echo - Use a smaller model
    echo - Close other applications to free RAM
    echo - Check if another LLM server is running
    echo.
)

pause