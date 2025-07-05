using CompanionCube.Core.Models;

namespace CompanionCube.Core.Services;

public interface ILlmService
{
    Task<string> InferTaskAsync(ActivityRecord activity);
    Task<UserState> InferUserStateAsync(List<ActivityRecord> recentActivities);
    Task<string> GenerateSuggestionAsync(UserState currentState, CompanionMode mode, List<ActivityRecord> context);
    Task<string> GenerateDailySummaryAsync(List<ActivityRecord> dailyActivities);
    Task<List<string>> AnalyzePatternAsync(List<ActivityRecord> activities, string analysisType);
    Task<bool> IsLlmAvailableAsync();
}

public class LlmQuery
{
    public string Prompt { get; set; } = string.Empty;
    public Dictionary<string, object> Context { get; set; } = new();
    public int MaxTokens { get; set; } = 150;
    public float Temperature { get; set; } = 0.7f;
}

public class LlmResponse
{
    public string Text { get; set; } = string.Empty;
    public int TokensUsed { get; set; }
    public TimeSpan ResponseTime { get; set; }
    public bool Success { get; set; }
    public string? Error { get; set; }
}