@echo off
echo Building Companion Cube Solution...

echo.
echo Restoring NuGet packages...
dotnet restore

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
    echo   scripts\test-system.bat     - Run system tests
) else (
    echo.
    echo ❌ Build failed!
    echo Check the output above for errors.
)

pause