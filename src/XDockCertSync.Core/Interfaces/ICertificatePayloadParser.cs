using XDockCertSync.Core.Models;

namespace XDockCertSync.Core.Interfaces;

public interface ICertificatePayloadParser
{
    CertificateImportDto Parse(string rawPayload);
}
