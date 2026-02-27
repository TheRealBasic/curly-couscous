namespace XDockCertSync.Core.Models;

public sealed class CertificateQueryFilter
{
    public string? DetectorSerial { get; init; }

    public DateTimeOffset? From { get; init; }

    public DateTimeOffset? To { get; init; }

    public bool? Passed { get; init; }

    public string? GasType { get; init; }
}
