using CompanionCube.Core.Models;

namespace CompanionCube.Core.Services;

public interface IActivityWatchClient
{
    Task<bool> IsConnectedAsync();
    Task<List<ActivityWatchBucket>> GetBucketsAsync();
    Task<List<ActivityWatchEvent>> GetEventsAsync(string bucketId, DateTime? start = null, DateTime? end = null, int limit = 1000);
    Task<List<ActivityWatchEvent>> GetWindowEventsAsync(DateTime? start = null, DateTime? end = null, int limit = 1000);
    Task<List<ActivityWatchEvent>> GetAfkEventsAsync(DateTime? start = null, DateTime? end = null, int limit = 1000);
    Task<List<ActivityWatchEvent>> GetWebEventsAsync(DateTime? start = null, DateTime? end = null, int limit = 1000);
    Task<List<ActivityRecord>> GetActivityRecordsAsync(DateTime? start = null, DateTime? end = null);
    Task<Dictionary<string, object>> QueryAsync(string query, DateTime? timeperiod_start = null, DateTime? timeperiod_end = null);
}