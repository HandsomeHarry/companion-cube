using CompanionCube.Core.Models;
using CompanionCube.Core.Services;
using System.Text.Json;

namespace CompanionCube.Service.Services;

public class PatternDetectionService : IPatternDetectionService
{
    private readonly ILogger<PatternDetectionService> _logger;

    public PatternDetectionService(ILogger<PatternDetectionService> logger)
    {
        _logger = logger;
    }

    public async Task<UserState> AnalyzeCurrentStateAsync(List<ActivityRecord> recentActivities)
    {
        if (!recentActivities.Any())
            return UserState.Away;

        var lastActivity = recentActivities.OrderByDescending(a => a.Timestamp).First();
        var timeSinceLastActivity = DateTime.Now - lastActivity.Timestamp;

        if (timeSinceLastActivity.TotalMinutes > 10)
            return UserState.Away;

        var focusApps = new[] { "code", "devenv", "notepad", "sublime", "atom", "vim" };
        var distractionApps = new[] { "chrome", "firefox", "edge", "steam", "discord" };

        var recentFocusTime = CalculateFocusTime(recentActivities, focusApps);
        var recentDistractionTime = CalculateDistractionTime(recentActivities, distractionApps);

        if (recentFocusTime > TimeSpan.FromMinutes(20) && recentDistractionTime < TimeSpan.FromMinutes(5))
            return UserState.FlowMode;

        if (recentDistractionTime > TimeSpan.FromMinutes(15))
            return UserState.NeedsNudge;

        return UserState.WorkingInterruptible;
    }

    public async Task<bool> IsUserStuckAsync(List<ActivityRecord> recentActivities)
    {
        if (recentActivities.Count < 3)
            return false;

        var last30Minutes = recentActivities
            .Where(a => a.Timestamp > DateTime.Now.AddMinutes(-30))
            .ToList();

        var appSwitchCount = CountAppSwitches(last30Minutes);
        var averageTaskDuration = CalculateAverageTaskDuration(last30Minutes);

        return appSwitchCount > 10 || averageTaskDuration < TimeSpan.FromMinutes(2);
    }

    public async Task<List<string>> GetSuggestionsAsync(List<ActivityRecord> recentActivities, CompanionMode mode)
    {
        var suggestions = new List<string>();

        if (await IsUserStuckAsync(recentActivities))
        {
            suggestions.AddRange(GetStuckSuggestions(mode));
        }

        var currentState = await AnalyzeCurrentStateAsync(recentActivities);
        suggestions.AddRange(GetStateSuggestions(currentState, mode));

        return suggestions;
    }

    public async Task<GoodDayTemplate> CreateGoodDayTemplateAsync(List<ActivityRecord> dayActivities, int userRating)
    {
        var template = new GoodDayTemplate
        {
            Date = DateTime.Today,
            UserRating = userRating,
            Activities = dayActivities
        };

        template.ActivityPattern = JsonSerializer.Serialize(
            dayActivities.GroupBy(a => a.InferredTask)
                .Select(g => new { Task = g.Key, Duration = g.Sum(a => a.DurationSeconds) })
                .OrderByDescending(x => x.Duration)
                .ToList()
        );

        template.TimingPattern = JsonSerializer.Serialize(
            dayActivities.GroupBy(a => a.Timestamp.Hour)
                .Select(g => new { Hour = g.Key, Activities = g.Count() })
                .OrderBy(x => x.Hour)
                .ToList()
        );

        template.TransitionPattern = JsonSerializer.Serialize(
            AnalyzeTransitions(dayActivities)
        );

        return template;
    }

    public async Task<List<string>> GetCoachingSuggestionsAsync(List<GoodDayTemplate> templates)
    {
        var suggestions = new List<string>();

        if (!templates.Any())
            return suggestions;

        var bestTemplate = templates.OrderByDescending(t => t.UserRating).First();
        var bestPatterns = JsonSerializer.Deserialize<List<dynamic>>(bestTemplate.ActivityPattern);

        suggestions.Add($"Your best days usually involve focusing on {bestPatterns?.FirstOrDefault()?.Task}");
        suggestions.Add($"Consider starting your day at {GetOptimalStartTime(bestTemplate)}");

        return suggestions;
    }

    private TimeSpan CalculateFocusTime(List<ActivityRecord> activities, string[] focusApps)
    {
        return TimeSpan.FromSeconds(
            activities.Where(a => focusApps.Contains(a.ApplicationName.ToLower()))
                     .Sum(a => a.DurationSeconds)
        );
    }

    private TimeSpan CalculateDistractionTime(List<ActivityRecord> activities, string[] distractionApps)
    {
        return TimeSpan.FromSeconds(
            activities.Where(a => distractionApps.Contains(a.ApplicationName.ToLower()) &&
                                 (a.WindowTitle.Contains("YouTube") || a.WindowTitle.Contains("Reddit")))
                     .Sum(a => a.DurationSeconds)
        );
    }

    private int CountAppSwitches(List<ActivityRecord> activities)
    {
        var switches = 0;
        var lastApp = string.Empty;

        foreach (var activity in activities.OrderBy(a => a.Timestamp))
        {
            if (activity.ApplicationName != lastApp)
            {
                switches++;
                lastApp = activity.ApplicationName;
            }
        }

        return switches;
    }

    private TimeSpan CalculateAverageTaskDuration(List<ActivityRecord> activities)
    {
        if (!activities.Any())
            return TimeSpan.Zero;

        return TimeSpan.FromSeconds(activities.Average(a => a.DurationSeconds));
    }

    private List<string> GetStuckSuggestions(CompanionMode mode)
    {
        return mode switch
        {
            CompanionMode.StudyBuddy => new List<string>
            {
                "You seem to be jumping between tasks. Would you like to take a 5-minute break?",
                "Let's focus on one thing at a time. What's the most important task right now?"
            },
            CompanionMode.CoachMode => new List<string>
            {
                "Based on your good days, you usually focus better after a short walk.",
                "Your pattern shows you work best with 25-minute focused sessions."
            },
            _ => new List<string>
            {
                "Consider taking a brief pause to reset your focus."
            }
        };
    }

    private List<string> GetStateSuggestions(UserState state, CompanionMode mode)
    {
        return state switch
        {
            UserState.FlowMode => new List<string> { "Great flow! I'll keep quiet and let you work." },
            UserState.NeedsNudge => new List<string> { "Noticed you've been browsing. Ready to get back to work?" },
            UserState.WorkingInterruptible => new List<string> { "You're doing great! Keep it up." },
            _ => new List<string>()
        };
    }

    private List<object> AnalyzeTransitions(List<ActivityRecord> activities)
    {
        var transitions = new List<object>();
        var orderedActivities = activities.OrderBy(a => a.Timestamp).ToList();

        for (int i = 0; i < orderedActivities.Count - 1; i++)
        {
            var current = orderedActivities[i];
            var next = orderedActivities[i + 1];

            transitions.Add(new
            {
                From = current.InferredTask,
                To = next.InferredTask,
                Duration = (next.Timestamp - current.Timestamp).TotalMinutes
            });
        }

        return transitions;
    }

    private string GetOptimalStartTime(GoodDayTemplate template)
    {
        var timingPattern = JsonSerializer.Deserialize<List<dynamic>>(template.TimingPattern);
        var mostActiveHour = timingPattern?.OrderByDescending(x => x.Activities).FirstOrDefault()?.Hour ?? 9;
        return $"{mostActiveHour}:00";
    }
}