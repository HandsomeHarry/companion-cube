using System.Text.Json.Serialization;

namespace CompanionCube.Core.Models;

public class ActivityWatchEvent
{
    [JsonPropertyName("id")]
    public int? Id { get; set; }
    
    [JsonPropertyName("timestamp")]
    public DateTime Timestamp { get; set; }
    
    [JsonPropertyName("duration")]
    public double Duration { get; set; }
    
    [JsonPropertyName("data")]
    public Dictionary<string, object> Data { get; set; } = new();
}

public class ActivityWatchBucket
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = string.Empty;
    
    [JsonPropertyName("name")]
    public string Name { get; set; } = string.Empty;
    
    [JsonPropertyName("type")]
    public string Type { get; set; } = string.Empty;
    
    [JsonPropertyName("client")]
    public string Client { get; set; } = string.Empty;
    
    [JsonPropertyName("hostname")]
    public string Hostname { get; set; } = string.Empty;
    
    [JsonPropertyName("created")]
    public DateTime Created { get; set; }
}

public class WindowEvent
{
    public string App { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string? Url { get; set; }
    public bool? Incognito { get; set; }
    public bool? Audible { get; set; }
}

public class AfkEvent
{
    public string Status { get; set; } = string.Empty; // "afk" or "not-afk"
}

public class WebEvent
{
    public string Url { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public bool? Incognito { get; set; }
    public bool? Audible { get; set; }
    public string? TabId { get; set; }
}