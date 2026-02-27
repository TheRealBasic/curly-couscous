using System.Text.Json;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.Infrastructure.Parsing;

public sealed class XDockJsonPayloadParser : ICertificatePayloadParser
{
    public CertificateImportDto Parse(string rawPayload)
    {
        var document = JsonDocument.Parse(rawPayload);
        var root = document.RootElement;

        var dto = new CertificateImportDto
        {
            DeviceId = root.TryGetProperty("deviceId", out var deviceId) ? deviceId.GetString() ?? string.Empty : string.Empty,
            Timestamp = root.TryGetProperty("timestamp", out var ts) ? ts.GetDateTimeOffset() : DateTimeOffset.MinValue,
            GasType = root.TryGetProperty("gasType", out var gasType) ? gasType.GetString() ?? string.Empty : string.Empty,
            Passed = root.TryGetProperty("passed", out var passed) && passed.GetBoolean(),
            CertificateFilePath = root.TryGetProperty("certificatePath", out var certPath) ? certPath.GetString() ?? string.Empty : string.Empty
        };

        ValidateRequired(dto);
        return dto;
    }

    private static void ValidateRequired(CertificateImportDto dto)
    {
        if (string.IsNullOrWhiteSpace(dto.DeviceId))
        {
            throw new InvalidDataException("deviceId is required.");
        }

        if (dto.Timestamp == DateTimeOffset.MinValue)
        {
            throw new InvalidDataException("timestamp is required.");
        }

        if (string.IsNullOrWhiteSpace(dto.GasType))
        {
            throw new InvalidDataException("gasType is required.");
        }
    }
}
