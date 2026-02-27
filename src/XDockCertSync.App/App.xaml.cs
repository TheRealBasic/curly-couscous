using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using Serilog;
using XDockCertSync.App.Models;
using XDockCertSync.App.ViewModels;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Infrastructure.Parsing;
using XDockCertSync.Infrastructure.Transport;
using XDockCertSync.Persistence;

namespace XDockCertSync.App;

public partial class App : Application
{
    private ServiceProvider? _serviceProvider;

    protected override void OnStartup(StartupEventArgs e)
    {
        base.OnStartup(e);

        var dataRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "XDockCertSync");
        Directory.CreateDirectory(dataRoot);

        Log.Logger = new LoggerConfiguration()
            .MinimumLevel.Information()
            .WriteTo.File(
                Path.Combine(dataRoot, "logs", "xdock-.log"),
                rollingInterval: RollingInterval.Day,
                retainedFileCountLimit: 14,
                rollOnFileSizeLimit: true,
                fileSizeLimitBytes: 2 * 1024 * 1024)
            .CreateLogger();

        var services = new ServiceCollection();
        services.AddSingleton(Log.Logger);
        services.AddSingleton<HttpClient>(_ => new HttpClient { BaseAddress = new Uri("http://localhost:5000/") });
        services.AddSingleton<IXDockClient, XDockManagerHttpClient>();
        services.AddSingleton<ICertificatePayloadParser, XDockJsonPayloadParser>();
        services.AddSingleton<ISettingsStore<SyncSettings>>(_ =>
            new JsonSettingsStore<SyncSettings>(Path.Combine(dataRoot, "settings.json")));
        services.AddSingleton<SettingsViewModel>();
        services.AddSingleton<MainWindow>();

        _serviceProvider = services.BuildServiceProvider();

        var window = _serviceProvider.GetRequiredService<MainWindow>();
        window.Show();

        Log.Information("Application started");
    }

    protected override void OnExit(ExitEventArgs e)
    {
        Log.Information("Application stopping");
        Log.CloseAndFlush();
        _serviceProvider?.Dispose();
        base.OnExit(e);
    }
}
