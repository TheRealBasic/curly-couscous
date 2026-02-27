using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Net.Http;
using System.Runtime.CompilerServices;
using Serilog;
using XDockCertSync.App.Models;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;
using XDockCertSync.Infrastructure.Transport;

namespace XDockCertSync.App.ViewModels;

public sealed class SettingsViewModel : INotifyPropertyChanged
{
    private readonly ISettingsStore<SyncSettings> _settingsStore;
    private readonly ICredentialStore _credentialStore;
    private readonly IXDockClient _xDockClient;
    private readonly ICertificateImportPipeline _importPipeline;
    private readonly ICertificateRepository _repository;
    private readonly ICertificateExportService _exportService;
    private readonly ILogger _logger;
    private readonly HttpClient _httpClient;
    private readonly XDockClientOptions _clientOptions;
    private readonly SemaphoreSlim _syncGate = new(1, 1);

    private CancellationTokenSource? _pollingCts;

    public SettingsViewModel(
        ISettingsStore<SyncSettings> settingsStore,
        ICredentialStore credentialStore,
        IXDockClient xDockClient,
        ICertificateImportPipeline importPipeline,
        ICertificateRepository repository,
        ICertificateExportService exportService,
        ILogger logger,
        HttpClient httpClient,
        XDockClientOptions clientOptions)
    {
        _settingsStore = settingsStore;
        _credentialStore = credentialStore;
        _xDockClient = xDockClient;
        _importPipeline = importPipeline;
        _repository = repository;
        _exportService = exportService;
        _logger = logger;
        _httpClient = httpClient;
        _clientOptions = clientOptions;

        SaveCommand = new RelayCommand(SaveAsync);
        ManualSyncNowCommand = new RelayCommand(() => SyncNowAsync(true));
        ApplyFiltersCommand = new RelayCommand(ApplyFiltersAsync);
        ExportCsvCommand = new RelayCommand(ExportCsvAsync);
        ExportPdfSummaryCommand = new RelayCommand(ExportPdfSummaryAsync);
    }

    private string _hostname = string.Empty;
    private string _username = string.Empty;
    private string _password = string.Empty;
    private int _pollingIntervalSeconds = 300;
    private int _requestTimeoutSeconds = 20;
    private int _maxRetryAttempts = 4;
    private int _initialBackoffMilliseconds = 500;
    private bool _autoSyncEnabled = true;
    private string _outputDirectory = string.Empty;
    private string _statusMessage = "Configure connection settings then save.";
    private ConnectivityState _connectivityState = ConnectivityState.Unavailable;
    private string _filterDetectorSerial = string.Empty;
    private string _filterDateFrom = string.Empty;
    private string _filterDateTo = string.Empty;
    private string _filterGasType = string.Empty;
    private string _filterPassFail = "All";

    public string Hostname { get => _hostname; set => SetField(ref _hostname, value); }
    public string Username { get => _username; set => SetField(ref _username, value); }
    public string Password { get => _password; set => SetField(ref _password, value); }
    public int PollingIntervalSeconds { get => _pollingIntervalSeconds; set => SetField(ref _pollingIntervalSeconds, value); }
    public int RequestTimeoutSeconds { get => _requestTimeoutSeconds; set => SetField(ref _requestTimeoutSeconds, value); }
    public int MaxRetryAttempts { get => _maxRetryAttempts; set => SetField(ref _maxRetryAttempts, value); }
    public int InitialBackoffMilliseconds { get => _initialBackoffMilliseconds; set => SetField(ref _initialBackoffMilliseconds, value); }
    public bool AutoSyncEnabled { get => _autoSyncEnabled; set => SetField(ref _autoSyncEnabled, value); }
    public string OutputDirectory { get => _outputDirectory; set => SetField(ref _outputDirectory, value); }
    public string StatusMessage { get => _statusMessage; set => SetField(ref _statusMessage, value); }
    public ConnectivityState ConnectivityState { get => _connectivityState; set => SetField(ref _connectivityState, value); }

    public string FilterDetectorSerial { get => _filterDetectorSerial; set => SetField(ref _filterDetectorSerial, value); }
    public string FilterDateFrom { get => _filterDateFrom; set => SetField(ref _filterDateFrom, value); }
    public string FilterDateTo { get => _filterDateTo; set => SetField(ref _filterDateTo, value); }
    public string FilterGasType { get => _filterGasType; set => SetField(ref _filterGasType, value); }
    public string FilterPassFail { get => _filterPassFail; set => SetField(ref _filterPassFail, value); }
    public IReadOnlyList<string> PassFailOptions { get; } = ["All", "Pass", "Fail"];

    public ObservableCollection<CertificateRecord> Records { get; } = [];

    public RelayCommand SaveCommand { get; }
    public RelayCommand ManualSyncNowCommand { get; }
    public RelayCommand ApplyFiltersCommand { get; }
    public RelayCommand ExportCsvCommand { get; }
    public RelayCommand ExportPdfSummaryCommand { get; }

    public event PropertyChangedEventHandler? PropertyChanged;

    public async Task LoadAsync()
    {
        using var cts = CreateIoCancellationToken();
        var settings = await _settingsStore.LoadAsync(cts.Token).ConfigureAwait(true);
        Hostname = settings.Hostname;
        Username = settings.Username;
        PollingIntervalSeconds = settings.PollingIntervalSeconds;
        RequestTimeoutSeconds = settings.RequestTimeoutSeconds;
        MaxRetryAttempts = settings.MaxRetryAttempts;
        InitialBackoffMilliseconds = settings.InitialBackoffMilliseconds;
        AutoSyncEnabled = settings.AutoSyncEnabled;
        OutputDirectory = settings.OutputDirectory;
        Password = await _credentialStore.LoadPasswordAsync(BuildCredentialKey(), cts.Token).ConfigureAwait(true) ?? string.Empty;

        ApplyRuntimeConnectionSettings();
        await ApplyFiltersAsync().ConfigureAwait(true);
        StartPolling();
    }

    private async Task SaveAsync()
    {
        using var cts = CreateIoCancellationToken();
        var settings = new SyncSettings
        {
            Hostname = Hostname,
            Username = Username,
            PollingIntervalSeconds = PollingIntervalSeconds,
            RequestTimeoutSeconds = RequestTimeoutSeconds,
            MaxRetryAttempts = MaxRetryAttempts,
            InitialBackoffMilliseconds = InitialBackoffMilliseconds,
            AutoSyncEnabled = AutoSyncEnabled,
            OutputDirectory = OutputDirectory
        };

        await _settingsStore.SaveAsync(settings, cts.Token).ConfigureAwait(true);
        await _credentialStore.SavePasswordAsync(BuildCredentialKey(), Password, cts.Token).ConfigureAwait(true);

        ApplyRuntimeConnectionSettings();
        StartPolling();

        StatusMessage = $"Saved at {DateTimeOffset.Now:t}";
        _logger.Information("Settings updated for host {Hostname} with polling interval {PollingIntervalSeconds}s", Hostname, PollingIntervalSeconds);
    }

    private async Task SyncNowAsync(bool manual)
    {
        var correlationId = Guid.NewGuid().ToString("N");
        await _syncGate.WaitAsync().ConfigureAwait(true);

        try
        {
            using var cts = CreateIoCancellationToken();
            _logger.Information("Sync attempt {CorrelationId} started (manual={Manual})", correlationId, manual);
            var payloads = await _xDockClient.RetrieveRawCertificatePayloadsAsync(cts.Token).ConfigureAwait(true);
            var imported = 0;
            var duplicates = 0;

            foreach (var payload in payloads)
            {
                var result = await _importPipeline.ImportRawPayloadAsync(payload, cts.Token).ConfigureAwait(true);
                if (result.Imported)
                {
                    imported++;
                }
                else
                {
                    duplicates++;
                }
            }

            ConnectivityState = ConnectivityState.Connected;
            await ApplyFiltersAsync().ConfigureAwait(true);
            StatusMessage = $"[{correlationId}] Sync complete. New: {imported}, duplicates skipped: {duplicates}.";
            _logger.Information("Sync attempt {CorrelationId} succeeded. Imported={Imported} Duplicate={Duplicates}", correlationId, imported, duplicates);
        }
        catch (XDockConnectivityException ex)
        {
            ConnectivityState = ex.State;
            StatusMessage = $"[{correlationId}] {ex.UserMessage}";
            _logger.Warning(ex, "Sync attempt {CorrelationId} failed with state {State}: {Message}", correlationId, ex.State, ex.UserMessage);
        }
        catch (OperationCanceledException ex)
        {
            ConnectivityState = ConnectivityState.Timeout;
            StatusMessage = $"[{correlationId}] Sync cancelled or timed out.";
            _logger.Warning(ex, "Sync attempt {CorrelationId} cancelled", correlationId);
        }
        catch (Exception ex)
        {
            ConnectivityState = ConnectivityState.Unavailable;
            StatusMessage = $"[{correlationId}] Unexpected sync failure. Check logs for details.";
            _logger.Error(ex, "Sync attempt {CorrelationId} failed unexpectedly", correlationId);
        }
        finally
        {
            _syncGate.Release();
        }
    }

    private async Task ApplyFiltersAsync()
    {
        using var cts = CreateIoCancellationToken();
        var filter = new CertificateQueryFilter
        {
            DetectorSerial = string.IsNullOrWhiteSpace(FilterDetectorSerial) ? null : FilterDetectorSerial,
            GasType = string.IsNullOrWhiteSpace(FilterGasType) ? null : FilterGasType,
            From = DateTimeOffset.TryParse(FilterDateFrom, out var from) ? from : null,
            To = DateTimeOffset.TryParse(FilterDateTo, out var to) ? to : null,
            Passed = FilterPassFail switch
            {
                "Pass" => true,
                "Fail" => false,
                _ => null
            }
        };

        var records = await _repository.QueryAsync(filter, cts.Token).ConfigureAwait(true);
        Records.Clear();
        foreach (var record in records)
        {
            Records.Add(record);
        }
    }

    private async Task ExportCsvAsync()
    {
        using var cts = CreateIoCancellationToken();
        var path = await _exportService.ExportCsvAsync(Records.ToList(), ResolveOutputDirectory(), cts.Token).ConfigureAwait(true);
        StatusMessage = $"CSV exported: {path}";
    }

    private async Task ExportPdfSummaryAsync()
    {
        using var cts = CreateIoCancellationToken();
        var path = await _exportService.ExportPdfSummaryAsync(Records.ToList(), ResolveOutputDirectory(), cts.Token).ConfigureAwait(true);
        StatusMessage = $"PDF summary exported: {path}";
    }

    private void StartPolling()
    {
        _pollingCts?.Cancel();

        if (!AutoSyncEnabled)
        {
            return;
        }

        _pollingCts = new CancellationTokenSource();
        var token = _pollingCts.Token;

        _ = Task.Run(async () =>
        {
            using var timer = new PeriodicTimer(TimeSpan.FromSeconds(Math.Max(5, PollingIntervalSeconds)));
            while (await timer.WaitForNextTickAsync(token).ConfigureAwait(false))
            {
                await SyncNowAsync(false).ConfigureAwait(false);
            }
        }, token);
    }

    private void ApplyRuntimeConnectionSettings()
    {
        if (Uri.TryCreate(Hostname, UriKind.Absolute, out var absoluteUri))
        {
            _httpClient.BaseAddress = absoluteUri;
        }
        else if (!string.IsNullOrWhiteSpace(Hostname))
        {
            _httpClient.BaseAddress = new Uri($"http://{Hostname.TrimEnd('/')}/");
        }

        _clientOptions.MaxRetryAttempts = Math.Max(1, MaxRetryAttempts);
        _clientOptions.InitialBackoffMilliseconds = Math.Max(100, InitialBackoffMilliseconds);
        _clientOptions.RequestTimeoutSeconds = Math.Max(5, RequestTimeoutSeconds);
    }

    private CancellationTokenSource CreateIoCancellationToken()
    {
        var cts = new CancellationTokenSource();
        cts.CancelAfter(TimeSpan.FromSeconds(Math.Max(5, RequestTimeoutSeconds)));
        return cts;
    }

    private string BuildCredentialKey() => $"{Hostname}|{Username}";

    private string ResolveOutputDirectory()
        => string.IsNullOrWhiteSpace(OutputDirectory)
            ? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "XDockCertSync", "exports")
            : OutputDirectory;

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
