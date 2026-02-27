using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using Serilog;
using XDockCertSync.App.Models;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.App.ViewModels;

public sealed class SettingsViewModel : INotifyPropertyChanged
{
    private readonly ISettingsStore<SyncSettings> _settingsStore;
    private readonly IXDockClient _xDockClient;
    private readonly ICertificateImportPipeline _importPipeline;
    private readonly ICertificateRepository _repository;
    private readonly ICertificateExportService _exportService;
    private readonly ILogger _logger;

    public SettingsViewModel(
        ISettingsStore<SyncSettings> settingsStore,
        IXDockClient xDockClient,
        ICertificateImportPipeline importPipeline,
        ICertificateRepository repository,
        ICertificateExportService exportService,
        ILogger logger)
    {
        _settingsStore = settingsStore;
        _xDockClient = xDockClient;
        _importPipeline = importPipeline;
        _repository = repository;
        _exportService = exportService;
        _logger = logger;

        SaveCommand = new RelayCommand(SaveAsync);
        ImportNowCommand = new RelayCommand(ImportNowAsync);
        ApplyFiltersCommand = new RelayCommand(ApplyFiltersAsync);
        ExportCsvCommand = new RelayCommand(ExportCsvAsync);
        ExportPdfSummaryCommand = new RelayCommand(ExportPdfSummaryAsync);
    }

    private string _hostname = string.Empty;
    private string _username = string.Empty;
    private string _password = string.Empty;
    private int _pollingIntervalSeconds = 300;
    private string _outputDirectory = string.Empty;
    private string _statusMessage = "Configure connection settings then save.";
    private string _filterDetectorSerial = string.Empty;
    private string _filterDateFrom = string.Empty;
    private string _filterDateTo = string.Empty;
    private string _filterGasType = string.Empty;
    private string _filterPassFail = "All";

    public string Hostname { get => _hostname; set => SetField(ref _hostname, value); }
    public string Username { get => _username; set => SetField(ref _username, value); }
    public string Password { get => _password; set => SetField(ref _password, value); }
    public int PollingIntervalSeconds { get => _pollingIntervalSeconds; set => SetField(ref _pollingIntervalSeconds, value); }
    public string OutputDirectory { get => _outputDirectory; set => SetField(ref _outputDirectory, value); }
    public string StatusMessage { get => _statusMessage; set => SetField(ref _statusMessage, value); }

    public string FilterDetectorSerial { get => _filterDetectorSerial; set => SetField(ref _filterDetectorSerial, value); }
    public string FilterDateFrom { get => _filterDateFrom; set => SetField(ref _filterDateFrom, value); }
    public string FilterDateTo { get => _filterDateTo; set => SetField(ref _filterDateTo, value); }
    public string FilterGasType { get => _filterGasType; set => SetField(ref _filterGasType, value); }
    public string FilterPassFail { get => _filterPassFail; set => SetField(ref _filterPassFail, value); }
    public IReadOnlyList<string> PassFailOptions { get; } = ["All", "Pass", "Fail"];

    public ObservableCollection<CertificateRecord> Records { get; } = [];

    public RelayCommand SaveCommand { get; }
    public RelayCommand ImportNowCommand { get; }
    public RelayCommand ApplyFiltersCommand { get; }
    public RelayCommand ExportCsvCommand { get; }
    public RelayCommand ExportPdfSummaryCommand { get; }

    public event PropertyChangedEventHandler? PropertyChanged;

    public async Task LoadAsync()
    {
        var settings = await _settingsStore.LoadAsync().ConfigureAwait(true);
        Hostname = settings.Hostname;
        Username = settings.Username;
        Password = settings.Password;
        PollingIntervalSeconds = settings.PollingIntervalSeconds;
        OutputDirectory = settings.OutputDirectory;
        await ApplyFiltersAsync().ConfigureAwait(true);
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

    private async Task ImportNowAsync()
    {
        var payloads = await _xDockClient.RetrieveRawCertificatePayloadsAsync().ConfigureAwait(true);
        var imported = 0;
        var duplicates = 0;

        foreach (var payload in payloads)
        {
            var result = await _importPipeline.ImportRawPayloadAsync(payload).ConfigureAwait(true);
            if (result.Imported)
            {
                imported++;
            }
            else
            {
                duplicates++;
            }
        }

        await ApplyFiltersAsync().ConfigureAwait(true);
        StatusMessage = $"Import complete. New: {imported}, duplicates skipped: {duplicates}.";
    }

    private async Task ApplyFiltersAsync()
    {
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

        var records = await _repository.QueryAsync(filter).ConfigureAwait(true);
        Records.Clear();
        foreach (var record in records)
        {
            Records.Add(record);
        }
    }

    private async Task ExportCsvAsync()
    {
        var path = await _exportService.ExportCsvAsync(Records.ToList(), ResolveOutputDirectory()).ConfigureAwait(true);
        StatusMessage = $"CSV exported: {path}";
    }

    private async Task ExportPdfSummaryAsync()
    {
        var path = await _exportService.ExportPdfSummaryAsync(Records.ToList(), ResolveOutputDirectory()).ConfigureAwait(true);
        StatusMessage = $"PDF summary exported: {path}";
    }

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
