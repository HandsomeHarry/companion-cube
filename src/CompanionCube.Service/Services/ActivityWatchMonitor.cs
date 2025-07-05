using CompanionCube.Core.Models;
using CompanionCube.Core.Services;

namespace CompanionCube.Service.Services;

public class ActivityWatchMonitor : IActivityMonitor
{
    private readonly IActivityWatchClient _activityWatchClient;
    private readonly ILogger<ActivityWatchMonitor> _logger;
    private System.Threading.Timer? _pollingTimer;
    private DateTime _lastPollTime = DateTime.Now.AddMinutes(-5);
    private List<ActivityRecord> _lastKnownActivities = new();
    private UserState _currentState = UserState.Away;

    public event EventHandler<ActivityRecord>? ActivityRecorded;
    public event EventHandler<UserState>? UserStateChanged;

    public ActivityWatchMonitor(IActivityWatchClient activityWatchClient, ILogger<ActivityWatchMonitor> logger)
    {
        _activityWatchClient = activityWatchClient;
        _logger = logger;
    }

    public async Task StartMonitoringAsync(CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Starting ActivityWatch monitoring...");
        
        // Check if ActivityWatch is available
        if (!await _activityWatchClient.IsConnectedAsync())
        {
            _logger.LogError("ActivityWatch server is not available. Please ensure ActivityWatch is running.");
            throw new InvalidOperationException("ActivityWatch server is not available");
        }

        _logger.LogInformation("Connected to ActivityWatch server successfully");
        
        // Start polling for new activities
        _pollingTimer = new System.Threading.Timer(PollForNewActivities, null, TimeSpan.Zero, TimeSpan.FromSeconds(30));
    }

    public async Task StopMonitoringAsync()
    {
        _logger.LogInformation("Stopping ActivityWatch monitoring...");
        
        _pollingTimer?.Dispose();
        _pollingTimer = null;
    }

    private async void PollForNewActivities(object? state)
    {
        try
        {
            var currentTime = DateTime.Now;
            var activities = await _activityWatchClient.GetActivityRecordsAsync(_lastPollTime, currentTime);
            
            _logger.LogDebug("Polled {Count} activities from ActivityWatch", activities.Count);

            foreach (var activity in activities.Where(a => a.Timestamp > _lastPollTime))
            {
                // Check for state changes
                if (activity.CurrentState != _currentState)
                {
                    _currentState = activity.CurrentState;
                    UserStateChanged?.Invoke(this, _currentState);
                }

                // Fire activity recorded event
                ActivityRecorded?.Invoke(this, activity);
                
                _logger.LogDebug("Activity: {App} - {Title} ({Duration}s) - State: {State}", 
                    activity.ApplicationName, activity.WindowTitle, activity.DurationSeconds, activity.CurrentState);
            }

            _lastKnownActivities = activities;
            _lastPollTime = currentTime;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error polling ActivityWatch for new activities");
        }
    }

    public async Task<List<ActivityRecord>> GetRecentActivitiesAsync(TimeSpan timespan)
    {
        var start = DateTime.Now - timespan;
        return await _activityWatchClient.GetActivityRecordsAsync(start);
    }

    public async Task<Dictionary<string, TimeSpan>> GetAppUsageSummaryAsync(DateTime start, DateTime end)
    {
        var activities = await _activityWatchClient.GetActivityRecordsAsync(start, end);
        
        return activities
            .GroupBy(a => a.ApplicationName)
            .ToDictionary(
                g => g.Key,
                g => TimeSpan.FromSeconds(g.Sum(a => a.DurationSeconds))
            );
    }

    public async Task<List<ActivityRecord>> GetFocusSessionsAsync(DateTime start, DateTime end)
    {
        var activities = await _activityWatchClient.GetActivityRecordsAsync(start, end);
        
        return activities
            .Where(a => a.CurrentState == UserState.FlowMode && a.DurationSeconds >= 300) // 5+ minute sessions
            .OrderBy(a => a.Timestamp)
            .ToList();
    }

    public async Task<UserState> GetCurrentUserStateAsync()
    {
        // Get very recent activities to determine current state
        var recentActivities = await GetRecentActivitiesAsync(TimeSpan.FromMinutes(5));
        
        if (!recentActivities.Any())
            return UserState.Away;

        var lastActivity = recentActivities.OrderByDescending(a => a.Timestamp).First();
        var timeSinceLastActivity = DateTime.Now - lastActivity.Timestamp;

        // If last activity was more than 5 minutes ago, user is likely away
        if (timeSinceLastActivity.TotalMinutes > 5)
            return UserState.Away;

        return lastActivity.CurrentState;
    }

    public async Task<Dictionary<string, object>> ExecuteCustomQueryAsync(string query)
    {
        return await _activityWatchClient.QueryAsync(query);
    }
}