# LLM Prompts Reference Guide

This document shows exactly where all prompts are stored and how to customize them for the Ring-lite model and ADHD-specific use cases.

## 📍 Prompt Locations

### 1. System Prompt (Main Personality)

**File:** `src/CompanionCube.LlmBridge/Python/llm_server.py`  
**Lines:** 19-27

```python
SYSTEM_PROMPT = """You are Companion Cube, an ADHD productivity assistant. Your core principles:
1. Celebrate what users did, not what they should do
2. No judgment, shame, or pressure
3. All suggestions are optional
4. Understand ADHD patterns: hyperfocus, task switching, time blindness
5. Be encouraging and supportive
6. Keep responses concise and actionable
"""
```

**Ring-lite Optimization:**
```python
SYSTEM_PROMPT = """You are Companion Cube, an ADHD productivity assistant built for understanding and supporting neurodivergent work patterns.

Core principles:
- Celebrate accomplishments, no matter how small
- Never shame or pressure - all suggestions are optional
- Recognize ADHD traits: hyperfocus, task switching, time blindness, executive dysfunction
- Provide gentle, specific, actionable suggestions
- Be encouraging and understanding

Response style:
- Keep responses under 30 words when possible
- Use positive, supportive language
- Focus on what worked well
- Suggest one specific next step if needed
"""
```

### 2. Task Inference Prompts

**File:** `src/CompanionCube.LlmBridge/Services/LocalLlmService.cs`  
**Method:** `BuildTaskInferencePrompt()`  
**Lines:** ~180-190

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

**Enhanced for ActivityWatch Data:**
```csharp
private string BuildTaskInferencePrompt(ActivityRecord activity)
{
    return $@"Analyze this activity for an ADHD user. What task are they working on?

Current Activity:
- App: {activity.ApplicationName}
- Window: {activity.WindowTitle}
- Duration: {activity.DurationSeconds}s

Context: This is part of their focus session. Be specific about the type of work.

Task (one word):";
}
```

### 3. State Detection Prompts

**File:** `src/CompanionCube.LlmBridge/Services/LocalLlmService.cs`  
**Method:** `BuildStateInferencePrompt()`  
**Lines:** ~192-205

```csharp
private string BuildStateInferencePrompt(List<ActivityRecord> recentActivities)
{
    var activities = string.Join("\n", recentActivities.TakeLast(10).Select(a => 
        $"- {a.ApplicationName} ({a.WindowTitle}) for {a.DurationSeconds}s"));

    return $@"You are an ADHD productivity assistant analyzing user behavior.
Based on the recent activities, determine the user's current state.
States: FlowMode (deep focus), WorkingInterruptible (active but available), NeedsNudge (distracted/stuck), Away (no activity)

Recent activities:
{activities}

Current state (one word only):";
}
```

**Enhanced with Web Data:**
```csharp
private string BuildStateInferencePrompt(List<ActivityRecord> recentActivities)
{
    var apps = recentActivities.Select(a => a.ApplicationName).Distinct().Count();
    var totalTime = recentActivities.Sum(a => a.DurationSeconds);
    var focusTime = CalculateFocusTime(recentActivities);
    
    return $@"ADHD behavior analysis - what's the user's current state?

Last 10 minutes:
- {apps} different apps used
- {focusTime/60:F1} min focus time out of {totalTime/60:F1} min total
- Recent: {recentActivities.LastOrDefault()?.ApplicationName} for {recentActivities.LastOrDefault()?.DurationSeconds}s

ADHD context: Look for hyperfocus, task switching, or distraction patterns.

State (FlowMode/WorkingInterruptible/NeedsNudge/Away):";
}
```

### 4. Suggestion Generation Prompts

**File:** `src/CompanionCube.LlmBridge/Services/LocalLlmService.cs`  
**Method:** `BuildSuggestionPrompt()`  
**Lines:** ~207-220

```csharp
private string BuildSuggestionPrompt(UserState state, CompanionMode mode, List<ActivityRecord> context)
{
    var modeDescription = mode switch
    {
        CompanionMode.StudyBuddy => "encouraging and supportive",
        CompanionMode.CoachMode => "based on successful patterns",
        CompanionMode.GhostMode => "minimal and non-intrusive",
        _ => "gentle and understanding"
    };

    return $@"You are an ADHD productivity companion in {mode} mode.
The user is currently in {state} state.
Generate a brief, {modeDescription} suggestion.
Remember: no judgment, no pressure, celebrate what they've done.

Suggestion (max 20 words):";
}
```

**Ring-lite Optimized:**
```csharp
private string BuildSuggestionPrompt(UserState state, CompanionMode mode, List<ActivityRecord> context)
{
    var recentWork = GetRecentAccomplishments(context);
    var timeInState = CalculateTimeInCurrentState(context);
    
    return $@"ADHD-friendly suggestion needed for user in {state} state.

Recent work: {recentWork}
Time in current state: {timeInState} minutes
Mode: {mode}

ADHD considerations:
- Celebrate what they accomplished
- Suggest only if genuinely helpful
- Keep it specific and actionable
- No pressure or shame

Suggestion (15 words max):";
}
```

### 5. Daily Summary Prompts

**File:** `src/CompanionCube.LlmBridge/Services/LocalLlmService.cs`  
**Method:** `BuildDailySummaryPrompt()`  
**Lines:** ~235-245

```csharp
private string BuildDailySummaryPrompt(List<ActivityRecord> activities)
{
    var taskSummary = activities
        .GroupBy(a => a.InferredTask)
        .Select(g => $"{g.Key}: {g.Sum(a => a.DurationSeconds) / 60} minutes")
        .Take(5);

    return $@"You are an ADHD productivity companion generating a daily summary.
Focus on celebrating accomplishments, not what wasn't done.
Be positive and encouraging.

Today's activities:
{string.Join("\n", taskSummary)}

Summary (2-3 sentences):";
}
```

## 🎯 ActivityWatch-Specific Prompts

### Web Browsing Analysis

**Location:** `src/CompanionCube.Service/Services/ActivityWatchClient.cs`  
**Method:** `InferTaskFromWebActivity()`

```csharp
private string BuildWebActivityPrompt(string url, string title, int duration)
{
    return $@"ADHD user spent {duration} seconds on this website:
URL: {url}
Title: {title}

Was this productive or distraction? Consider:
- Research/learning sites = productive
- Social media/entertainment = might be break time
- Documentation/tutorials = very productive

Classification (Productive/Break/Distraction):";
}
```

### Hyperfocus Detection

**New prompt to add:**
```csharp
private string BuildHyperfocusPrompt(List<ActivityRecord> longSession)
{
    var duration = longSession.Sum(a => a.DurationSeconds) / 60;
    var mainTask = longSession.GroupBy(a => a.InferredTask).OrderByDescending(g => g.Sum(a => a.DurationSeconds)).First().Key;
    
    return $@"ADHD hyperfocus session detected:
Duration: {duration} minutes
Main task: {mainTask}
Apps used: {string.Join(", ", longSession.Select(a => a.ApplicationName).Distinct())}

This looks like a hyperfocus session! Consider:
- Celebrate this focused time
- Suggest a break if over 90 minutes
- Note what conditions enabled this focus

Response (encouraging, max 25 words):";
}
```

## 🔧 Customizing for Ring-lite

### Ring-lite Specific Parameters

**File:** `src/CompanionCube.LlmBridge/Services/LocalLlmService.cs`  
**Method:** `QueryLlmAsync()`

```csharp
private async Task<LlmResponse?> QueryLlmAsync(string prompt, int maxTokens = 150, float temperature = 0.7f)
{
    // Ring-lite optimized parameters
    var ringLiteParams = new
    {
        prompt = prompt,
        max_tokens = Math.Min(maxTokens, 100), // Ring-lite works better with shorter responses
        temperature = 0.6f, // Slightly more focused than default
        top_p = 0.9f, // Add nucleus sampling
        repeat_penalty = 1.1f, // Reduce repetition
        stop = new[] { "\n\n", "User:", "Human:" } // Ring-lite specific stop tokens
    };
    
    // Rest of method...
}
```

### ADHD-Specific Prompt Templates

**Add to:** `src/CompanionCube.LlmBridge/Services/ADHDPromptTemplates.cs` (new file)

```csharp
public static class ADHDPromptTemplates
{
    public const string HYPERFOCUS_CELEBRATION = @"
🎯 Amazing focus session! You spent {duration} minutes on {task}.
This is exactly the kind of deep work that's hard with ADHD - celebrate this win!
{suggestion}";

    public const string TASK_SWITCHING_SUPPORT = @"
I notice you've switched between {appCount} apps in {timespan} minutes.
That's totally normal with ADHD! Your brain is actively working.
{suggestion}";

    public const string GENTLE_NUDGE = @"
You've been on {site} for {duration} minutes.
No judgment - sometimes we need these breaks!
{suggestion}";

    public const string TRANSITION_HELP = @"
Great work on {completedTask}! 
Ready to move to something new? Here's a gentle transition:
{suggestion}";
}
```

## 🧪 Testing Prompts

### Test Script Location

**File:** `scripts/test-prompts.bat`

```batch
@echo off
echo Testing Ring-lite prompts with real ActivityWatch data...

curl -X POST http://localhost:5678/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"User spent 45 minutes switching between VS Code (React components) and Stack Overflow (React hooks questions). ADHD analysis:\", \"max_tokens\": 50}"

echo.
echo Testing state detection...
curl -X POST http://localhost:5678/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\": \"Recent ADHD user activity: chrome(stackoverflow) 5min, code(App.js) 15min, chrome(youtube) 3min, code(App.js) 20min. Current state:\", \"max_tokens\": 10}"
```

## 🎮 Real-World Prompt Examples

With ActivityWatch data, your prompts will include rich context:

**Before (Windows API only):**
```
Application: chrome
Window: New Tab - Google Chrome
Duration: 300 seconds
```

**After (ActivityWatch integration):**
```
Application: chrome
URL: https://stackoverflow.com/questions/54269635/how-to-use-react-hooks
Title: How to use React hooks for state management
Duration: 300 seconds
Previous activity: VS Code editing UserDashboard.jsx for 15 minutes
ADHD context: Research session during active coding - likely productive learning
```

This rich context allows Ring-lite to provide much more relevant and supportive ADHD-focused suggestions!

## 📝 Quick Customization Checklist

- [ ] Update system prompt for Ring-lite personality
- [ ] Adjust max_tokens to 50-100 for concise responses  
- [ ] Set temperature to 0.6 for more focused responses
- [ ] Add ActivityWatch context to all prompts
- [ ] Include ADHD-specific considerations
- [ ] Test with real browsing and coding data
- [ ] Monitor for helpful vs overwhelming suggestions
- [ ] Adjust based on actual usage patterns

The prompts are designed to be easily customizable - just edit the methods in `LocalLlmService.cs` and restart the service!