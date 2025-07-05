namespace CompanionCube.Core.Models;

public class ActivityRecord
{
    public int Id { get; set; }
    public DateTime Timestamp { get; set; }
    public string ApplicationName { get; set; } = string.Empty;
    public string WindowTitle { get; set; } = string.Empty;
    public int DurationSeconds { get; set; }
    public string InferredTask { get; set; } = string.Empty;
    public UserState CurrentState { get; set; }
}