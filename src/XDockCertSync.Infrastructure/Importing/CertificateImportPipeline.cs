using System.Security.Cryptography;
using System.Text;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.Infrastructure.Importing;

public sealed class CertificateImportPipeline(
    ICertificatePayloadParser parser,
    ICertificateRepository repository,
    string rawDataDirectory) : ICertificateImportPipeline
{
    public async Task<ImportPipelineResult> ImportRawPayloadAsync(string rawPayload, CancellationToken cancellationToken = default)
    {
        Directory.CreateDirectory(rawDataDirectory);

        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(rawPayload)));
        var artifactPath = Path.Combine(rawDataDirectory, $"{hash}.json");

        if (!File.Exists(artifactPath))
        {
            await File.WriteAllTextAsync(artifactPath, rawPayload, cancellationToken).ConfigureAwait(false);
        }

        var parsed = parser.Parse(rawPayload);

        var record = new CertificateRecord
        {
            DeviceId = parsed.DeviceId,
            Timestamp = parsed.Timestamp,
            GasType = parsed.GasType,
            Passed = parsed.Passed,
            CertificateFilePath = parsed.CertificateFilePath,
            CertificateHash = hash
        };

        var imported = await repository.SaveIfNewAsync(record, cancellationToken).ConfigureAwait(false);

        return new ImportPipelineResult
        {
            Hash = hash,
            RawArtifactPath = artifactPath,
            Imported = imported
        };
    }
}
