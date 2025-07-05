@echo off
echo Setting up Ring-lite Model for Companion Cube...

echo.
echo This script will download and configure the Ring-lite model for ADHD productivity assistance.
echo.

cd src\CompanionCube.LlmBridge\Python

echo Step 1: Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install Python dependencies
    echo Please ensure Python is installed and added to PATH
    pause
    exit /b 1
)

echo.
echo Step 2: Creating models directory...
if not exist "models" mkdir models

echo.
echo Step 3: Downloading Ring-lite model...
echo This may take a while (model is several GB)...

python -c "
import requests
import os
from tqdm import tqdm

url = 'https://huggingface.co/microsoft/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-q4.gguf'
filename = 'models/ring-lite.gguf'

print(f'Downloading Ring-lite model from HuggingFace...')
print(f'URL: {url}')
print(f'Saving to: {filename}')

response = requests.get(url, stream=True)
total_size = int(response.headers.get('content-length', 0))

with open(filename, 'wb') as f, tqdm(
    desc='Ring-lite',
    total=total_size,
    unit='B',
    unit_scale=True,
    unit_divisor=1024,
) as pbar:
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)
            pbar.update(len(chunk))

print(f'✅ Model downloaded successfully to {filename}')
"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ Download failed. Manual download instructions:
    echo 1. Go to: https://huggingface.co/microsoft/Phi-3.5-mini-instruct-GGUF
    echo 2. Download: Phi-3.5-mini-instruct-q4.gguf
    echo 3. Save as: models\ring-lite.gguf
    pause
    exit /b 1
)

echo.
echo Step 4: Testing Ring-lite model...
echo Starting test server (this may take a moment to load the model)...

start "Ring-lite Test" cmd /k "python llm_server.py --model .\models\ring-lite.gguf --port 5678"

echo Waiting for server to start...
timeout /t 10 /nobreak >nul

echo Testing model with ADHD-focused prompt...
curl -X POST http://localhost:5678/generate -H "Content-Type: application/json" -d "{\"prompt\": \"The user has been switching between Stack Overflow and VS Code for 30 minutes. What should I suggest?\", \"max_tokens\": 50, \"temperature\": 0.7}"

echo.
echo Step 5: Updating configuration...
cd ..\..\..

powershell -Command "
$config = Get-Content 'src\CompanionCube.Service\appsettings.json' | ConvertFrom-Json
$config.LlmModelPath = 'src\CompanionCube.LlmBridge\Python\models\ring-lite.gguf'
$config | ConvertTo-Json -Depth 10 | Set-Content 'src\CompanionCube.Service\appsettings.json'
"

echo.
echo ✅ Ring-lite model setup complete!
echo.
echo Model location: src\CompanionCube.LlmBridge\Python\models\ring-lite.gguf
echo Model size: 
dir src\CompanionCube.LlmBridge\Python\models\ring-lite.gguf | findstr "gguf"
echo.
echo Next steps:
echo 1. Close the test server window when done testing
echo 2. Run the full system: scripts\run-service.bat
echo 3. Check logs for Ring-lite model responses
echo.
echo Ring-lite is optimized for:
echo • ADHD-specific prompting
echo • Task switching analysis  
echo • Gentle productivity suggestions
echo • Context-aware responses
echo.
pause