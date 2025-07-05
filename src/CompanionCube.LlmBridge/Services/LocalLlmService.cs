using System.Diagnostics;
using System.Text;
using CompanionCube.Core.Models;
using CompanionCube.Core.Services;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;

namespace CompanionCube.LlmBridge.Services;

public class LocalLlmService : ILlmService
{
    private readonly ILogger<LocalLlmService> _logger;
    private readonly string _pythonScriptPath;
    private readonly string _modelPath;
    private readonly int _port;
    private Process? _llmProcess;

    public LocalLlmService(ILogger<LocalLlmService> logger, string modelPath)
    {
        _logger = logger;
        _modelPath = modelPath;
        _pythonScriptPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Python", "llm_server.py");
        _port = 5678;
    }

    public async Task<string> InferTaskAsync(ActivityRecord activity)
    {
        var prompt = BuildTaskInferencePrompt(activity);
        var response = await QueryLlmAsync(prompt);
        return response?.Text ?? "Unknown";
    }

    public async Task<UserState> InferUserStateAsync(List<ActivityRecord> recentActivities)
    {
        if (!recentActivities.Any())
            return UserState.Away;

        var prompt = BuildStateInferencePrompt(recentActivities);
        var response = await QueryLlmAsync(prompt);
        
        if (response?.Success == true)
        {
            return ParseUserState(response.Text);
        }

        return UserState.WorkingInterruptible;
    }

    public async Task<string> GenerateSuggestionAsync(UserState currentState, CompanionMode mode, List<ActivityRecord> context)
    {
        var prompt = BuildSuggestionPrompt(currentState, mode, context);
        var response = await QueryLlmAsync(prompt, maxTokens: 100);
        return response?.Text ?? GetFallbackSuggestion(currentState, mode);
    }

    public async Task<string> GenerateDailySummaryAsync(List<ActivityRecord> dailyActivities)
    {
        var prompt = BuildDailySummaryPrompt(dailyActivities);
        var response = await QueryLlmAsync(prompt, maxTokens: 300);
        return response?.Text ?? "Today was productive!";
    }

    public async Task<List<string>> AnalyzePatternAsync(List<ActivityRecord> activities, string analysisType)
    {
        var prompt = BuildPatternAnalysisPrompt(activities, analysisType);
        var response = await QueryLlmAsync(prompt, maxTokens: 200);
        
        if (response?.Success == true)
        {
            return response.Text.Split('\n', StringSplitOptions.RemoveEmptyEntries).ToList();
        }

        return new List<string>();
    }

    public async Task<bool> IsLlmAvailableAsync()
    {
        try
        {
            var testPrompt = "Test connection";
            var response = await QueryLlmAsync(testPrompt, maxTokens: 10);
            return response?.Success == true;
        }
        catch
        {
            return false;
        }
    }

    private async Task<LlmResponse?> QueryLlmAsync(string prompt, int maxTokens = 150, float temperature = 0.7f)
    {
        try
        {
            await EnsureLlmServiceRunning();

            using var client = new HttpClient();
            client.Timeout = TimeSpan.FromSeconds(30);

            var request = new
            {
                prompt = prompt,
                max_tokens = maxTokens,
                temperature = temperature
            };

            var json = JsonConvert.SerializeObject(request);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await client.PostAsync($"http://localhost:{_port}/generate", content);
            
            if (response.IsSuccessStatusCode)
            {
                var responseJson = await response.Content.ReadAsStringAsync();
                return JsonConvert.DeserializeObject<LlmResponse>(responseJson);
            }

            _logger.LogError("LLM query failed with status: {StatusCode}", response.StatusCode);
            return null;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error querying LLM");
            return null;
        }
    }

    private async Task EnsureLlmServiceRunning()
    {
        if (_llmProcess == null || _llmProcess.HasExited)
        {
            await StartLlmService();
        }
    }

    private async Task StartLlmService()
    {
        try
        {
            _logger.LogInformation("Starting LLM service...");

            var startInfo = new ProcessStartInfo
            {
                FileName = "python",
                Arguments = $"\"{_pythonScriptPath}\" --model \"{_modelPath}\" --port {_port}",
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            };

            _llmProcess = Process.Start(startInfo);
            
            if (_llmProcess == null)
            {
                throw new Exception("Failed to start LLM process");
            }

            // Wait for service to be ready
            await Task.Delay(5000);
            
            _logger.LogInformation("LLM service started on port {Port}", _port);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to start LLM service");
            throw;
        }
    }

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

    private string BuildPatternAnalysisPrompt(List<ActivityRecord> activities, string analysisType)
    {
        return $@"You are an ADHD behavior pattern analyzer.
Analyze the following activities for {analysisType} patterns.
Provide 3-5 brief insights that could help the user.

Activities: {activities.Count} total over {(activities.Last().Timestamp - activities.First().Timestamp).TotalHours:F1} hours

Key insights:";
    }

    private UserState ParseUserState(string text)
    {
        var normalized = text.Trim().ToLower();
        
        return normalized switch
        {
            "flowmode" or "flow" => UserState.FlowMode,
            "workinginterruptible" or "working" => UserState.WorkingInterruptible,
            "needsnudge" or "nudge" or "distracted" => UserState.NeedsNudge,
            "away" => UserState.Away,
            _ => UserState.WorkingInterruptible
        };
    }

    private string GetFallbackSuggestion(UserState state, CompanionMode mode)
    {
        return (state, mode) switch
        {
            (UserState.FlowMode, _) => "Great focus! Keep it up!",
            (UserState.NeedsNudge, CompanionMode.StudyBuddy) => "Need a quick break? That's okay!",
            (UserState.NeedsNudge, CompanionMode.CoachMode) => "Time for your focus technique?",
            _ => "You're doing great!"
        };
    }

    public void Dispose()
    {
        _llmProcess?.Kill();
        _llmProcess?.Dispose();
    }
}