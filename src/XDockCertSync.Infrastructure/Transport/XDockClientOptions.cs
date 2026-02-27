namespace XDockCertSync.Infrastructure.Transport;

public sealed class XDockClientOptions
{
    public int MaxRetryAttempts { get; set; } = 4;

    public int InitialBackoffMilliseconds { get; set; } = 500;

    public int RequestTimeoutSeconds { get; set; } = 20;
}
