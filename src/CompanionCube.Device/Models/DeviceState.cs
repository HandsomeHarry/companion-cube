namespace CompanionCube.Device.Models;

public enum DeviceState
{
    Off,
    FlowMode,
    WorkingInterruptible,
    NeedsNudge,
    Away
}

public class DeviceMessage
{
    public DeviceState State { get; set; }
    public string? DisplayText { get; set; }
    public int Brightness { get; set; } = 100;
}