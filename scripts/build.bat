@echo off
setlocal enabledelayedexpansion

echo Building Companion Cube Solution...
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Navigate to project root
cd /d "%PROJECT_ROOT%"
echo Project root: %CD%

echo.
echo Restoring NuGet packages...
dotnet restore

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Package restore failed!
    echo Check the output above for errors.
    pause
    exit /b 1
)

echo.
echo Building solution...
dotnet build --configuration Release --no-restore

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Build completed successfully!
    echo.
    echo Available commands:
    echo   scripts\run-service.bat     - Run the background service
    echo   scripts\run-config.bat      - Run the configuration app
    echo   scripts\setup-llm.bat       - Set up the LLM
    echo   scripts\test-llm.bat        - Test LLM server
) else (
    echo.
    echo ❌ Build failed!
    echo Check the output above for errors.
    pause
    exit /b 1
)

pause