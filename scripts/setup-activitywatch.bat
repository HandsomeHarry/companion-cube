@echo off
echo Setting up ActivityWatch Integration for Companion Cube...

echo.
echo This script will help you set up ActivityWatch for use with Companion Cube.
echo.

echo Step 1: Checking if ActivityWatch is installed...
curl -s http://localhost:5600/api/0/info >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo ✅ ActivityWatch is running!
    goto :check_data
) else (
    echo ❌ ActivityWatch not detected.
    echo.
    echo Please install ActivityWatch first:
    echo 1. Download from: https://activitywatch.net
    echo 2. Or use Chocolatey: choco install activitywatch
    echo 3. Or use Scoop: scoop install activitywatch
    echo.
    echo After installation, start ActivityWatch and run this script again.
    pause
    exit /b 1
)

:check_data
echo.
echo Step 2: Checking ActivityWatch data buckets...
curl -s http://localhost:5600/api/0/buckets/ > temp_buckets.json 2>nul
if %ERRORLEVEL% EQU 0 (
    echo ✅ Successfully connected to ActivityWatch API
    echo.
    echo Available data sources:
    findstr /i "currentwindow" temp_buckets.json >nul && echo   • Window activity tracking
    findstr /i "afkstatus" temp_buckets.json >nul && echo   • AFK/idle detection
    findstr /i "web.tab.current" temp_buckets.json >nul && echo   • Web browsing data || echo   ⚠️  Web browsing data not found - consider installing browser extensions
    del temp_buckets.json >nul 2>&1
) else (
    echo ❌ Could not fetch ActivityWatch data
    echo Please ensure ActivityWatch is running properly.
    pause
    exit /b 1
)

echo.
echo Step 3: Updating Companion Cube configuration...

echo Enabling ActivityWatch integration in appsettings.json...
powershell -Command "(Get-Content src\CompanionCube.Service\appsettings.json) -replace '\"UseActivityWatch\": false', '\"UseActivityWatch\": true' | Set-Content src\CompanionCube.Service\appsettings.json"

echo.
echo Step 4: Testing the integration...
echo Starting Companion Cube configuration app to test connection...
start "" cmd /k "cd src\CompanionCube.ConfigApp && dotnet run && pause"

echo.
echo ✅ ActivityWatch integration setup complete!
echo.
echo Next steps:
echo 1. Use the configuration app that just opened to test the connection
echo 2. Install browser extensions for better web tracking:
echo    • Chrome/Edge: Search "ActivityWatch Web Watcher" in Chrome Web Store
echo    • Firefox: Search "ActivityWatch Web Watcher" in Firefox Add-ons
echo 3. Run the Companion Cube service: scripts\run-service.bat
echo.
echo For detailed setup instructions, see: docs\ActivityWatch-Integration.md
echo.
pause