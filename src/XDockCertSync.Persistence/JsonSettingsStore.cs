using System.Text.Json;
using XDockCertSync.Core.Interfaces;

namespace XDockCertSync.Persistence;

public sealed class JsonSettingsStore<TSettings>(string settingsFilePath) : ISettingsStore<TSettings>
    where TSettings : class, new()
{
    private static readonly JsonSerializerOptions SerializerOptions = new() { WriteIndented = true };

    public async Task<TSettings> LoadAsync(CancellationToken cancellationToken = default)
    {
        if (!File.Exists(settingsFilePath))
        {
            return new TSettings();
        }

        await using var stream = File.OpenRead(settingsFilePath);
        var settings = await JsonSerializer.DeserializeAsync<TSettings>(stream, cancellationToken: cancellationToken)
            .ConfigureAwait(false);

        return settings ?? new TSettings();
    }

    public async Task SaveAsync(TSettings settings, CancellationToken cancellationToken = default)
    {
        await using var stream = File.Create(settingsFilePath);
        await JsonSerializer.SerializeAsync(stream, settings, SerializerOptions, cancellationToken).ConfigureAwait(false);
    }
}
