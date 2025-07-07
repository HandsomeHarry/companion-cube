# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Companion Cube is a Python-based ADHD productivity assistant that monitors user activity through ActivityWatch and provides intelligent, supportive interventions using local LLM inference (Ollama).

## Commands

### Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Ensure ActivityWatch is running (required dependency)
# Check at: http://localhost:5600

# Optional: Set up Ollama for LLM features
ollama serve
ollama pull cas/mistral-7b-instruct-v0.3
```

### Running the Application
```bash
# Basic run (coach mode, 60s intervals)
python companion_main.py

# Run with specific mode and interval
python companion_main.py --mode study_buddy --interval 30

# Test connections only
python companion_main.py --test-connections

# Single activity check for testing
python companion_main.py --test

# Generate LLM-powered daily summary
python companion_main.py --daily-summary

# Generate weekly pattern insights using LLM
python companion_main.py --weekly-insights

# Generate comprehensive productivity pattern analysis
python companion_main.py --productivity-insights

# Specify LLM model (if you have it installed)
python companion_main.py --model mistral

# Enable verbose mode with detailed LLM prompts and processing info
# Also shows 1-minute activity summaries in real-time
python companion_main.py --verbose

# Combine options for verbose daily summary
python companion_main.py --verbose --daily-summary --model mistral

# Weekly insights with verbose LLM details
python companion_main.py --verbose --weekly-insights

# Productivity analysis with verbose output
python companion_main.py --verbose --productivity-insights
```

### Testing and Debugging
```bash
# Test all connections (ActivityWatch + Ollama)
python companion_main.py --test-connections

# Single activity snapshot for debugging
python companion_main.py --test

# View detailed logging and LLM processing
python companion_main.py --verbose
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
   - Prepares raw activity data with minimal pre-processing for LLM analysis
   - Provides detailed activity timelines, context switches, and usage statistics
   - Creates chronological activity sequences and app transition data
   - **NEW**: `prepare_raw_data_for_llm()` method provides comprehensive raw data instead of pre-categorized summaries
   - **NEW**: `_create_prioritized_timeline()` intelligently limits 5-minute data to 30 activities while preserving full context

3. **CompanionCube** (`companion_main.py`)
   - Main orchestrator with configurable intervention logic
   - Integrates with Ollama API on `localhost:11434`
   - Manages intervention cooldowns (flow: 45min, working: 15min, nudge: 5min)
   - Persists data in `data/` directory
   - **LLM-Powered Features**: 
     - **NEW**: Raw data analysis for state determination (`analyze_user_state_with_llm()`)
     - **NEW**: Structured JSON response parsing for consistent state detection
     - Daily summaries with enhanced context and timing
     - Hourly activity summaries (auto-generated every hour)
     - Weekly pattern insights and trends
     - Comprehensive productivity pattern analysis
     - Real-time minute summaries in verbose mode
     - Contextual ADHD-supportive interventions

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

**NEW LLM-Driven Analysis Pipeline:**
1. ActivityWatch raw events → minimal filtering → comprehensive data structure
2. Raw data (timeline, context switches, statistics) → LLM analysis prompt
3. LLM determines: `current_state`, `focus_trend`, `distraction_trend` + reasoning
4. Structured JSON response parsing → validated state determination  
5. State + LLM context → ADHD-specific intervention prompt → supportive response

**NEW Organized Data Persistence:**
6. 5-minute activity summaries logged to `data/log.json` (LLM analysis every 5 minutes)
7. 30-minute summaries generated every :00 and :30 (stored in memory, compiled into daily)
8. Daily summaries at 4am saved to `data/daily_summary.json` (practical tone with 30-min periods)
9. Pattern analysis uses comprehensive historical data across all timeframes

## Critical Implementation Details

- **3-Bucket Analysis Hierarchy**: AFK → Window → Web (web data only relevant when browser is active)
- **LLM Context Management**: 30 recent activities for 5-minute analysis, full 8K context for historical patterns  
- **Activity Timeline Prioritization**: Current events (5-min) prioritized over historical context in LLM prompts
- **Browser State Logic**: Web events ignored for current state unless user is actively in a browser app
- **Bucket Selection**: Uses `last_updated` timestamp to find active buckets (not hostname-based)
- **Time Handling**: Subtracts 2 seconds from "now" to avoid querying future timestamps  
- **State Detection**: LLM-powered analysis with current vs historical context separation
- **Prompt Engineering**: Clear hierarchy prevents "always on webpage" analysis errors
- **NEW Organized Data Storage**: Minimal files in `data/` directory (log.json, daily_summary.json only)
- **5-Minute Logging**: LLM state analysis logged every 5 minutes with comprehensive context
- **30-Minute Summaries**: Automatic practical summaries every :00 and :30 with activity breakdown
- **4am Daily Summaries**: Daily summaries generated at 4am (not midnight) with practical tone
- **Ctrl+C Clean Exit**: No summary generation on manual exit for cleaner workflow
- **Error Handling**: Graceful fallbacks when ActivityWatch or Ollama are unavailable
- **Signal Handling**: Clean shutdown without forced summaries
- **Intervention Cooldowns**: Prevents over-notification (flow: 45min, working: 15min, nudge: 5min)
- **LLM Integration**: Multiple specialized prompts for different analysis types
- **NEW LLM State Analysis**: Raw data analysis with structured JSON responses for state determination
- **Fallback Logic**: Rule-based analysis when LLM is unavailable 
- **Response Validation**: Strict parsing and validation of LLM JSON outputs
- **Verbose Mode**: Real-time minute-by-minute activity tracking
- **Pattern Analysis**: Cross-references comprehensive timeframe data for insights

## Codebase Structure

- **companion_main.py** (955 lines) - Main orchestrator with CompanionCube class
  - Handles CLI arguments, signal handling, intervention logic
  - Manages Ollama API integration and LLM prompt generation  
  - Implements daily/weekly summary generation with fallbacks
  
- **activitywatch_client.py** (334 lines) - ActivityWatch API client
  - Robust error handling with retries and exponential backoff
  - Multi-host bucket selection using timestamps
  - Timezone-aware date handling for query consistency
  
- **event_processor.py** (477 lines) - Activity analysis and pattern detection
  - App/website categorization (productivity vs distraction)
  - ADHD-specific pattern detection (rapid switching, hyperfocus)
  - State inference with context-aware reasoning