using XDockCertSync.Core.Models;

namespace XDockCertSync.Core.Interfaces;

public interface ICertificatePayloadParser
{
    CertificateRecord Parse(string rawPayload);
}
