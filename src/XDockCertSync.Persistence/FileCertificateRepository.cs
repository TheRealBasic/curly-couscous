using Microsoft.Data.Sqlite;
using XDockCertSync.Core.Interfaces;
using XDockCertSync.Core.Models;

namespace XDockCertSync.Persistence;

public sealed class SqliteCertificateRepository(string databaseFilePath) : ICertificateRepository
{
    private readonly string _connectionString = new SqliteConnectionStringBuilder { DataSource = databaseFilePath }.ToString();

    public async Task<bool> SaveIfNewAsync(CertificateRecord record, CancellationToken cancellationToken = default)
    {
        await EnsureSchemaAsync(cancellationToken).ConfigureAwait(false);

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);

        var command = connection.CreateCommand();
        command.CommandText = @"
INSERT INTO certificates(device_id, cert_timestamp_utc, gas_type, passed, certificate_file_path, certificate_hash)
VALUES ($deviceId, $timestamp, $gasType, $passed, $filePath, $hash)
ON CONFLICT(device_id, cert_timestamp_utc, certificate_hash) DO NOTHING;";
        command.Parameters.AddWithValue("$deviceId", record.DeviceId);
        command.Parameters.AddWithValue("$timestamp", record.Timestamp.UtcDateTime.ToString("O"));
        command.Parameters.AddWithValue("$gasType", record.GasType);
        command.Parameters.AddWithValue("$passed", record.Passed ? 1 : 0);
        command.Parameters.AddWithValue("$filePath", record.CertificateFilePath);
        command.Parameters.AddWithValue("$hash", record.CertificateHash);

        var affected = await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
        return affected > 0;
    }

    public Task<IReadOnlyCollection<CertificateRecord>> GetAllAsync(CancellationToken cancellationToken = default)
        => QueryAsync(new CertificateQueryFilter(), cancellationToken);

    public async Task<IReadOnlyCollection<CertificateRecord>> QueryAsync(CertificateQueryFilter filter, CancellationToken cancellationToken = default)
    {
        await EnsureSchemaAsync(cancellationToken).ConfigureAwait(false);

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);

        var where = new List<string>();
        var command = connection.CreateCommand();

        if (!string.IsNullOrWhiteSpace(filter.DetectorSerial))
        {
            where.Add("device_id = $deviceId");
            command.Parameters.AddWithValue("$deviceId", filter.DetectorSerial);
        }

        if (filter.From is not null)
        {
            where.Add("cert_timestamp_utc >= $from");
            command.Parameters.AddWithValue("$from", filter.From.Value.UtcDateTime.ToString("O"));
        }

        if (filter.To is not null)
        {
            where.Add("cert_timestamp_utc <= $to");
            command.Parameters.AddWithValue("$to", filter.To.Value.UtcDateTime.ToString("O"));
        }

        if (filter.Passed is not null)
        {
            where.Add("passed = $passed");
            command.Parameters.AddWithValue("$passed", filter.Passed.Value ? 1 : 0);
        }

        if (!string.IsNullOrWhiteSpace(filter.GasType))
        {
            where.Add("gas_type = $gasType");
            command.Parameters.AddWithValue("$gasType", filter.GasType);
        }

        var whereClause = where.Count > 0 ? $"WHERE {string.Join(" AND ", where)}" : string.Empty;

        command.CommandText = $@"
SELECT device_id, cert_timestamp_utc, gas_type, passed, certificate_file_path, certificate_hash
FROM certificates
{whereClause}
ORDER BY cert_timestamp_utc DESC;";

        var results = new List<CertificateRecord>();
        await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            results.Add(new CertificateRecord
            {
                DeviceId = reader.GetString(0),
                Timestamp = DateTimeOffset.Parse(reader.GetString(1)),
                GasType = reader.GetString(2),
                Passed = reader.GetInt32(3) == 1,
                CertificateFilePath = reader.GetString(4),
                CertificateHash = reader.GetString(5)
            });
        }

        return results;
    }

    private async Task EnsureSchemaAsync(CancellationToken cancellationToken)
    {
        var directory = Path.GetDirectoryName(databaseFilePath);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        await using var connection = new SqliteConnection(_connectionString);
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
        var command = connection.CreateCommand();
        command.CommandText = @"
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    cert_timestamp_utc TEXT NOT NULL,
    gas_type TEXT NOT NULL,
    passed INTEGER NOT NULL,
    certificate_file_path TEXT NOT NULL,
    certificate_hash TEXT NOT NULL,
    UNIQUE(device_id, cert_timestamp_utc, certificate_hash)
);";

        await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
    }
}
