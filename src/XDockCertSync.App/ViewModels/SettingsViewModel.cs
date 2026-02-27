using System.ComponentModel;
using System.Runtime.CompilerServices;
using Serilog;
using XDockCertSync.App.Models;
using XDockCertSync.Core.Interfaces;

namespace XDockCertSync.App.ViewModels;

public sealed class SettingsViewModel : INotifyPropertyChanged
{
    private readonly ISettingsStore<SyncSettings> _settingsStore;
    private readonly ILogger _logger;

    public SettingsViewModel(ISettingsStore<SyncSettings> settingsStore, ILogger logger)
    {
        _settingsStore = settingsStore;
        _logger = logger;
        SaveCommand = new RelayCommand(SaveAsync);
    }

    private string _hostname = string.Empty;
    private string _username = string.Empty;
    private string _password = string.Empty;
    private int _pollingIntervalSeconds = 300;
    private string _outputDirectory = string.Empty;
    private string _statusMessage = "Configure connection settings then save.";

    public string Hostname { get => _hostname; set => SetField(ref _hostname, value); }
    public string Username { get => _username; set => SetField(ref _username, value); }
    public string Password { get => _password; set => SetField(ref _password, value); }
    public int PollingIntervalSeconds { get => _pollingIntervalSeconds; set => SetField(ref _pollingIntervalSeconds, value); }
    public string OutputDirectory { get => _outputDirectory; set => SetField(ref _outputDirectory, value); }
    public string StatusMessage { get => _statusMessage; set => SetField(ref _statusMessage, value); }

    public RelayCommand SaveCommand { get; }

    public event PropertyChangedEventHandler? PropertyChanged;

    public async Task LoadAsync()
    {
        var settings = await _settingsStore.LoadAsync().ConfigureAwait(true);
        Hostname = settings.Hostname;
        Username = settings.Username;
        Password = settings.Password;
        PollingIntervalSeconds = settings.PollingIntervalSeconds;
        OutputDirectory = settings.OutputDirectory;
    }

    private async Task SaveAsync()
    {
        var settings = new SyncSettings
        {
            Hostname = Hostname,
            Username = Username,
            Password = Password,
            PollingIntervalSeconds = PollingIntervalSeconds,
            OutputDirectory = OutputDirectory
        };

        await _settingsStore.SaveAsync(settings).ConfigureAwait(true);

        StatusMessage = $"Saved at {DateTimeOffset.Now:t}";
        _logger.Information("Settings updated for host {Hostname} with polling interval {PollingIntervalSeconds}s", Hostname, PollingIntervalSeconds);
    }

    private void SetField<T>(ref T field, T value, [CallerMemberName] string? propertyName = null)
    {
        if (EqualityComparer<T>.Default.Equals(field, value))
        {
            return;
        }

        field = value;
        PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
    }
}
