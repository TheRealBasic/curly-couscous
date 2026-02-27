namespace XDockCertSync.Core.Interfaces;

public interface IXDockClient
{
    Task<IReadOnlyCollection<string>> RetrieveRawCertificatePayloadsAsync(CancellationToken cancellationToken = default);
}
