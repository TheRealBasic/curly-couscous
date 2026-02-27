using XDockCertSync.Core.Models;

namespace XDockCertSync.Core.Interfaces;

public interface ICertificateImportPipeline
{
    Task<ImportPipelineResult> ImportRawPayloadAsync(string rawPayload, CancellationToken cancellationToken = default);
}
