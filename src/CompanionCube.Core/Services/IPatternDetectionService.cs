using CompanionCube.Core.Models;

namespace CompanionCube.Core.Services;

public interface IPatternDetectionService
{
    Task<UserState> AnalyzeCurrentStateAsync(List<ActivityRecord> recentActivities);
    Task<bool> IsUserStuckAsync(List<ActivityRecord> recentActivities);
    Task<List<string>> GetSuggestionsAsync(List<ActivityRecord> recentActivities, CompanionMode mode);
    Task<GoodDayTemplate> CreateGoodDayTemplateAsync(List<ActivityRecord> dayActivities, int userRating);
    Task<List<string>> GetCoachingSuggestionsAsync(List<GoodDayTemplate> templates);
}