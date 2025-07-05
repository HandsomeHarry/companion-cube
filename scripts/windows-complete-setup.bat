@echo off
echo ================================================================
echo    COMPANION CUBE - Complete Windows Setup for Testing
echo ================================================================
echo.
echo This script will set up everything needed to test Companion Cube
echo on Windows with ActivityWatch and Ring-lite model.
echo.
pause

echo.
echo ================================================================
echo STEP 1: Checking Prerequisites
echo ================================================================

echo Checking .NET 6 SDK...
dotnet --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ .NET 6 SDK not found
    echo Please install from: https://dotnet.microsoft.com/download/dotnet/6.0
    pause
    exit /b 1
) else (
    echo ✅ .NET 6 SDK found
)

echo Checking Python...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python not found or not in PATH
    echo Please install Python 3.8+ from: https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
) else (
    echo ✅ Python found
)

echo.
echo ================================================================
echo STEP 2: Setting up ActivityWatch
echo ================================================================

echo Checking if ActivityWatch is running...
curl -s http://localhost:5600/api/0/info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ ActivityWatch is running!
) else (
    echo ❌ ActivityWatch not detected
    echo.
    echo Please install ActivityWatch:
    echo 1. Download from: https://activitywatch.net
    echo 2. Install and start ActivityWatch
    echo 3. Verify it's running by visiting: http://localhost:5600
    echo 4. Install browser extensions for web tracking
    echo.
    echo After ActivityWatch is running, press any key to continue...
    pause
    
    REM Check again
    curl -s http://localhost:5600/api/0/info >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo Still not detected. Please set up ActivityWatch first.
        pause
        exit /b 1
    )
)

echo.
echo ================================================================
echo STEP 3: Building Companion Cube
echo ================================================================

echo Restoring NuGet packages...
dotnet restore
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to restore packages
    pause
    exit /b 1
)

echo Building solution...
dotnet build --configuration Release
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Build failed
    pause
    exit /b 1
)

echo ✅ Build successful!

echo.
echo ================================================================
echo STEP 4: Setting up Ring-lite Model
echo ================================================================

call scripts\setup-ring-lite.bat
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Ring-lite setup failed
    pause
    exit /b 1
)

echo.
echo ================================================================
echo STEP 5: Testing Configuration
echo ================================================================

echo Testing ActivityWatch connection...
cd src\CompanionCube.ConfigApp
start "Config Test" cmd /k "dotnet run && pause"
cd ..\..

echo.
echo Please use the configuration app that just opened to:
echo 1. Select "ActivityWatch (Recommended)"
echo 2. Click "Test ActivityWatch Connection"
echo 3. Click "Test AI Connection" 
echo 4. Save settings
echo.
echo Press any key when configuration testing is complete...
pause

echo.
echo ================================================================
echo STEP 6: Final System Test
echo ================================================================

echo Starting complete system test...
echo.

echo 1. Starting LLM Server...
start "LLM Server" cmd /k "cd src\CompanionCube.LlmBridge\Python && python llm_server.py --model .\models\ring-lite.gguf --port 5678"

echo 2. Waiting for LLM server to start...
timeout /t 10 /nobreak >nul

echo 3. Testing LLM server...
curl -X POST http://localhost:5678/generate -H "Content-Type: application/json" -d "{\"prompt\": \"Test: User coding for 30 minutes. ADHD suggestion:\", \"max_tokens\": 30}"

echo.
echo 4. Starting Companion Cube Service...
start "Companion Cube" cmd /k "cd src\CompanionCube.Service && dotnet run --configuration Release"

echo.
echo ================================================================
echo SETUP COMPLETE!
echo ================================================================
echo.
echo ✅ All components are now running:
echo    • ActivityWatch (port 5600)
echo    • Ring-lite LLM Server (port 5678) 
echo    • Companion Cube Service
echo.
echo 🧪 TO TEST:
echo 1. Browse some websites (GitHub, Stack Overflow, YouTube)
echo 2. Switch between VS Code and browser
echo 3. Watch the Companion Cube Service logs for activity detection
echo 4. Look for AI-generated task inferences and suggestions
echo.
echo 📊 MONITOR:
echo • ActivityWatch: http://localhost:5600
echo • Service logs in the Companion Cube window
echo • LLM responses in the LLM Server window
echo.
echo 🔧 PROMPTS LOCATION:
echo • System prompt: src\CompanionCube.LlmBridge\Python\llm_server.py (line 19)
echo • Task inference: src\CompanionCube.LlmBridge\Services\LocalLlmService.cs (line ~180)
echo • State detection: src\CompanionCube.LlmBridge\Services\LocalLlmService.cs (line ~192)
echo • Suggestions: src\CompanionCube.LlmBridge\Services\LocalLlmService.cs (line ~207)
echo.
echo 📚 DOCUMENTATION:
echo • docs\Windows-Testing-Guide.md - Complete setup guide
echo • docs\LLM-Prompts-Reference.md - All prompt locations
echo • docs\ActivityWatch-Integration.md - ActivityWatch details
echo.
echo Happy testing! The system will now learn from your ActivityWatch data
echo and provide ADHD-focused productivity insights using Ring-lite.
echo.
pause