using System.Net.Http;
using System.Text;
using System.Text.Json;
using CompanionCube.Core.Models;
using CompanionCube.Core.Services;

namespace CompanionCube.Service.Services;

public class ActivityWatchClient : IActivityWatchClient
{
    private readonly HttpClient _httpClient;
    private readonly ILogger<ActivityWatchClient> _logger;
    private readonly string _baseUrl;
    private string? _windowBucketId;
    private string? _afkBucketId;
    private string? _webBucketId;

    public ActivityWatchClient(HttpClient httpClient, ILogger<ActivityWatchClient> logger, IConfiguration configuration)
    {
        _httpClient = httpClient;
        _logger = logger;
        _baseUrl = configuration.GetValue<string>("ActivityWatch:ServerUrl") ?? "http://localhost:5600";
        _httpClient.BaseAddress = new Uri(_baseUrl);
    }

    public async Task<bool> IsConnectedAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/api/0/info");
            return response.IsSuccessStatusCode;
        }
        catch (Exception ex)
        {
            _logger.LogDebug("ActivityWatch connection failed: {Error}", ex.Message);
            return false;
        }
    }

    public async Task<List<ActivityWatchBucket>> GetBucketsAsync()
    {
        try
        {
            var response = await _httpClient.GetAsync("/api/0/buckets/");
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError("Failed to get buckets: {StatusCode}", response.StatusCode);
                return new List<ActivityWatchBucket>();
            }

            var content = await response.Content.ReadAsStringAsync();
            var bucketsDict = JsonSerializer.Deserialize<Dictionary<string, ActivityWatchBucket>>(content);
            
            return bucketsDict?.Values.ToList() ?? new List<ActivityWatchBucket>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting ActivityWatch buckets");
            return new List<ActivityWatchBucket>();
        }
    }

    public async Task<List<ActivityWatchEvent>> GetEventsAsync(string bucketId, DateTime? start = null, DateTime? end = null, int limit = 1000)
    {
        try
        {
            var startParam = start?.ToString("yyyy-MM-ddTHH:mm:ss.fffZ") ?? "";
            var endParam = end?.ToString("yyyy-MM-ddTHH:mm:ss.fffZ") ?? "";
            
            var url = $"/api/0/buckets/{bucketId}/events?limit={limit}";
            if (!string.IsNullOrEmpty(startParam))
                url += $"&start={startParam}";
            if (!string.IsNullOrEmpty(endParam))
                url += $"&end={endParam}";

            var response = await _httpClient.GetAsync(url);
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError("Failed to get events from bucket {BucketId}: {StatusCode}", bucketId, response.StatusCode);
                return new List<ActivityWatchEvent>();
            }

            var content = await response.Content.ReadAsStringAsync();
            var events = JsonSerializer.Deserialize<List<ActivityWatchEvent>>(content, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });

            return events ?? new List<ActivityWatchEvent>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error getting events from bucket {BucketId}", bucketId);
            return new List<ActivityWatchEvent>();
        }
    }

    public async Task<List<ActivityWatchEvent>> GetWindowEventsAsync(DateTime? start = null, DateTime? end = null, int limit = 1000)
    {
        await EnsureBucketIds();
        
        if (string.IsNullOrEmpty(_windowBucketId))
        {
            _logger.LogWarning("No window watcher bucket found");
            return new List<ActivityWatchEvent>();
        }

        return await GetEventsAsync(_windowBucketId, start, end, limit);
    }

    public async Task<List<ActivityWatchEvent>> GetAfkEventsAsync(DateTime? start = null, DateTime? end = null, int limit = 1000)
    {
        await EnsureBucketIds();
        
        if (string.IsNullOrEmpty(_afkBucketId))
        {
            _logger.LogWarning("No AFK watcher bucket found");
            return new List<ActivityWatchEvent>();
        }

        return await GetEventsAsync(_afkBucketId, start, end, limit);
    }

    public async Task<List<ActivityWatchEvent>> GetWebEventsAsync(DateTime? start = null, DateTime? end = null, int limit = 1000)
    {
        await EnsureBucketIds();
        
        if (string.IsNullOrEmpty(_webBucketId))
        {
            _logger.LogDebug("No web watcher bucket found");
            return new List<ActivityWatchEvent>();
        }

        return await GetEventsAsync(_webBucketId, start, end, limit);
    }

    public async Task<List<ActivityRecord>> GetActivityRecordsAsync(DateTime? start = null, DateTime? end = null)
    {
        var windowEvents = await GetWindowEventsAsync(start, end);
        var afkEvents = await GetAfkEventsAsync(start, end);
        var webEvents = await GetWebEventsAsync(start, end);

        var records = new List<ActivityRecord>();

        // Convert window events to activity records
        foreach (var windowEvent in windowEvents)
        {
            if (windowEvent.Data.TryGetValue("app", out var appObj) &&
                windowEvent.Data.TryGetValue("title", out var titleObj))
            {
                var app = appObj?.ToString() ?? "Unknown";
                var title = titleObj?.ToString() ?? "Unknown";
                
                var record = new ActivityRecord
                {
                    Timestamp = windowEvent.Timestamp,
                    ApplicationName = app,
                    WindowTitle = title,
                    DurationSeconds = (int)windowEvent.Duration,
                    InferredTask = InferTaskFromActivity(app, title),
                    CurrentState = DetermineUserState(app, title, afkEvents, windowEvent.Timestamp)
                };

                records.Add(record);
            }
        }

        // Enhance with web activity data
        foreach (var webEvent in webEvents)
        {
            if (webEvent.Data.TryGetValue("url", out var urlObj) &&
                webEvent.Data.TryGetValue("title", out var titleObj))
            {
                var url = urlObj?.ToString() ?? "";
                var title = titleObj?.ToString() ?? "";
                
                // Find corresponding window event or create new record
                var existingRecord = records.FirstOrDefault(r => 
                    Math.Abs((r.Timestamp - webEvent.Timestamp).TotalSeconds) < 5);

                if (existingRecord != null)
                {
                    // Enhance existing record with web data
                    existingRecord.WindowTitle = $"{existingRecord.WindowTitle} - {title}";
                    existingRecord.InferredTask = InferTaskFromWebActivity(url, title);
                }
                else
                {
                    // Create new record for web activity
                    var record = new ActivityRecord
                    {
                        Timestamp = webEvent.Timestamp,
                        ApplicationName = ExtractAppFromUrl(url),
                        WindowTitle = title,
                        DurationSeconds = (int)webEvent.Duration,
                        InferredTask = InferTaskFromWebActivity(url, title),
                        CurrentState = DetermineUserStateFromWeb(url, title)
                    };

                    records.Add(record);
                }
            }
        }

        return records.OrderBy(r => r.Timestamp).ToList();
    }

    public async Task<Dictionary<string, object>> QueryAsync(string query, DateTime? timeperiod_start = null, DateTime? timeperiod_end = null)
    {
        try
        {
            var queryData = new
            {
                query = new[] { query },
                timeperiods = new[]
                {
                    new
                    {
                        start = timeperiod_start?.ToString("yyyy-MM-ddTHH:mm:ss.fffZ") ?? DateTime.Today.ToString("yyyy-MM-ddTHH:mm:ss.fffZ"),
                        end = timeperiod_end?.ToString("yyyy-MM-ddTHH:mm:ss.fffZ") ?? DateTime.Now.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
                    }
                }
            };

            var json = JsonSerializer.Serialize(queryData);
            var content = new StringContent(json, Encoding.UTF8, "application/json");

            var response = await _httpClient.PostAsync("/api/0/query/", content);
            if (!response.IsSuccessStatusCode)
            {
                _logger.LogError("Query failed: {StatusCode}", response.StatusCode);
                return new Dictionary<string, object>();
            }

            var responseContent = await response.Content.ReadAsStringAsync();
            var result = JsonSerializer.Deserialize<Dictionary<string, object>>(responseContent);
            
            return result ?? new Dictionary<string, object>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error executing ActivityWatch query: {Query}", query);
            return new Dictionary<string, object>();
        }
    }

    private async Task EnsureBucketIds()
    {
        if (_windowBucketId != null && _afkBucketId != null)
            return;

        var buckets = await GetBucketsAsync();
        var hostname = Environment.MachineName;

        _windowBucketId = buckets.FirstOrDefault(b => b.Type == "currentwindow" && b.Hostname == hostname)?.Id;
        _afkBucketId = buckets.FirstOrDefault(b => b.Type == "afkstatus" && b.Hostname == hostname)?.Id;
        _webBucketId = buckets.FirstOrDefault(b => b.Type.StartsWith("web.tab.current") && b.Hostname == hostname)?.Id;

        _logger.LogInformation("ActivityWatch buckets - Window: {Window}, AFK: {Afk}, Web: {Web}", 
            _windowBucketId ?? "Not found", 
            _afkBucketId ?? "Not found", 
            _webBucketId ?? "Not found");
    }

    private string InferTaskFromActivity(string app, string title)
    {
        return app.ToLower() switch
        {
            "code" or "devenv" or "rider" or "pycharm" or "intellij" => "Coding",
            "chrome" or "firefox" or "edge" or "safari" => InferTaskFromWebTitle(title),
            "notepad" or "wordpad" or "word" or "libreoffice" => "Writing",
            "outlook" or "thunderbird" => "Email",
            "teams" or "slack" or "discord" or "zoom" => "Communication",
            "spotify" or "vlc" or "media" => "Entertainment",
            "explorer" or "finder" => "File Management",
            _ => "General"
        };
    }

    private string InferTaskFromWebActivity(string url, string title)
    {
        var domain = ExtractDomain(url);
        
        return domain switch
        {
            "github.com" or "gitlab.com" or "bitbucket.org" => "Coding",
            "stackoverflow.com" or "docs.microsoft.com" or "developer.mozilla.org" => "Research",
            "youtube.com" or "netflix.com" or "twitch.tv" => "Entertainment",
            "twitter.com" or "facebook.com" or "linkedin.com" => "Social Media",
            "gmail.com" or "outlook.com" or "mail.google.com" => "Email",
            "reddit.com" or "news.ycombinator.com" => "News/Discussion",
            _ => InferTaskFromWebTitle(title)
        };
    }

    private string InferTaskFromWebTitle(string title)
    {
        var lowerTitle = title.ToLower();
        
        if (lowerTitle.Contains("stackoverflow") || lowerTitle.Contains("documentation") || lowerTitle.Contains("tutorial"))
            return "Research";
        if (lowerTitle.Contains("youtube") || lowerTitle.Contains("video") || lowerTitle.Contains("music"))
            return "Entertainment";
        if (lowerTitle.Contains("github") || lowerTitle.Contains("code") || lowerTitle.Contains("programming"))
            return "Coding";
        if (lowerTitle.Contains("mail") || lowerTitle.Contains("email"))
            return "Email";
        if (lowerTitle.Contains("news") || lowerTitle.Contains("article"))
            return "Reading";
        
        return "Web Browsing";
    }

    private UserState DetermineUserState(string app, string title, List<ActivityWatchEvent> afkEvents, DateTime timestamp)
    {
        // Check if user was AFK around this time
        var relevantAfkEvent = afkEvents.FirstOrDefault(e => 
            Math.Abs((e.Timestamp - timestamp).TotalMinutes) < 2);
        
        if (relevantAfkEvent?.Data.TryGetValue("status", out var statusObj) == true &&
            statusObj?.ToString() == "afk")
        {
            return UserState.Away;
        }

        // Determine state based on application and content
        var focusApps = new[] { "code", "devenv", "rider", "pycharm", "intellij", "vim", "sublime" };
        var distractionSites = new[] { "youtube", "reddit", "facebook", "twitter", "netflix", "twitch" };
        
        if (focusApps.Contains(app.ToLower()))
        {
            return UserState.FlowMode;
        }
        
        if (distractionSites.Any(site => title.ToLower().Contains(site)))
        {
            return UserState.NeedsNudge;
        }
        
        return UserState.WorkingInterruptible;
    }

    private UserState DetermineUserStateFromWeb(string url, string title)
    {
        var domain = ExtractDomain(url);
        var distractionSites = new[] { "youtube.com", "reddit.com", "facebook.com", "twitter.com", "netflix.com", "twitch.tv" };
        var focusSites = new[] { "github.com", "stackoverflow.com", "docs.microsoft.com", "developer.mozilla.org" };
        
        if (focusSites.Contains(domain))
            return UserState.FlowMode;
        
        if (distractionSites.Contains(domain))
            return UserState.NeedsNudge;
        
        return UserState.WorkingInterruptible;
    }

    private string ExtractAppFromUrl(string url)
    {
        var domain = ExtractDomain(url);
        return domain switch
        {
            "github.com" => "GitHub",
            "stackoverflow.com" => "Stack Overflow",
            "youtube.com" => "YouTube",
            "gmail.com" => "Gmail",
            _ => "Web Browser"
        };
    }

    private string ExtractDomain(string url)
    {
        try
        {
            var uri = new Uri(url);
            return uri.Host.ToLower();
        }
        catch
        {
            return "";
        }
    }
}