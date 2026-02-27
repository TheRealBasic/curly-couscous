using XDockCertSync.Core.Models;

namespace XDockCertSync.Core.Interfaces;

public interface ICertificateRepository
{
    Task SaveAsync(CertificateRecord record, CancellationToken cancellationToken = default);

    Task<IReadOnlyCollection<CertificateRecord>> GetAllAsync(CancellationToken cancellationToken = default);
}
