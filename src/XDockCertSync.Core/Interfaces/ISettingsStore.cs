namespace XDockCertSync.Core.Interfaces;

public interface ISettingsStore<TSettings>
{
    Task<TSettings> LoadAsync(CancellationToken cancellationToken = default);

    Task SaveAsync(TSettings settings, CancellationToken cancellationToken = default);
}
