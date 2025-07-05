using CompanionCube.Core.Services;
using CompanionCube.Data;
using CompanionCube.Service.Services;
using CompanionCube.LlmBridge.Services;
using CompanionCube.Device.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;

var host = Host.CreateDefaultBuilder(args)
    .ConfigureServices((context, services) => {

// Database
services.AddDbContext<CompanionCubeDbContext>(options =>
    options.UseSqlite(context.Configuration.GetConnectionString("DefaultConnection")));

// HTTP Client for ActivityWatch
services.AddHttpClient<ActivityWatchClient>();

// Activity monitoring - choose between ActivityWatch and Windows API
var useActivityWatch = context.Configuration.GetValue<bool>("ActivityWatch:UseActivityWatch", true);
if (useActivityWatch)
{
    services.AddScoped<IActivityWatchClient, ActivityWatchClient>();
    services.AddScoped<IActivityMonitor, ActivityWatchMonitor>();
}
else
{
    services.AddScoped<IActivityMonitor, WindowsActivityMonitor>();
}

// Core services
services.AddScoped<IPatternDetectionService, PatternDetectionService>();

// LLM service
var modelPath = context.Configuration.GetValue<string>("LlmModelPath") ?? 
                Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "models", "phi-2-adhd.gguf");
services.AddScoped<ILlmService>(provider => 
    new LocalLlmService(provider.GetRequiredService<ILogger<LocalLlmService>>(), modelPath));

// Device service (optional)
var enableDevice = context.Configuration.GetValue<bool>("EnableDevice");
if (enableDevice)
{
    services.AddScoped<IDeviceCommunicationService, SerialDeviceCommunicationService>();
}

// Main service
services.AddHostedService<CompanionCubeService>();

// Windows service support
services.AddWindowsService();
})
.Build();

// Ensure database is created
using (var scope = host.Services.CreateScope())
{
    var context = scope.ServiceProvider.GetRequiredService<CompanionCubeDbContext>();
    await context.Database.EnsureCreatedAsync();
}

await host.RunAsync();