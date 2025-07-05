using System.Diagnostics;
using System.Runtime.InteropServices;
using CompanionCube.Core.Models;
using CompanionCube.Core.Services;

namespace CompanionCube.Service.Services;

public class WindowsActivityMonitor : IActivityMonitor
{
    private readonly ILogger<WindowsActivityMonitor> _logger;
    private System.Threading.Timer? _monitoringTimer;
    private string _lastActiveWindow = string.Empty;
    private string _lastActiveProcess = string.Empty;
    private DateTime _lastActivityTime = DateTime.Now;
    private UserState _currentState = UserState.Away;

    public event EventHandler<ActivityRecord>? ActivityRecorded;
    public event EventHandler<UserState>? UserStateChanged;

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);

    [DllImport("user32.dll")]
    private static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);

    public WindowsActivityMonitor(ILogger<WindowsActivityMonitor> logger)
    {
        _logger = logger;
    }

    public Task StartMonitoringAsync(CancellationToken cancellationToken = default)
    {
        _logger.LogInformation("Starting activity monitoring...");
        
        _monitoringTimer = new System.Threading.Timer(MonitorActivity, null, TimeSpan.Zero, TimeSpan.FromSeconds(5));
        
        return Task.CompletedTask;
    }

    public Task StopMonitoringAsync()
    {
        _logger.LogInformation("Stopping activity monitoring...");
        
        _monitoringTimer?.Dispose();
        _monitoringTimer = null;
        
        return Task.CompletedTask;
    }

    private void MonitorActivity(object? state)
    {
        try
        {
            var foregroundWindow = GetForegroundWindow();
            if (foregroundWindow == IntPtr.Zero)
            {
                UpdateUserState(UserState.Away);
                return;
            }

            var windowTitle = GetWindowTitle(foregroundWindow);
            var processName = GetProcessName(foregroundWindow);

            if (string.IsNullOrEmpty(windowTitle) || string.IsNullOrEmpty(processName))
            {
                UpdateUserState(UserState.Away);
                return;
            }

            var hasChanged = windowTitle != _lastActiveWindow || processName != _lastActiveProcess;
            
            if (hasChanged)
            {
                if (!string.IsNullOrEmpty(_lastActiveWindow))
                {
                    var duration = (int)(DateTime.Now - _lastActivityTime).TotalSeconds;
                    
                    var activityRecord = new ActivityRecord
                    {
                        Timestamp = _lastActivityTime,
                        ApplicationName = _lastActiveProcess,
                        WindowTitle = _lastActiveWindow,
                        DurationSeconds = duration,
                        InferredTask = InferTask(_lastActiveProcess, _lastActiveWindow),
                        CurrentState = _currentState
                    };

                    ActivityRecorded?.Invoke(this, activityRecord);
                }

                _lastActiveWindow = windowTitle;
                _lastActiveProcess = processName;
                _lastActivityTime = DateTime.Now;
            }

            UpdateUserState(DetermineUserState(processName, windowTitle));
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error monitoring activity");
        }
    }

    private string GetWindowTitle(IntPtr hWnd)
    {
        var text = new System.Text.StringBuilder(256);
        GetWindowText(hWnd, text, text.Capacity);
        return text.ToString();
    }

    private string GetProcessName(IntPtr hWnd)
    {
        try
        {
            GetWindowThreadProcessId(hWnd, out int processId);
            var process = Process.GetProcessById(processId);
            return process.ProcessName;
        }
        catch
        {
            return string.Empty;
        }
    }

    private UserState DetermineUserState(string processName, string windowTitle)
    {
        var focusApps = new[] { "code", "devenv", "notepad", "sublime", "atom", "vim" };
        var entertainmentApps = new[] { "chrome", "firefox", "edge", "steam", "discord" };
        
        if (focusApps.Contains(processName.ToLower()) || 
            windowTitle.Contains("Visual Studio") || 
            windowTitle.Contains("Code"))
        {
            return UserState.FlowMode;
        }
        
        if (entertainmentApps.Contains(processName.ToLower()) && 
            (windowTitle.Contains("YouTube") || windowTitle.Contains("Netflix") || windowTitle.Contains("Reddit")))
        {
            return UserState.NeedsNudge;
        }
        
        return UserState.WorkingInterruptible;
    }

    private void UpdateUserState(UserState newState)
    {
        if (_currentState != newState)
        {
            _currentState = newState;
            UserStateChanged?.Invoke(this, newState);
        }
    }

    private string InferTask(string processName, string windowTitle)
    {
        return processName.ToLower() switch
        {
            "code" or "devenv" => "Coding",
            "chrome" or "firefox" or "edge" => windowTitle.Contains("YouTube") ? "Entertainment" : "Research",
            "notepad" or "wordpad" => "Writing",
            "outlook" => "Email",
            _ => "Unknown"
        };
    }
}