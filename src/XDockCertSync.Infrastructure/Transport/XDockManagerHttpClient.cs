using System.Net;
using System.Net.Http.Json;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.Infrastructure.Transport;

/// <summary>
/// Adapter for pulling certificate payload stubs from an X-dock Manager style HTTP endpoint.
/// Discovery shows station-to-manager push as the documented path; this class targets the manager side.
/// </summary>
public sealed class XDockManagerHttpClient(HttpClient httpClient, XDockClientOptions options) : IXDockClient
{
    public async Task<IReadOnlyCollection<string>> RetrieveRawCertificatePayloadsAsync(CancellationToken cancellationToken = default)
    {
        Exception? lastException = null;

        for (var attempt = 1; attempt <= options.MaxRetryAttempts; attempt++)
        {
            cancellationToken.ThrowIfCancellationRequested();

            using var timeoutCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeoutCts.CancelAfter(TimeSpan.FromSeconds(options.RequestTimeoutSeconds));

            try
            {
                var payloads = await httpClient.GetFromJsonAsync<List<string>>("api/certificates/payloads", timeoutCts.Token)
                    .ConfigureAwait(false);

                return payloads ?? [];
            }
            catch (OperationCanceledException ex) when (!cancellationToken.IsCancellationRequested)
            {
                lastException = new XDockConnectivityException(ConnectivityState.Timeout, "The XDock endpoint timed out.", ex);
            }
            catch (HttpRequestException ex) when (ex.StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden)
            {
                throw new XDockConnectivityException(ConnectivityState.AuthFailed, "Authentication failed. Verify username and password.", ex);
            }
            catch (HttpRequestException ex)
            {
                lastException = new XDockConnectivityException(ConnectivityState.Unavailable, "The XDock endpoint is unavailable.", ex);
            }

            if (attempt < options.MaxRetryAttempts)
            {
                var delay = TimeSpan.FromMilliseconds(options.InitialBackoffMilliseconds * Math.Pow(2, attempt - 1));
                await Task.Delay(delay, cancellationToken).ConfigureAwait(false);
            }
        }

        throw lastException as XDockConnectivityException
              ?? new XDockConnectivityException(ConnectivityState.Unavailable, "Unable to reach the XDock endpoint.");
    }
}
