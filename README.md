# Companion Cube

A Python-based ADHD productivity assistant that monitors user activity and provides supportive interventions using local LLM inference.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default settings
python companion_main.py

# Run with verbose logging
python companion_main.py --verbose

# Test connections
python companion_main.py --test-connections
```

## Requirements

- **ActivityWatch** running on `localhost:5600` (required)
- **Ollama** on `localhost:11434` (optional, for LLM features)

## Features

- Real-time activity monitoring via ActivityWatch
- ADHD-focused productivity state detection
- Local LLM analysis (privacy-first)
- Automatic daily summaries at 4am
- Organized data logging (5-minute intervals)
- Flow state protection and gentle interventions

## Data

All data is stored locally in the `data/` directory:
- `log.json` - 5-minute activity summaries
- `daily_summary.json` - Daily productivity summaries

## License

MIT