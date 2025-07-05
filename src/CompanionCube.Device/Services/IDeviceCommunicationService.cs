using CompanionCube.Device.Models;

namespace CompanionCube.Device.Services;

public interface IDeviceCommunicationService
{
    Task<bool> ConnectAsync(string portName);
    Task DisconnectAsync();
    Task SendStateAsync(DeviceState state);
    Task SendMessageAsync(DeviceMessage message);
    Task<bool> IsConnectedAsync();
    event EventHandler<string> DeviceDisconnected;
    event EventHandler<string> DeviceError;
}