namespace CompanionCube.Core.Models;

public class GoodDayTemplate
{
    public int Id { get; set; }
    public DateTime Date { get; set; }
    public string ActivityPattern { get; set; } = string.Empty;
    public string TimingPattern { get; set; } = string.Empty;
    public string TransitionPattern { get; set; } = string.Empty;
    public int UserRating { get; set; }
    public List<ActivityRecord> Activities { get; set; } = new();
}