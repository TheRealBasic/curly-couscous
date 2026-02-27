# XDockCertSync

`XDockCertSync` is a Windows desktop tool for syncing X-dock certificate payloads from an HTTP endpoint into a local SQLite database, then filtering and exporting those records for reporting.

## What the program does

- Connects to an X-dock Manager-style endpoint (default base URL: `http://localhost:5000/`).
- Pulls raw certificate payloads from `GET /api/certificates/payloads`.
- Parses and imports payloads into a local SQLite store while skipping duplicates.
- Lets you filter imported records by detector serial, date range, pass/fail status, and gas type.
- Exports filtered results to:
  - CSV (full record export)
  - PDF summary (record count + pass/fail totals)
- Supports manual sync and optional automatic polling sync.

## Requirements

- **OS:** Windows (WPF app targeting `net8.0-windows`)
- **.NET SDK:** .NET 8 SDK (for building/running from source)
- **X-dock endpoint:** Reachable HTTP service that returns a JSON array of raw payload strings at `api/certificates/payloads`

## Install / Build

### Option 1: Run from source (developer workflow)

```bash
git clone <your-repo-url>
cd curly-couscous
dotnet restore XDockCertSync.sln
dotnet build XDockCertSync.sln -c Release
```

Run the app:

```bash
dotnet run --project src/XDockCertSync.App/XDockCertSync.App.csproj -c Release
```

### Option 2: Publish a distributable folder

```bash
dotnet publish src/XDockCertSync.App/XDockCertSync.App.csproj -c Release -r win-x64 --self-contained false -o ./publish/win-x64
```

Then launch `XDockCertSync.App.exe` from `./publish/win-x64`.

## How to use

1. Start the app.
2. Enter connection settings:
   - **IP / Hostname** (for example, `http://localhost:5000/`)
   - **Username** and **Password**
   - Polling interval, timeout, retry/backoff values
   - Output directory for exports
3. Click **Save Settings**.
4. Click **Manual sync now** to fetch and import payloads immediately.
5. Use **Query Filters** to narrow records.
6. Click **Export CSV** or **Export PDF Summary**.

## Data and logs location

The app stores local data under:

- `%LOCALAPPDATA%\XDockCertSync\data\certificates.db` (SQLite database)
- `%LOCALAPPDATA%\XDockCertSync\data\raw\` (raw payload archive)
- `%LOCALAPPDATA%\XDockCertSync\logs\` (rolling logs)
- `%LOCALAPPDATA%\XDockCertSync\settings.json` (saved settings)
- `%LOCALAPPDATA%\XDockCertSync\secrets\` (protected credentials)

## Notes

- Automatic polling can be toggled with **Enable automatic polling**.
- If sync fails, check the status bar message and logs for details (timeouts, auth issues, endpoint unavailable, etc.).
