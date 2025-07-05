using CompanionCube.Core.Services;
using CompanionCube.Data;
using CompanionCube.Service.Services;
using CompanionCube.LlmBridge.Services;
using CompanionCube.Device.Services;
using Microsoft.EntityFrameworkCore;

var builder = Host.CreateApplicationBuilder(args);

// Database
builder.Services.AddDbContext<CompanionCubeDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("DefaultConnection")));

// HTTP Client for ActivityWatch
builder.Services.AddHttpClient<ActivityWatchClient>();

// Activity monitoring - choose between ActivityWatch and Windows API
var useActivityWatch = builder.Configuration.GetValue<bool>("ActivityWatch:UseActivityWatch", true);
if (useActivityWatch)
{
    builder.Services.AddScoped<IActivityWatchClient, ActivityWatchClient>();
    builder.Services.AddScoped<IActivityMonitor, ActivityWatchMonitor>();
}
else
{
    builder.Services.AddScoped<IActivityMonitor, WindowsActivityMonitor>();
}

// Core services
builder.Services.AddScoped<IPatternDetectionService, PatternDetectionService>();

// LLM service
var modelPath = builder.Configuration.GetValue<string>("LlmModelPath") ?? 
                Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "models", "phi-2-adhd.gguf");
builder.Services.AddScoped<ILlmService>(provider => 
    new LocalLlmService(provider.GetRequiredService<ILogger<LocalLlmService>>(), modelPath));

// Device service (optional)
var enableDevice = builder.Configuration.GetValue<bool>("EnableDevice");
if (enableDevice)
{
    builder.Services.AddScoped<IDeviceCommunicationService, SerialDeviceCommunicationService>();
}

// Main service
builder.Services.AddHostedService<CompanionCubeService>();

// Windows service support
builder.Services.AddWindowsService();

var host = builder.Build();

// Ensure database is created
using (var scope = host.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<CompanionCubeDbContext>();
    await context.Database.EnsureCreatedAsync();
}

await host.RunAsync();