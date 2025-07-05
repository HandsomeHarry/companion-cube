#!/bin/bash
set -e

echo "Building Companion Cube Solution..."
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Navigate to project root
cd "$PROJECT_ROOT"

echo "Project root: $(pwd)"

echo "Restoring NuGet packages..."
dotnet restore

echo
echo "Building solution..."
dotnet build --configuration Release --no-restore

if [ $? -eq 0 ]; then
    echo
    echo "✅ Build completed successfully!"
    echo
    echo "Available commands:"
    echo "  scripts/run-service.sh     - Run the background service"
    echo "  scripts/run-config.sh      - Run the configuration app"
    echo "  scripts/setup-llm.sh       - Set up the LLM"
    echo "  scripts/test-llm.sh        - Test LLM server"
else
    echo
    echo "❌ Build failed!"
    echo "Check the output above for errors."
    exit 1
fi