@echo off
setlocal enabledelayedexpansion

echo Starting Companion Cube Configuration App...
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%\.."

REM Navigate to project root
cd /d "%PROJECT_ROOT%"
echo Project root: %CD%

echo.
echo Starting Configuration App...
cd "%PROJECT_ROOT%\src\CompanionCube.ConfigApp"
dotnet run --configuration Release

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Failed to start Configuration App!
    echo Make sure the solution is built first with: scripts\build.bat
    cd /d "%PROJECT_ROOT%"
    pause
    exit /b 1
)

cd /d "%PROJECT_ROOT%"
pause