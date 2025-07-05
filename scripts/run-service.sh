#!/bin/bash
set -e

echo "Starting Companion Cube Service..."
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Navigate to project root
cd "$PROJECT_ROOT"

echo "Project root: $(pwd)"

echo "Checking if LLM server is running..."
if ! curl -s http://localhost:5678/health > /dev/null 2>&1; then
    echo
    echo "⚠️ LLM server not detected. Starting it now..."
    echo "This may take a few moments..."
    
    # Start LLM server in background
    cd "$PROJECT_ROOT/src/CompanionCube.LlmBridge/Python"
    
    # Check for Python command
    if command -v python3 &> /dev/null; then
        python3 llm_server.py --model ./models/mistral-7b.gguf --port 5678 &
    else
        python llm_server.py --model ./models/mistral-7b.gguf --port 5678 &
    fi
    LLM_PID=$!
    cd "$PROJECT_ROOT"
    
    echo "Waiting for LLM server to start..."
    sleep 10
    
    # Check if server started successfully
    if ! curl -s http://localhost:5678/health > /dev/null 2>&1; then
        echo "❌ Failed to start LLM server"
        kill $LLM_PID 2>/dev/null || true
        exit 1
    fi
    echo "✅ LLM server started successfully"
fi

echo
echo "Starting Companion Cube Service..."
cd src/CompanionCube.Service
dotnet run --configuration Release