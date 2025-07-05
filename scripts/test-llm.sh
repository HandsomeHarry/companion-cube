#!/bin/bash
set -e

echo "Testing LLM Server..."
echo

# Navigate to project root if not already there
if [[ ! -f "CompanionCube.sln" ]]; then
    echo "Navigating to companion-cube directory..."
    cd "$(dirname "$0")/.."
fi

echo "Starting LLM server (this may take a few moments)..."
cd src/CompanionCube.LlmBridge/Python

# Start server in background
python llm_server.py --model ./models/mistral-7b.gguf --port 5678 &
LLM_PID=$!

echo
echo "Waiting for server to start..."
sleep 10

# Test health endpoint
echo
echo "Testing health endpoint..."
if curl -X GET http://localhost:5678/health; then
    echo
    echo "✅ Health check passed!"
else
    echo
    echo "❌ Health check failed!"
    kill $LLM_PID 2>/dev/null || true
    exit 1
fi

echo
echo "Testing text generation..."
if curl -X POST http://localhost:5678/generate \
    -H "Content-Type: application/json" \
    -d '{"prompt": "The user is using Visual Studio Code to edit a Python file. What task are they doing?", "max_tokens": 20}'; then
    echo
    echo "✅ Text generation test passed!"
else
    echo
    echo "❌ Text generation test failed!"
fi

echo
echo "✅ LLM test completed!"
echo
echo "If you see successful responses above, the LLM is working correctly."
echo "Press Ctrl+C to stop the LLM server."

# Keep server running until user stops it
wait $LLM_PID