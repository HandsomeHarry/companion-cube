# Companion Cube - ADHD Productivity Assistant

A Windows-based ADHD productivity companion that combines background monitoring with a physical desk device to provide gentle, adaptive support.

## Project Status

### ✅ Phase 1: Core Infrastructure (Complete)
- Windows service architecture with activity monitoring
- SQLite database with Entity Framework Core
- Real-time activity logging and user state detection
- Pattern detection algorithms
- WPF configuration application
- Device communication protocol (Serial/USB)
- Arduino firmware for ESP32 device

### ✅ Phase 2: LLM Integration (Complete)
- Local LLM infrastructure using llama.cpp
- Python REST API server for LLM queries
- C# service interface for LLM integration
- Task inference from user activities
- ADHD-focused behavior analysis
- Adaptive suggestion generation

## Architecture

### Core Components

1. **CompanionCube.Service** - Windows background service
2. **CompanionCube.Core** - Shared models and interfaces
3. **CompanionCube.Data** - SQLite database layer
4. **CompanionCube.LlmBridge** - LLM integration layer
5. **CompanionCube.ConfigApp** - WPF configuration UI
6. **CompanionCube.Device** - Physical device communication

### LLM Integration

The system uses a local LLM for:
- Task inference from window titles and app usage
- User state detection (Flow, Working, Needs Nudge, Away)
- ADHD-pattern analysis
- Personalized suggestion generation
- Daily summaries with positive reinforcement

## Setup Instructions

### Prerequisites
- Windows 10/11
- .NET 6.0 or later
- Python 3.8+
- ActivityWatch (recommended) or Windows API monitoring
- Visual Studio 2022 or VS Code
- Arduino IDE (for device firmware)

### Quick Start

1. **Install ActivityWatch** (recommended for best experience):
   ```bash
   # Download from https://activitywatch.net
   # OR use package manager:
   choco install activitywatch
   # OR
   scoop install activitywatch
   ```

2. **Set up ActivityWatch integration**:
   ```bash
   scripts/setup-activitywatch.bat
   ```

3. **Install AI models**:
   ```bash
   scripts/setup-llm.bat
   ```

4. **Build and run**:
   ```bash
   scripts/build.bat
   scripts/run-service.bat
   ```

### Manual Setup

#### Installing the LLM

1. Install Python dependencies:
```bash
cd src/CompanionCube.LlmBridge/Python
pip install -r requirements.txt
```

2. Download an ADHD-optimized model:
```bash
python download_model.py --model phi-2-adhd --output ./models
```

Available models:
- `phi-2-adhd` (1.6GB) - Lightweight, fast inference
- `mistral-7b-adhd` (4.1GB) - Balanced performance
- `llama2-7b-adhd` (3.8GB) - Most comprehensive

#### Activity Monitoring Options

**Option 1: ActivityWatch (Recommended)**
- Comprehensive web browsing tracking
- Cross-platform support
- Rich historical data
- Browser extension integration
- See: [ActivityWatch Integration Guide](docs/ActivityWatch-Integration.md)

**Option 2: Windows API (Basic)**
- Simple window and application tracking
- No additional dependencies
- Windows-only

#### Running the System

1. Start ActivityWatch (if using):
   - ActivityWatch should auto-start after installation
   - Verify at: http://localhost:5600

2. Start the LLM server:
```bash
cd src/CompanionCube.LlmBridge/Python
python llm_server.py --model ./models/phi-2-adhd.gguf --port 5678
```

3. Build and run the Windows service:
```bash
dotnet build
dotnet run --project src/CompanionCube.Service
```

4. Configure settings using the WPF app:
```bash
dotnet run --project src/CompanionCube.ConfigApp
```

## Features

### Adaptive Learning
- Silent observation on Day 1
- Gradual interaction increase
- Learns individual ADHD patterns
- No judgment or pressure

### Companion Modes
- **Study Buddy**: Active encouragement, 15-30 min check-ins
- **Ghost Mode**: Silent logging, minimal interaction
- **Coach Mode**: Suggestions based on "good day" patterns
- **Weekend Mode**: Relaxed monitoring

### User States (Device Colors)
- **Flow Mode** (Green): Deep focus detected
- **Working** (Yellow): Active but interruptible
- **Needs Nudge** (Red): Distraction detected
- **Away** (Off): No activity

### Privacy First
- All data stays local
- No cloud connectivity
- LLM runs entirely on your machine
- Full data control

## Development Roadmap

### Phase 3: Physical Device (Next)
- ESP32 hardware design
- E-ink/OLED display integration
- 3D printed enclosure
- Button interactions

### Phase 4: User Experience
- Notification system
- Daily/weekly summaries
- Good day templates
- Seasonal adaptation

### Phase 5: Intelligence Enhancement
- Fine-tuned ADHD models
- Advanced pattern prediction
- Interruption recovery
- Weekly insights

## Technical Details

### LLM Prompts
The system uses ADHD-focused prompts that:
- Celebrate accomplishments
- Avoid judgment or shame
- Provide optional suggestions
- Understand ADHD patterns

### API Endpoints
- `POST /generate` - General text generation
- `POST /analyze_behavior` - ADHD behavior analysis
- `GET /health` - Service health check

### Database Schema
- `ActivityRecords` - User activity logs
- `GoodDayTemplates` - Successful day patterns
- `UserPreferences` - Configuration settings

## License
MIT License - see LICENSE file for details