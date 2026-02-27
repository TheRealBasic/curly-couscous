namespace XDockCertSync.App.Models;

public sealed class SyncSettings
{
    public string Hostname { get; set; } = "";

    public string Username { get; set; } = "";

    public int PollingIntervalSeconds { get; set; } = 300;

    public int RequestTimeoutSeconds { get; set; } = 20;

    public int MaxRetryAttempts { get; set; } = 4;

    public int InitialBackoffMilliseconds { get; set; } = 500;

    public bool AutoSyncEnabled { get; set; } = true;

    public string OutputDirectory { get; set; } = "";
}
