using CompanionCube.Core.Models;

namespace CompanionCube.Core.Services;

public interface IActivityMonitor
{
    Task StartMonitoringAsync(CancellationToken cancellationToken = default);
    Task StopMonitoringAsync();
    event EventHandler<ActivityRecord> ActivityRecorded;
    event EventHandler<UserState> UserStateChanged;
}