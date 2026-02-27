namespace XDockCertSync.Core.Models;

public sealed class CertificateImportDto
{
    public required string DeviceId { get; init; }

    public required DateTimeOffset Timestamp { get; init; }

    public required string GasType { get; init; }

    public required bool Passed { get; init; }

    public string CertificateFilePath { get; init; } = string.Empty;
}
