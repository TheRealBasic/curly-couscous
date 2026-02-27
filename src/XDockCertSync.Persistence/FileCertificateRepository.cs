using System.Text.Json;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.Persistence;

public sealed class FileCertificateRepository(string databaseFilePath) : ICertificateRepository
{
    private static readonly JsonSerializerOptions SerializerOptions = new() { WriteIndented = true };

    public async Task SaveAsync(CertificateRecord record, CancellationToken cancellationToken = default)
    {
        var existing = (await GetAllAsync(cancellationToken).ConfigureAwait(false)).ToList();
        existing.Add(record);

        await using var stream = File.Create(databaseFilePath);
        await JsonSerializer.SerializeAsync(stream, existing, SerializerOptions, cancellationToken).ConfigureAwait(false);
    }

    public async Task<IReadOnlyCollection<CertificateRecord>> GetAllAsync(CancellationToken cancellationToken = default)
    {
        if (!File.Exists(databaseFilePath))
        {
            return [];
        }

        await using var stream = File.OpenRead(databaseFilePath);
        var records = await JsonSerializer.DeserializeAsync<List<CertificateRecord>>(stream, cancellationToken: cancellationToken)
            .ConfigureAwait(false);

        return records ?? [];
    }
}
