#!/bin/bash
set -e

echo "Starting Companion Cube Service..."
echo

# Navigate to project root if not already there
if [[ ! -f "CompanionCube.sln" ]]; then
    echo "Navigating to companion-cube directory..."
    cd "$(dirname "$0")/.."
fi

echo "Checking if LLM server is running..."
if ! curl -s http://localhost:5678/health > /dev/null 2>&1; then
    echo
    echo "⚠️ LLM server not detected. Starting it now..."
    echo "This may take a few moments..."
    
    # Start LLM server in background
    cd src/CompanionCube.LlmBridge/Python
    python llm_server.py --model ./models/mistral-7b.gguf --port 5678 &
    LLM_PID=$!
    cd ../../..
    
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