# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Companion Cube is a Python-based ADHD productivity assistant that monitors user activity through ActivityWatch and provides intelligent, supportive interventions using local LLM inference (Ollama).

## Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Basic run (coach mode, 60s intervals)
python companion_main.py

# Run with specific mode and interval
python companion_main.py --mode study_buddy --interval 30

# Test connections only
python companion_main.py --test-connections

# Single activity check for testing
python companion_main.py --test

# Generate daily summary
python companion_main.py --daily-summary

# Specify LLM model
python companion_main.py --model deepseek-r1-distill-qwen

# Enable verbose mode with detailed LLM prompts and processing info
python companion_main.py --verbose

# Combine options
python companion_main.py --verbose --test --model cas/mistral-7b-instruct-v0.3
```

### Available Modes
- `ghost` - Monitoring only, no interventions
- `coach` - Active suggestions based on patterns (default)
- `study_buddy` - Regular check-ins
- `weekend` - Minimal interventions

## Architecture

The system consists of three main components that work together:

1. **ActivityWatchClient** (`activitywatch_client.py`)
   - Interfaces with ActivityWatch API on `localhost:5600`
   - Intelligently selects buckets with most recent data (handles multi-host scenarios)
   - Fetches events from window, web, and AFK watchers
   - Provides multi-timeframe data collection (5min, 10min, 30min, 1hr, today)

2. **EventProcessor** (`event_processor.py`)
   - Filters noise from raw ActivityWatch events
   - Detects ADHD-relevant patterns: rapid task switching, hyperfocus, distractions
   - Determines user states: `flow`, `working`, `needs_nudge`, `afk`
   - Generates context-aware prompts for the LLM

3. **CompanionCube** (`companion_main.py`)
   - Main orchestrator with configurable intervention logic
   - Integrates with Ollama API on `localhost:11434`
   - Manages intervention cooldowns (flow: 45min, working: 15min, nudge: 5min)
   - Persists data in `data/` directory

## Key Design Principles

- **ADHD-Supportive**: All prompts focus on encouragement, never shame or judgment
- **Flow State Protection**: Detects and respects hyperfocus sessions (>15 min in same app)
- **Context-Aware**: Analyzes behavior across multiple timeframes to understand patterns
- **Privacy-First**: All processing happens locally, no cloud dependencies

## Troubleshooting Common Issues

### ActivityWatch 500 Errors
The client handles timezone format preferences and automatically retries. If persistent:
- Check if ActivityWatch is running: `http://localhost:5600`
- Verify buckets have data using the test commands
- The system auto-selects buckets with most recent data

### Ollama Connection
- System works without Ollama using fallback responses
- To enable LLM: `ollama serve` then `ollama pull cas/mistral-7b-instruct-v0.3`
- Test with: `python companion_main.py --test-connections`

## Data Flow

1. ActivityWatch events → filtered summaries → behavior patterns → user state
2. State + context → ADHD-specific prompt → Ollama LLM → supportive response
3. All interactions logged to `data/interactions.json`
4. Daily summaries saved to `data/daily_summaries.json`

## Critical Implementation Details

- **Bucket Selection**: Uses `last_updated` timestamp to find active buckets (not hostname-based)
- **Time Handling**: Subtracts 2 seconds from "now" to avoid querying future timestamps
- **State Detection**: Based on app switches, focus duration, and distraction ratio
- **Prompt Generation**: State-specific, keeping responses under 50 words for ADHD-friendly brevity