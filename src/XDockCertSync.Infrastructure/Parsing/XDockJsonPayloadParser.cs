using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.Infrastructure.Parsing;

public sealed class XDockJsonPayloadParser : ICertificatePayloadParser
{
    public CertificateRecord Parse(string rawPayload)
    {
        var document = JsonDocument.Parse(rawPayload);
        var root = document.RootElement;

        var certificatePath = root.GetProperty("certificatePath").GetString() ?? string.Empty;
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(rawPayload)));

        return new CertificateRecord
        {
            DeviceId = root.GetProperty("deviceId").GetString() ?? "unknown",
            Timestamp = root.TryGetProperty("timestamp", out var ts)
                ? ts.GetDateTimeOffset()
                : DateTimeOffset.UtcNow,
            GasType = root.GetProperty("gasType").GetString() ?? "unknown",
            Passed = root.GetProperty("passed").GetBoolean(),
            CertificateFilePath = certificatePath,
            CertificateHash = hash
        };
    }
}
