#!/bin/bash
set -e

echo "Setting up LLM for Companion Cube..."
echo

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Navigate to project root
cd "$PROJECT_ROOT"

echo "Project root: $(pwd)"

echo "Installing Python dependencies..."
cd src/CompanionCube.LlmBridge/Python

# Check for Python and pip
PYTHON_CMD=""
PIP_CMD=""

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python not found. Please install Python 3.8+ first."
    exit 1
fi

if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "❌ pip not found. Please install pip first."
    exit 1
fi

echo "Using $PYTHON_CMD and $PIP_CMD"
$PIP_CMD install -r requirements.txt

echo
echo "Creating models directory..."
mkdir -p models

echo
echo "Downloading mistral-7b model..."
$PYTHON_CMD download_model.py --model mistral-7b --output ./models

if [ $? -eq 0 ]; then
    echo
    echo "✅ LLM setup completed successfully!"
    echo
    echo "The AI model is ready for use."
    echo "Model location: src/CompanionCube.LlmBridge/Python/models/mistral-7b.gguf"
    echo
    echo "To test the LLM server:"
    echo "  scripts/test-llm.sh"
else
    echo
    echo "❌ LLM setup failed!"
    echo "Check your internet connection and try again."
    exit 1
fi

cd "$PROJECT_ROOT"