namespace XDockCertSync.Core.Models;

public sealed class CertificateRecord
{
    public required string DeviceId { get; init; }

    public required DateTimeOffset Timestamp { get; init; }

    public required string GasType { get; init; }

    public required bool Passed { get; init; }

    public required string CertificateFilePath { get; init; }

    public required string CertificateHash { get; init; }
}
