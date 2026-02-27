# gasdock-cert-manager

Offline certificate ingestion and dashboard system for Dräger X-dock 6300 calibration PDFs.

## Features

- Watches `C:\GasDock\Imports` for new PDF certificates.
- Waits for file copy completion (stable size checks).
- Parses certificate data from filename and PDF text:
  - Serial
  - Test date/time
  - Device type
  - Overall result (PASS/FAIL)
- Saves results to SQLite (`C:\GasDock\gasdock.db`).
- Sorts parsed files into:
  - `C:\GasDock\Sorted\<PASS|FAIL|UNKNOWN>\YYYY\MM\DD\SERIAL\`
- Sends failed parses to `C:\GasDock\Quarantine` and records parse errors.
- Hosts local FastAPI dashboard at `http://localhost:8765`.
- CSV export and filtering.
- Manual barcode entry per certificate from the device history page.
- Fully offline and local-file only.

## Project Structure

```text
gasdock-cert-manager/
├── app/
├── templates/
├── static/
├── example_inputs/
├── tests/
├── config.yaml
├── requirements.txt
├── run.py
├── README.md
└── build_exe.spec
```

## Setup

1. Use Python 3.11+
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Review and adjust `config.yaml` if needed.

## Run

```bash
python run.py
```

- Watcher starts automatically.
- Dashboard available on `http://localhost:8765`.

## CSV Export

Use dashboard button or direct URL:

```text
http://localhost:8765/export.csv
```

Supports filters:
- `serial`
- `result`
- `date_from` (YYYY-MM-DD)
- `date_to` (YYYY-MM-DD)

## Tests

```bash
pytest
```

## Build Windows EXE

```bash
pyinstaller build_exe.spec
```

Binary name:
- `gasdock-cert-manager.exe`

## Compliance Notes

- No connection to X-dock hardware.
- No undocumented protocols.
- Local PDF processing only.
- Offline-compatible design.
