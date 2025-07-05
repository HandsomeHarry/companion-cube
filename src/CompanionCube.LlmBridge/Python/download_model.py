#!/usr/bin/env python3
"""
Download and prepare ADHD-optimized LLM model for Companion Cube
"""

import os
import sys
import requests
import argparse
from pathlib import Path

# Recommended models for local deployment
RECOMMENDED_MODELS = {
    "phi-2-adhd": {
        "url": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf",
        "size": "1.6GB",
        "description": "Lightweight model suitable for task inference"
    },
    "mistral-7b": {
        "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size": "4.1GB",
        "description": "Balanced model for behavior analysis"
    },
    "llama2-7b-adhd": {
        "url": "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf",
        "size": "3.8GB",
        "description": "Comprehensive model for all features"
    }
}

def download_model(model_name: str, output_dir: str):
    """Download the specified model"""
    if model_name not in RECOMMENDED_MODELS:
        print(f"Unknown model: {model_name}")
        print(f"Available models: {', '.join(RECOMMENDED_MODELS.keys())}")
        return False
    
    model_info = RECOMMENDED_MODELS[model_name]
    output_path = Path(output_dir) / f"{model_name}.gguf"
    
    print(f"Downloading {model_name} ({model_info['size']})...")
    print(f"Description: {model_info['description']}")
    print(f"Output: {output_path}")
    
    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download with progress
    response = requests.get(model_info['url'], stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    progress = downloaded / total_size * 100
                    print(f"\rProgress: {progress:.1f}%", end='')
    
    print(f"\nModel downloaded successfully to {output_path}")
    return True

def create_model_config(model_name: str, output_dir: str):
    """Create configuration file for the model"""
    config = {
        "model_name": model_name,
        "model_path": f"{model_name}.gguf",
        "context_length": 2048,
        "adhd_prompts": {
            "system": "You are Companion Cube, an ADHD productivity assistant focused on support without judgment.",
            "task_inference": "Based on the user's activity, infer their current task. Be specific but understanding.",
            "state_detection": "Analyze behavior patterns to detect if the user is in flow, working, needs support, or away.",
            "encouragement": "Provide gentle, non-judgmental encouragement that celebrates progress."
        }
    }
    
    config_path = Path(output_dir) / f"{model_name}_config.json"
    
    import json
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"Configuration saved to {config_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download ADHD-optimized LLM for Companion Cube')
    parser.add_argument('--model', default='mistral-7b', 
                       choices=list(RECOMMENDED_MODELS.keys()),
                       help='Model to download')
    parser.add_argument('--output', default='./models', 
                       help='Output directory for model files')
    
    args = parser.parse_args()
    
    print("Companion Cube Model Downloader")
    print("================================")
    
    if download_model(args.model, args.output):
        create_model_config(args.model, args.output)
        print("\nSetup complete! You can now use this model with Companion Cube.")
        print(f"Model path: {Path(args.output) / f'{args.model}.gguf'}")
    else:
        sys.exit(1)