using System.Security.Cryptography;
using System.Text;
using XDockCertSync.Core.Interfaces;

namespace XDockCertSync.Persistence;

public sealed class WindowsDpapiCredentialStore(string secretsDirectory) : ICredentialStore
{
    public async Task SavePasswordAsync(string accountKey, string password, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        Directory.CreateDirectory(secretsDirectory);

        var payload = Encoding.UTF8.GetBytes(password);
        var encrypted = ProtectedData.Protect(payload, Encoding.UTF8.GetBytes(accountKey), DataProtectionScope.CurrentUser);
        var path = ResolvePath(accountKey);
        await File.WriteAllBytesAsync(path, encrypted, cancellationToken).ConfigureAwait(false);
    }

    public async Task<string?> LoadPasswordAsync(string accountKey, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var path = ResolvePath(accountKey);
        if (!File.Exists(path))
        {
            return null;
        }

        var encrypted = await File.ReadAllBytesAsync(path, cancellationToken).ConfigureAwait(false);
        var decrypted = ProtectedData.Unprotect(encrypted, Encoding.UTF8.GetBytes(accountKey), DataProtectionScope.CurrentUser);
        return Encoding.UTF8.GetString(decrypted);
    }

    private string ResolvePath(string accountKey)
    {
        var safe = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(accountKey)));
        return Path.Combine(secretsDirectory, $"{safe}.bin");
    }
}
