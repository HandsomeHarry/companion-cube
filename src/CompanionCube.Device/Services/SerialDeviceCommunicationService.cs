using System.IO.Ports;
using System.Text.Json;
using CompanionCube.Device.Models;
using CompanionCube.Device.Services;
using Microsoft.Extensions.Logging;

namespace CompanionCube.Device.Services;

public class SerialDeviceCommunicationService : IDeviceCommunicationService, IDisposable
{
    private readonly ILogger<SerialDeviceCommunicationService> _logger;
    private SerialPort? _serialPort;
    private readonly object _lock = new object();
    private bool _isConnected = false;

    public event EventHandler<string>? DeviceDisconnected;
    public event EventHandler<string>? DeviceError;

    public SerialDeviceCommunicationService(ILogger<SerialDeviceCommunicationService> logger)
    {
        _logger = logger;
    }

    public async Task<bool> ConnectAsync(string portName)
    {
        try
        {
            lock (_lock)
            {
                if (_serialPort != null && _serialPort.IsOpen)
                {
                    _serialPort.Close();
                    _serialPort.Dispose();
                }

                _serialPort = new SerialPort(portName, 9600, Parity.None, 8, StopBits.One)
                {
                    ReadTimeout = 5000,
                    WriteTimeout = 5000
                };

                _serialPort.Open();
                _isConnected = true;
            }

            // Send initial handshake
            await SendHandshakeAsync();
            
            return true;
        }
        catch (Exception ex)
        {
            DeviceError?.Invoke(this, $"Connection failed: {ex.Message}");
            return false;
        }
    }

    public Task DisconnectAsync()
    {
        try
        {
            lock (_lock)
            {
                if (_serialPort != null && _serialPort.IsOpen)
                {
                    _serialPort.Close();
                }
                _isConnected = false;
            }
        }
        catch (Exception ex)
        {
            DeviceError?.Invoke(this, $"Disconnect error: {ex.Message}");
        }
        
        return Task.CompletedTask;
    }

    public async Task SendStateAsync(DeviceState state)
    {
        var message = new DeviceMessage
        {
            State = state,
            DisplayText = GetStateDisplayText(state)
        };

        await SendMessageAsync(message);
    }

    public Task SendMessageAsync(DeviceMessage message)
    {
        try
        {
            lock (_lock)
            {
                if (_serialPort == null || !_serialPort.IsOpen)
                {
                    throw new InvalidOperationException("Device not connected");
                }

                var json = JsonSerializer.Serialize(message);
                var data = System.Text.Encoding.UTF8.GetBytes(json + "\n");
                
                _serialPort.Write(data, 0, data.Length);
            }
        }
        catch (Exception ex)
        {
            DeviceError?.Invoke(this, $"Send message error: {ex.Message}");
            
            // If communication fails, assume device is disconnected
            _isConnected = false;
            DeviceDisconnected?.Invoke(this, "Communication lost");
        }
        
        return Task.CompletedTask;
    }

    public Task<bool> IsConnectedAsync()
    {
        lock (_lock)
        {
            return Task.FromResult(_isConnected && _serialPort != null && _serialPort.IsOpen);
        }
    }

    private async Task SendHandshakeAsync()
    {
        var handshake = new DeviceMessage
        {
            State = DeviceState.Off,
            DisplayText = "Connected"
        };

        await SendMessageAsync(handshake);
    }

    private string GetStateDisplayText(DeviceState state)
    {
        return state switch
        {
            DeviceState.FlowMode => "Flow",
            DeviceState.WorkingInterruptible => "Working",
            DeviceState.NeedsNudge => "Nudge",
            DeviceState.Away => "Away",
            DeviceState.Off => "",
            _ => "Unknown"
        };
    }

    public void Dispose()
    {
        lock (_lock)
        {
            if (_serialPort != null)
            {
                if (_serialPort.IsOpen)
                {
                    _serialPort.Close();
                }
                _serialPort.Dispose();
                _serialPort = null;
            }
        }
    }
}