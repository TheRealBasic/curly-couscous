# X-dock 6500 Integration Contract (based on Dräger X-dock 5300/6300/6600 docs)

## Scope and source set
- I could not find vendor documentation for a product explicitly named **"X-dock 6500"**.
- The vendor family docs available are for **Dräger X-dock 5300/6300/6600** and **X-dock Manager**; this contract is based on those.
- Source PDF used: `research/xdock-manager.pdf` (Dräger X-dock Manager Software).
- Source PDF used: `research/xdock-faq.pdf` (Dräger X-dock Frequently Asked Questions).
- Supplementary release-note transcription used: `research/release-notes.txt`.

## Evidence extracted from vendor docs
1. **Network model in vendor docs**
   - "network-connected Dräger X-dock stations send data to the X-dock Manager server".
   - "Data from non-connected Dräger X-dock stations can be transferred using a USB thumb drive".
   - "With the simplest installation variant ... enter the IP of the computer/server ... no firewall blocks the data communication".

2. **Certificate/report generation in vendor docs**
   - X-dock Manager keeps "comprehensive calibration certificates".
   - If not using X-dock Manager: "When logged in, all available certificates and datalogger can be copied onto the stick via the menu".
   - Release notes: "The station can independently generate a PDF. The X-dock Manager can also generate PDFs from the database".

3. **What is NOT documented in retrieved vendor sources**
   - No REST/SOAP/API endpoint is documented.
   - No FTP/SMB export path is documented.
   - No OPC interface is documented.
   - No XML/CSV certificate-export endpoint is documented.
   - No token/session authentication mechanism is described for network retrieval.

---

## 1-page integration contract

### Endpoint(s) / export location
- **Ethernet-accessible interface (documented):**
  - X-dock station(s) -> **X-dock Manager Server** (push of test data over LAN to manager server).
- **Certificate retrieval interfaces (documented):**
  - In X-dock Manager: generate/view reports and calibration certificates from database.
  - On standalone station: copy certificates/datalogger to **USB** while logged in.
- **No documented pull endpoint** (HTTP API/FTP/SMB/OPC) for direct certificate download from station.

### Auth method
- **Station local export (USB):** requires operator to be "logged in" on station UI.
- **X-dock Manager / server comms:** docs mention IP/server/firewall configuration and Windows/SQL-backed manager operation, but retrieved docs do **not** specify token/session API auth.
- **Conclusion:** authentication appears role/login based in UI/software, not tokenized API auth.

### Data format
- **Certificates/reports:** PDF supported (station-generated and manager-generated).
- **Datalogger:** export/readout supported; FAQ mentions converting with CC Vision to text file.
- **No documented XML/CSV certificate feed** in retrieved vendor docs.

### Error codes / failure behavior
- No protocol-level error-code catalog found in retrieved docs.
- Documented failure-related behavior in text:
  - Communication can fail if firewall blocks data communication.
  - Auto-repair/adjustment behavior exists for failed bump tests, but this is device-test behavior, not network API codes.

### Polling limits / rate restrictions
- No network polling/rate-limit contract found in retrieved docs.
- Architecture described is **push to manager server** + UI/report retrieval, rather than high-frequency pull API polling.

### Pull vs push determination (certificate retrieval)
- **Primary Ethernet mechanism is push-based**: station sends test data to X-dock Manager server.
- Certificate access is then through manager software/database reporting.
- Standalone fallback is manual USB export.
- Therefore, certificate retrieval is **not documented as pull from a station endpoint**.

---

## Validation status (real round-trip on Windows 11 network)
- Requested validation ("one real detector certificate round-trip on Windows 11 network") could not be executed in this container because no Windows 11 host, X-dock hardware, detector, or reachable X-dock Manager instance is attached.
- Result: **not executed in this environment**.

## Exact answer to "which Ethernet-accessible interface exists for certificate retrieval?"
- Based on retrieved vendor docs, the only Ethernet path described is:
  - **X-dock station -> X-dock Manager server (push ingestion)**
  - Then certificate/report generation within X-dock Manager.
- A direct Ethernet pull interface (API/FTP/SMB/OPC endpoint on station for certificate export) is **not documented** in the collected sources.
