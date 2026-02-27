using System.Text;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.Infrastructure.Exporting;

public sealed class CertificateExportService : ICertificateExportService
{
    public async Task<string> ExportCsvAsync(IReadOnlyCollection<CertificateRecord> records, string outputDirectory, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(outputDirectory);
        var path = Path.Combine(outputDirectory, $"certificates-{DateTimeOffset.UtcNow:yyyyMMddHHmmss}.csv");

        var sb = new StringBuilder();
        sb.AppendLine("DeviceId,Timestamp,GasType,Passed,CertificateFilePath,CertificateHash");
        foreach (var record in records)
        {
            sb.AppendLine($"{Escape(record.DeviceId)},{record.Timestamp:O},{Escape(record.GasType)},{record.Passed},{Escape(record.CertificateFilePath)},{record.CertificateHash}");
        }

        await File.WriteAllTextAsync(path, sb.ToString(), cancellationToken).ConfigureAwait(false);
        return path;
    }

    public async Task<string> ExportPdfSummaryAsync(IReadOnlyCollection<CertificateRecord> records, string outputDirectory, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(outputDirectory);
        var path = Path.Combine(outputDirectory, $"certificates-summary-{DateTimeOffset.UtcNow:yyyyMMddHHmmss}.pdf");

        var contentLines = new List<string>
        {
            "Certificate Compliance Summary",
            $"Generated: {DateTimeOffset.Now:O}",
            $"Total Records: {records.Count}",
            $"Pass: {records.Count(x => x.Passed)}",
            $"Fail: {records.Count(x => !x.Passed)}"
        };

        var text = string.Join("\\n", contentLines);
        var escapedText = text.Replace("\\", "\\\\").Replace("(", "\\(").Replace(")", "\\)");
        var stream = $"BT /F1 12 Tf 50 760 Td ({escapedText}) Tj ET";
        var pdf = BuildSinglePagePdf(stream);
        await File.WriteAllBytesAsync(path, pdf, cancellationToken).ConfigureAwait(false);
        return path;
    }

    private static string Escape(string input) => $"\"{input.Replace("\"", "\"\"")}\"";

    private static byte[] BuildSinglePagePdf(string content)
    {
        var objects = new List<string>
        {
            "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj",
            $"4 0 obj << /Length {Encoding.ASCII.GetByteCount(content)} >> stream\n{content}\nendstream endobj",
            "5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj"
        };

        var builder = new StringBuilder();
        builder.AppendLine("%PDF-1.4");

        var offsets = new List<int>();
        foreach (var obj in objects)
        {
            offsets.Add(Encoding.ASCII.GetByteCount(builder.ToString()));
            builder.AppendLine(obj);
        }

        var xrefOffset = Encoding.ASCII.GetByteCount(builder.ToString());
        builder.AppendLine($"xref\n0 {objects.Count + 1}\n0000000000 65535 f ");
        foreach (var offset in offsets)
        {
            builder.AppendLine($"{offset:D10} 00000 n ");
        }

        builder.AppendLine($"trailer << /Size {objects.Count + 1} /Root 1 0 R >>");
        builder.AppendLine($"startxref\n{xrefOffset}\n%%EOF");

        return Encoding.ASCII.GetBytes(builder.ToString());
    }
}
