namespace XDockCertSync.Core.Models;

public sealed class ImportPipelineResult
{
    public required string Hash { get; init; }

    public required string RawArtifactPath { get; init; }

    public required bool Imported { get; init; }
}
