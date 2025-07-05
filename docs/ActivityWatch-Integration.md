# ActivityWatch Integration Guide

Companion Cube now integrates with ActivityWatch to provide comprehensive activity monitoring including web browsing, application usage, and detailed user behavior tracking.

## What is ActivityWatch?

ActivityWatch is an open-source automated time tracker that runs locally on your machine. It collects data about:
- **Window activity**: Applications and window titles
- **Web browsing**: URLs, page titles, time spent on websites
- **AFK detection**: When you're away from your computer
- **Editor activity**: Code editing sessions (with extensions)
- **Media consumption**: Music, videos, and other media

## Benefits Over Built-in Monitoring

| Feature | Built-in Windows API | ActivityWatch Integration |
|---------|---------------------|---------------------------|
| Application tracking | ✅ Basic | ✅ Advanced |
| Window titles | ✅ | ✅ |
| Web browsing details | ❌ | ✅ URLs, domains, time |
| AFK detection | ❌ | ✅ Accurate idle time |
| Historical data | ❌ | ✅ Long-term storage |
| Browser extensions | ❌ | ✅ Chrome, Firefox, Edge |
| Editor integration | ❌ | ✅ VS Code, IntelliJ, etc. |
| Cross-platform | ❌ Windows only | ✅ Windows, Mac, Linux |

## Installation and Setup

### 1. Install ActivityWatch

Download and install ActivityWatch from [activitywatch.net](https://activitywatch.net)

**Windows:**
```bash
# Download from GitHub releases
# https://github.com/ActivityWatch/activitywatch/releases
# Install the .exe file
```

**Alternative: Using Package Manager**
```bash
# Using Chocolatey
choco install activitywatch

# Using Scoop
scoop bucket add extras
scoop install activitywatch
```

### 2. Start ActivityWatch

After installation, ActivityWatch will start automatically. You can also:
- Run from Start Menu: "ActivityWatch"
- Check system tray for the ActivityWatch icon
- Verify it's running by visiting: http://localhost:5600

### 3. Install Browser Extensions (Recommended)

For comprehensive web tracking, install the ActivityWatch browser extension:

**Chrome/Edge:**
1. Go to Chrome Web Store
2. Search "ActivityWatch Web Watcher"
3. Click "Add to Chrome"

**Firefox:**
1. Go to Firefox Add-ons
2. Search "ActivityWatch Web Watcher"
3. Click "Add to Firefox"

### 4. Configure Companion Cube

1. Run the Companion Cube configuration app:
   ```bash
   scripts/run-config.bat
   ```

2. In the "Activity Monitoring" section:
   - Select "ActivityWatch (Recommended)"
   - Verify server URL: `http://localhost:5600`
   - Set polling interval: 30 seconds (recommended)
   - Click "Test ActivityWatch Connection"

3. Save settings and restart Companion Cube service

## Configuration Options

### appsettings.json Configuration

```json
{
  "ActivityWatch": {
    "UseActivityWatch": true,
    "ServerUrl": "http://localhost:5600",
    "PollingIntervalSeconds": 30,
    "MinimumEventDuration": 5
  }
}
```

### Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `UseActivityWatch` | `true` | Enable ActivityWatch integration |
| `ServerUrl` | `http://localhost:5600` | ActivityWatch server URL |
| `PollingIntervalSeconds` | `30` | How often to fetch new data |
| `MinimumEventDuration` | `5` | Ignore events shorter than X seconds |

## Data Types and Buckets

ActivityWatch organizes data into "buckets" by type and device:

### Window Activity Bucket
```
aw-watcher-window_{hostname}
```
**Data includes:**
- Application name (e.g., "chrome", "code", "notepad")
- Window title
- Duration of focus

### AFK Status Bucket
```
aw-watcher-afk_{hostname}
```
**Data includes:**
- Status: "not-afk" or "afk"
- Idle detection based on mouse/keyboard activity

### Web Activity Bucket
```
aw-watcher-web-chrome_{hostname}
aw-watcher-web-firefox_{hostname}
```
**Data includes:**
- Full URL
- Page title
- Incognito/private mode status
- Audio playing status

## How Companion Cube Uses the Data

### 1. Enhanced Task Inference

**Before (Windows API only):**
- Application: "chrome"
- Window: "New Tab - Google Chrome"
- Inferred Task: "Web Browsing"

**After (ActivityWatch integration):**
- Application: "chrome"
- URL: "https://stackoverflow.com/questions/..."
- Page Title: "How to implement async/await in C#"
- Inferred Task: "Research/Learning"

### 2. Better State Detection

Companion Cube can now detect:
- **Flow State**: Extended coding sessions in VS Code with minimal browser switching
- **Research Mode**: Deep diving into documentation and Stack Overflow
- **Distraction**: Excessive time on social media or entertainment sites
- **Away**: Accurately detected idle time from ActivityWatch

### 3. Web-Based Pattern Analysis

- **Focus websites**: GitHub, documentation sites, Stack Overflow
- **Distraction websites**: Social media, YouTube, Reddit
- **Productivity websites**: Email, project management tools
- **Learning websites**: Online courses, tutorials

### 4. Enhanced ADHD Insights

The AI can now provide more nuanced suggestions:
- "I notice you've been researching React hooks for 45 minutes. Great focus! Would you like to take a break?"
- "You've switched between YouTube and your code editor 8 times in the last hour. Let's try the Pomodoro technique?"
- "Your most productive coding sessions happen after you spend 10-15 minutes reading documentation first."

## Troubleshooting

### ActivityWatch Not Detected

1. **Check if ActivityWatch is running:**
   ```bash
   # Visit in browser
   http://localhost:5600
   ```

2. **Restart ActivityWatch:**
   - Close from system tray
   - Restart from Start Menu

3. **Check port conflicts:**
   - Default port is 5600
   - Change in ActivityWatch config if needed

### No Web Data

1. **Install browser extensions:**
   - ActivityWatch Web Watcher for Chrome/Edge
   - ActivityWatch Web Watcher for Firefox

2. **Check extension permissions:**
   - Allow access to all websites
   - Enable in incognito mode (optional)

### Missing Data Types

1. **Check available buckets:**
   ```bash
   # In Companion Cube, this will log available buckets:
   GET http://localhost:5600/api/0/buckets/
   ```

2. **Common bucket names:**
   - `aw-watcher-window_{hostname}`
   - `aw-watcher-afk_{hostname}`
   - `aw-watcher-web-chrome_{hostname}`

### Performance Issues

1. **Reduce polling frequency:**
   - Increase `PollingIntervalSeconds` to 60 or 120

2. **Limit data range:**
   - Only fetch last few hours of data
   - Increase `MinimumEventDuration` to filter noise

## Privacy and Data

### Local Data Only
- All ActivityWatch data stays on your machine
- No cloud synchronization unless you configure it
- Companion Cube only reads data, never modifies it

### Data Location
**Windows:**
```
%APPDATA%\activitywatch\aw-server\databases\
```

**What's Stored:**
- Application usage patterns
- Website visit history
- Window focus duration
- Idle/active time

### Data Control
- View data in ActivityWatch web interface: http://localhost:5600
- Export data from ActivityWatch
- Delete specific data ranges
- Configure watchers to exclude sensitive applications

## Advanced Usage

### Custom Queries

Companion Cube supports custom ActivityWatch queries for advanced analysis:

```csharp
// Example: Get top applications for today
var query = @"
    events = query_bucket(""aw-watcher-window_"" + hostname);
    events = filter_period_intersect(events, filter_timeperiods);
    events = categorize(events, [[""Work"", {""app"": [""code"", ""devenv""]}]]);
    duration = sum_by_key(events, ""category"");
    RETURN = duration;
";

var result = await activityWatchClient.QueryAsync(query);
```

### Integration with Other Watchers

ActivityWatch supports many community watchers:
- **aw-watcher-spotify**: Music listening habits
- **aw-watcher-input**: Keystroke and mouse patterns
- **aw-watcher-steam**: Gaming activity
- **aw-watcher-vim**: Detailed coding statistics

These can enhance Companion Cube's understanding of your work patterns.

## Comparison: Windows API vs ActivityWatch

### When to Use Windows API
- Simple setup requirements
- Privacy concerns about detailed web tracking
- Minimal system resource usage
- Basic application monitoring sufficient

### When to Use ActivityWatch (Recommended)
- Comprehensive activity tracking needed
- Web browsing is significant part of workflow
- Want detailed historical analysis
- Using multiple applications/browsers
- Interested in long-term productivity insights
- Already using ActivityWatch for other purposes

## Getting Started Checklist

- [ ] Install ActivityWatch from official website
- [ ] Start ActivityWatch service
- [ ] Install browser extensions for web tracking
- [ ] Test ActivityWatch web interface (http://localhost:5600)
- [ ] Configure Companion Cube to use ActivityWatch
- [ ] Test connection in Companion Cube config app
- [ ] Run Companion Cube service
- [ ] Verify activity data is being imported
- [ ] Check logs for any integration issues

## Support

If you encounter issues with the ActivityWatch integration:

1. **Check ActivityWatch documentation**: https://docs.activitywatch.net
2. **Verify ActivityWatch is working independently**
3. **Check Companion Cube logs for connection errors**
4. **Test the API endpoint manually**: http://localhost:5600/api/0/info
5. **Report integration-specific issues to Companion Cube project**

The ActivityWatch integration makes Companion Cube significantly more powerful for ADHD productivity support by providing rich, contextual data about your actual work patterns and digital behavior.