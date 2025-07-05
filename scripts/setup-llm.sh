#!/bin/bash
set -e

echo "Setting up LLM for Companion Cube..."
echo

# Navigate to project root if not already there
if [[ ! -f "CompanionCube.sln" ]]; then
    echo "Navigating to companion-cube directory..."
    cd "$(dirname "$0")/.."
fi

echo "Installing Python dependencies..."
cd src/CompanionCube.LlmBridge/Python

if ! command -v pip &> /dev/null; then
    echo "❌ pip not found. Please install Python and pip first."
    exit 1
fi

pip install -r requirements.txt

echo
echo "Creating models directory..."
mkdir -p models

echo
echo "Downloading mistral-7b model..."
python download_model.py --model mistral-7b --output ./models

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

cd ../../..