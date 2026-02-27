namespace XDockCertSync.App.Models;

public sealed class SyncSettings
{
    public string Hostname { get; set; } = "";

    public string Username { get; set; } = "";

    public string Password { get; set; } = "";

    public int PollingIntervalSeconds { get; set; } = 300;

    public string OutputDirectory { get; set; } = "";
}
