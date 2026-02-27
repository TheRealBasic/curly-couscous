using XDockCertSync.Core.Models;

namespace XDockCertSync.Core.Interfaces;

public interface ICertificateExportService
{
    Task<string> ExportCsvAsync(IReadOnlyCollection<CertificateRecord> records, string outputDirectory, CancellationToken cancellationToken = default);

    Task<string> ExportPdfSummaryAsync(IReadOnlyCollection<CertificateRecord> records, string outputDirectory, CancellationToken cancellationToken = default);
}
