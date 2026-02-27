namespace XDockCertSync.Core.Interfaces;

public interface ICredentialStore
{
    Task SavePasswordAsync(string accountKey, string password, CancellationToken cancellationToken = default);

    Task<string?> LoadPasswordAsync(string accountKey, CancellationToken cancellationToken = default);
}
