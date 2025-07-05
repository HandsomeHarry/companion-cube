using CompanionCube.Core.Models;
using CompanionCube.Core.Services;
using CompanionCube.Data;
using CompanionCube.Device.Models;
using CompanionCube.Device.Services;

namespace CompanionCube.Service.Services;

public class CompanionCubeService : BackgroundService
{
    private readonly ILogger<CompanionCubeService> _logger;
    private readonly IServiceProvider _serviceProvider;
    private readonly IActivityMonitor _activityMonitor;
    private readonly ILlmService _llmService;
    private readonly IPatternDetectionService _patternService;
    private readonly IDeviceCommunicationService? _deviceService;
    private List<ActivityRecord> _recentActivities = new();
    private CompanionMode _currentMode = CompanionMode.StudyBuddy;

    public CompanionCubeService(
        ILogger<CompanionCubeService> logger,
        IServiceProvider serviceProvider,
        IActivityMonitor activityMonitor,
        ILlmService llmService,
        IPatternDetectionService patternService,
        IDeviceCommunicationService? deviceService = null)
    {
        _logger = logger;
        _serviceProvider = serviceProvider;
        _activityMonitor = activityMonitor;
        _llmService = llmService;
        _patternService = patternService;
        _deviceService = deviceService;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("Companion Cube Service starting...");

        _activityMonitor.ActivityRecorded += OnActivityRecorded;
        _activityMonitor.UserStateChanged += OnUserStateChanged;

        await _activityMonitor.StartMonitoringAsync(stoppingToken);
        
        // Start periodic tasks
        _ = Task.Run(() => PeriodicStateAnalysis(stoppingToken), stoppingToken);
        _ = Task.Run(() => PeriodicSuggestions(stoppingToken), stoppingToken);

        while (!stoppingToken.IsCancellationRequested)
        {
            await Task.Delay(1000, stoppingToken);
        }

        await _activityMonitor.StopMonitoringAsync();
        _logger.LogInformation("Companion Cube Service stopped.");
    }

    private async void OnActivityRecorded(object? sender, ActivityRecord activity)
    {
        try
        {
            // Infer task using LLM
            if (await _llmService.IsLlmAvailableAsync())
            {
                activity.InferredTask = await _llmService.InferTaskAsync(activity);
            }

            using var scope = _serviceProvider.CreateScope();
            var context = scope.ServiceProvider.GetRequiredService<CompanionCubeDbContext>();
            
            context.ActivityRecords.Add(activity);
            await context.SaveChangesAsync();
            
            // Keep recent activities in memory
            _recentActivities.Add(activity);
            if (_recentActivities.Count > 100)
            {
                _recentActivities.RemoveAt(0);
            }
            
            _logger.LogDebug("Activity recorded: {App} - {Title} - Task: {Task}", 
                activity.ApplicationName, activity.WindowTitle, activity.InferredTask);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error saving activity record");
        }
    }

    private async void OnUserStateChanged(object? sender, UserState newState)
    {
        _logger.LogInformation("User state changed to: {State}", newState);
        
        // Update device state
        if (_deviceService != null && await _deviceService.IsConnectedAsync())
        {
            var deviceState = MapUserStateToDeviceState(newState);
            await _deviceService.SendStateAsync(deviceState);
        }
    }

    private async Task PeriodicStateAnalysis(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                await Task.Delay(TimeSpan.FromMinutes(5), cancellationToken);
                
                if (_recentActivities.Any() && await _llmService.IsLlmAvailableAsync())
                {
                    var inferredState = await _llmService.InferUserStateAsync(_recentActivities);
                    var currentState = await _patternService.AnalyzeCurrentStateAsync(_recentActivities);
                    
                    // Combine LLM and pattern-based analysis
                    if (inferredState == UserState.NeedsNudge && currentState == UserState.NeedsNudge)
                    {
                        await GenerateNudge();
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in periodic state analysis");
            }
        }
    }

    private async Task PeriodicSuggestions(CancellationToken cancellationToken)
    {
        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                var frequency = _currentMode switch
                {
                    CompanionMode.StudyBuddy => TimeSpan.FromMinutes(20),
                    CompanionMode.CoachMode => TimeSpan.FromMinutes(30),
                    CompanionMode.GhostMode => TimeSpan.FromHours(2),
                    _ => TimeSpan.FromMinutes(45)
                };
                
                await Task.Delay(frequency, cancellationToken);
                
                if (_currentMode != CompanionMode.GhostMode && _recentActivities.Any())
                {
                    var currentState = await _patternService.AnalyzeCurrentStateAsync(_recentActivities);
                    
                    if (currentState != UserState.FlowMode) // Don't interrupt flow
                    {
                        var suggestion = await _llmService.GenerateSuggestionAsync(
                            currentState, _currentMode, _recentActivities);
                        
                        if (!string.IsNullOrEmpty(suggestion))
                        {
                            await ShowSuggestion(suggestion);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error in periodic suggestions");
            }
        }
    }

    private async Task GenerateNudge()
    {
        var suggestions = await _patternService.GetSuggestionsAsync(_recentActivities, _currentMode);
        
        if (suggestions.Any())
        {
            var nudge = suggestions.First();
            await ShowSuggestion(nudge);
            
            if (_deviceService != null && await _deviceService.IsConnectedAsync())
            {
                await _deviceService.SendMessageAsync(new DeviceMessage
                {
                    State = DeviceState.NeedsNudge,
                    DisplayText = "Need help?",
                    Brightness = 80
                });
            }
        }
    }

    private async Task ShowSuggestion(string suggestion)
    {
        _logger.LogInformation("Showing suggestion: {Suggestion}", suggestion);
        
        // In a real implementation, this would show a Windows notification
        // For now, just log it
        
        if (_deviceService != null && await _deviceService.IsConnectedAsync())
        {
            await _deviceService.SendMessageAsync(new DeviceMessage
            {
                State = DeviceState.WorkingInterruptible,
                DisplayText = suggestion.Length > 20 ? suggestion.Substring(0, 20) : suggestion,
                Brightness = 60
            });
        }
    }

    private DeviceState MapUserStateToDeviceState(UserState userState)
    {
        return userState switch
        {
            UserState.FlowMode => DeviceState.FlowMode,
            UserState.WorkingInterruptible => DeviceState.WorkingInterruptible,
            UserState.NeedsNudge => DeviceState.NeedsNudge,
            UserState.Away => DeviceState.Away,
            _ => DeviceState.Off
        };
    }
}