using XDockCertSync.Core.Models;

namespace XDockCertSync.Core.Interfaces;

public interface ICertificateRepository
{
    Task<bool> SaveIfNewAsync(CertificateRecord record, CancellationToken cancellationToken = default);

    Task<IReadOnlyCollection<CertificateRecord>> QueryAsync(CertificateQueryFilter filter, CancellationToken cancellationToken = default);

    Task<IReadOnlyCollection<CertificateRecord>> GetAllAsync(CancellationToken cancellationToken = default);
}
