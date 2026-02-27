using System.Net.Http.Json;
using XDockCertSync.Core.Interfaces;

namespace XDockCertSync.Infrastructure.Transport;

/// <summary>
/// Adapter for pulling certificate payload stubs from an X-dock Manager style HTTP endpoint.
/// Discovery shows station-to-manager push as the documented path; this class targets the manager side.
/// </summary>
public sealed class XDockManagerHttpClient(HttpClient httpClient) : IXDockClient
{
    public async Task<IReadOnlyCollection<string>> RetrieveRawCertificatePayloadsAsync(CancellationToken cancellationToken = default)
    {
        var payloads = await httpClient.GetFromJsonAsync<List<string>>("api/certificates/payloads", cancellationToken)
            .ConfigureAwait(false);

        return payloads ?? [];
    }
}
