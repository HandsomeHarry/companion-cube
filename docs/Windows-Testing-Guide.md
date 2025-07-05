# Windows Testing Setup Guide

## Phase 1: Transfer Files to Windows

### Method 1: Shared Folder (Recommended)
1. **In VMware:**
   - VM → Settings → Options → Shared Folders
   - Enable shared folders
   - Add folder: `C:\CompanionCube` (on Windows) ↔ `/mnt/hgfs/CompanionCube` (on Ubuntu)

2. **Copy project:**
   ```bash
   # On Ubuntu VM
   cp -r /home/harry/Desktop/adhd-thing/CompanionCube /mnt/hgfs/CompanionCube
   ```

### Method 2: ZIP Transfer
```bash
# On Ubuntu VM
cd /home/harry/Desktop/adhd-thing
zip -r CompanionCube.zip CompanionCube/
# Copy zip to Windows via shared folder or network
```

### Method 3: Git Repository
```bash
# On Ubuntu VM
cd /home/harry/Desktop/adhd-thing/CompanionCube
git init
git add .
git commit -m "Initial Companion Cube implementation"
# Push to GitHub/GitLab, then clone on Windows
```

## Phase 2: Windows Prerequisites

### 1. Install .NET 6 SDK
- Download from: https://dotnet.microsoft.com/download/dotnet/6.0
- Install "SDK" version (not just runtime)
- Verify: `dotnet --version` in Command Prompt

### 2. Install Python 3.8+
- Download from: https://python.org
- ⚠️ **IMPORTANT**: Check "Add Python to PATH" during installation
- Verify: `python --version` in Command Prompt

### 3. Install ActivityWatch
**Option A - Direct Download:**
- Go to: https://activitywatch.net
- Download Windows installer
- Run installer and start ActivityWatch

**Option B - Package Manager:**
```powershell
# Using Chocolatey (if installed)
choco install activitywatch

# Using Scoop (if installed)
scoop bucket add extras
scoop install activitywatch
```

### 4. Install Git (if using Method 3)
- Download from: https://git-scm.com/download/win

## Phase 3: Setup ActivityWatch

### 1. Start ActivityWatch
- Find "ActivityWatch" in Start Menu
- Launch it (should appear in system tray)
- Verify it's running: Open browser to http://localhost:5600

### 2. Install Browser Extensions (Recommended)
**Chrome/Edge:**
1. Open Chrome Web Store
2. Search "ActivityWatch Web Watcher"
3. Install extension
4. Grant permissions to all websites

**Firefox:**
1. Open Firefox Add-ons
2. Search "ActivityWatch Web Watcher"  
3. Install extension

### 3. Generate Some Test Data
- Browse different websites for a few minutes
- Switch between applications
- Let ActivityWatch collect data for 10-15 minutes
- Verify data at: http://localhost:5600

## Phase 4: Setup LLM (Ring-lite Model)

### 1. Navigate to Project
```cmd
cd C:\CompanionCube
```

### 2. Install Python Dependencies
```cmd
cd src\CompanionCube.LlmBridge\Python
pip install -r requirements.txt
```

### 3. Download Ring-lite Model
**Manual Download:**
1. Go to: https://huggingface.co/microsoft/Phi-3.5-mini-instruct-GGUF
2. Download: `Phi-3.5-mini-instruct-q4.gguf` (or similar 4-bit quantized version)
3. Create folder: `src\CompanionCube.LlmBridge\Python\models\`
4. Place file as: `models\ring-lite.gguf`

**OR Use Download Script (Modified):**
```cmd
cd src\CompanionCube.LlmBridge\Python
python download_model.py --model phi-2-adhd --output .\models
```

### 4. Test LLM Server
```cmd
cd src\CompanionCube.LlmBridge\Python
python llm_server.py --model .\models\ring-lite.gguf --port 5678
```

Should see: "Starting server on 127.0.0.1:5678"

## Phase 5: Build and Configure Companion Cube

### 1. Build the Solution
```cmd
cd C:\CompanionCube
dotnet restore
dotnet build --configuration Release
```

### 2. Update Configuration for Ring-lite
Edit `src\CompanionCube.Service\appsettings.json`:
```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information"
    }
  },
  "ConnectionStrings": {
    "DefaultConnection": "Data Source=companionCube.db"
  },
  "ActivityWatch": {
    "UseActivityWatch": true,
    "ServerUrl": "http://localhost:5600",
    "PollingIntervalSeconds": 30,
    "MinimumEventDuration": 5
  },
  "LlmModelPath": "src\\CompanionCube.LlmBridge\\Python\\models\\ring-lite.gguf",
  "EnableDevice": false
}
```

### 3. Test Configuration App
```cmd
cd src\CompanionCube.ConfigApp
dotnet run
```

- Select "ActivityWatch (Recommended)"
- Set ActivityWatch Server: `http://localhost:5600`
- Click "Test ActivityWatch Connection"
- Should show: "✅ ActivityWatch connection successful!"

## Phase 6: Run the Complete System

### 1. Start LLM Server (Terminal 1)
```cmd
cd C:\CompanionCube\src\CompanionCube.LlmBridge\Python
python llm_server.py --model .\models\ring-lite.gguf --port 5678
```

### 2. Start Companion Cube Service (Terminal 2)
```cmd
cd C:\CompanionCube\src\CompanionCube.Service
dotnet run --configuration Release
```

### 3. Watch the Logs
You should see:
```
info: CompanionCube.Service.Services.ActivityWatchMonitor[0]
      Starting ActivityWatch monitoring...
info: CompanionCube.Service.Services.ActivityWatchMonitor[0]
      Connected to ActivityWatch server successfully
info: CompanionCube.Service.Services.ActivityWatchClient[0]
      ActivityWatch buckets - Window: aw-watcher-window_YOURPC, AFK: aw-watcher-afk_YOURPC, Web: aw-watcher-web-chrome_YOURPC
```

## Phase 7: Test with Real Data

### 1. Generate Activity
- Browse some websites (GitHub, Stack Overflow, YouTube)
- Switch between VS Code and browser
- Wait 2-3 minutes for data to be collected

### 2. Check ActivityWatch Data
- Visit: http://localhost:5600
- Should see activity timeline with your recent activity

### 3. Verify Companion Cube Integration
Look for logs like:
```
info: CompanionCube.Service.Services.ActivityWatchMonitor[0]
      Polled 15 activities from ActivityWatch
dbug: CompanionCube.Service.Services.ActivityWatchMonitor[0]
      Activity: chrome - Stack Overflow - How to use async/await (45s) - State: FlowMode
info: CompanionCube.Service.Services.CompanionCubeService[0]
      User state changed to: FlowMode
```

## LLM Prompts Location and Customization

### Where Prompts Are Stored

**1. System Prompt (Main personality):**
```
File: src/CompanionCube.LlmBridge/Python/llm_server.py
Lines: 19-26
```

**2. Task Inference Prompts:**
```
File: src/CompanionCube.LlmBridge/Services/LocalLlmService.cs
Method: BuildTaskInferencePrompt() - Lines ~180-190
```

**3. State Detection Prompts:**
```
File: src/CompanionCube.LlmBridge/Services/LocalLlmService.cs  
Method: BuildStateInferencePrompt() - Lines ~192-205
```

**4. Suggestion Generation Prompts:**
```
File: src/CompanionCube.LlmBridge/Services/LocalLlmService.cs
Method: BuildSuggestionPrompt() - Lines ~207-220
```

### Example Prompt with ActivityWatch Data

**Current Task Inference Prompt:**
```csharp
private string BuildTaskInferencePrompt(ActivityRecord activity)
{
    return $@"You are an ADHD productivity assistant analyzing user activity.
Based on the following activity, infer what task the user is working on.
Be concise and specific.

Application: {activity.ApplicationName}
Window Title: {activity.WindowTitle}
Duration: {activity.DurationSeconds} seconds

Inferred task:";
}
```

**Enhanced with ActivityWatch Data:**
```csharp
private string BuildTaskInferencePrompt(ActivityRecord activity, List<ActivityWatchEvent> recentEvents)
{
    var webContext = GetRecentWebActivity(recentEvents);
    var appSwitches = CountRecentAppSwitches(recentEvents);
    
    return $@"You are an ADHD productivity assistant analyzing user activity.
Based on the following activity and recent context, infer what task the user is working on.

Current Activity:
- Application: {activity.ApplicationName}
- Window Title: {activity.WindowTitle}
- Duration: {activity.DurationSeconds} seconds

Recent Context (last 10 minutes):
- Web sites visited: {webContext}
- App switches: {appSwitches}
- Total focus time: {CalculateFocusTime(recentEvents)} minutes

ADHD-friendly task inference (be encouraging and specific):";
}
```

## Troubleshooting Common Issues

### "ActivityWatch not detected"
1. Verify ActivityWatch is running: http://localhost:5600
2. Check Windows Firewall isn't blocking port 5600
3. Restart ActivityWatch from Start Menu

### "Model not found" 
1. Verify file path: `src\CompanionCube.LlmBridge\Python\models\ring-lite.gguf`
2. Check file size (should be several GB)
3. Try absolute path in appsettings.json

### "Build failed"
1. Ensure .NET 6 SDK is installed (not just runtime)
2. Run `dotnet --list-sdks` to verify
3. Try `dotnet clean` then `dotnet build`

### "No activity data"
1. Check ActivityWatch has browser extensions installed
2. Verify you've used the computer for a few minutes
3. Check ActivityWatch web interface shows data

### Performance Issues
1. Reduce polling frequency to 60 seconds
2. Use smaller LLM model
3. Increase minimum event duration to 10 seconds

## Testing Checklist

- [ ] ActivityWatch installed and running
- [ ] Browser extensions installed  
- [ ] Ring-lite model downloaded and accessible
- [ ] Companion Cube builds without errors
- [ ] Configuration app can connect to ActivityWatch
- [ ] LLM server starts successfully
- [ ] Companion Cube service starts and logs activity
- [ ] AI generates task inferences from real data
- [ ] Web browsing data appears in logs
- [ ] State changes are detected and logged

## Next Steps for Development

1. **Test with various activities** - coding, researching, social media
2. **Monitor LLM prompt effectiveness** - adjust prompts in the source files
3. **Customize for Ring-lite model** - may need different temperature/parameters
4. **Add logging** to see exact prompts being sent to LLM
5. **Test ADHD-specific scenarios** - task switching, hyperfocus detection

The system should now be running on Windows with real ActivityWatch data and the Ring-lite model providing ADHD-focused productivity insights!