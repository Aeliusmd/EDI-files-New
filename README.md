# EDI 835 Converter

FastAPI and Next.js application for parsing X12 835 Electronic Remittance
Advice (ERA) files, reviewing claim and service-line data, exporting results,
and integrating ERA data with internal systems.

## Features

- Upload `.835`, `.edi`, or `.txt` ERA files
- Readable claim/service-line table and normalized JSON output
- JSON, CSV, and Excel exports
- Optional MySQL persistence for manually uploaded files
- Automatic SFTP polling for Matrix and DMS accounts
- MongoDB storage with duplicate protection
- Billing API enrichment by claim ID and service date
- CARC adjustment-code descriptions
- JWT access and refresh tokens for external ERA lookup
- Rate limiting, refresh-token revocation, and audit logging
- Configurable ports and IIS reverse-proxy support

## Project structure

```text
edi-835-converter/
|-- backend/              FastAPI application, parser, auth, and persistence
|-- frontend/             Next.js user interface
|-- pipeline/             SFTP ingestion, billing lookup, and MongoDB storage
|-- scripts/              Windows start, stop, import, and data-generation tools
|-- SQL/                  Database creation scripts
|-- sample-files/         Redacted sample EDI files
|-- deploy.env.example    Backend and frontend port template
`-- web.config            IIS reverse-proxy configuration
```

The local `docs/`, `downloads/`, `logs/`, environment files, dependencies, and
generated exports are intentionally excluded from Git.

## Requirements

- Python 3.10 or later
- Node.js 18 or later
- npm
- PowerShell 5.1 or later for the start/stop scripts
- MongoDB for SFTP ingestion and external ERA lookup
- MySQL only when `/api/edi/save` is required
- IIS URL Rewrite and ARR only when hosting behind IIS

## Initial setup

### 1. Backend

From the repository root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
cd ..
```

Edit `backend/.env` for the services used in your environment. Never commit
this file.

Important settings:

```env
# Optional manual-save database
# MYSQL_URL=mysql+pymysql://user:password@localhost:3306/edi_835_converter

# JWT authentication
JWT_SECRET=replace_with_a_long_random_secret
JWT_CLIENTS=outside_team:replace_with_a_client_secret
JWT_EXPIRE_SECONDS=3600
JWT_REFRESH_EXPIRE_SECONDS=86400

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DB=edi_835
MONGO_COLLECTION=era_payments
MONGO_REFRESH_COLLECTION=auth_refresh_tokens
MONGO_TRACKER_COLLECTION=pipeline_tracker

# SFTP pipeline
SFTP_HOST=Secure.edidrop.com
SFTP_PORT=522
SFTP_REMOTE_PATH=/837P/OUT/
SFTP_POLL_INTERVAL_SECONDS=60
SFTP_MATRIX_USER=
SFTP_MATRIX_PASS=
SFTP_DMS_USER=
SFTP_DMS_PASS=

# Billing API enrichment
BILLING_API_ENABLED=true
BILLING_API_BASE_URL=http://localhost/api/BillingManagement/Billing
BILLING_API_TIMEOUT=15
BILLING_API_RETRIES=2
BILLING_API_BREAKER_THRESHOLD=5
BILLING_API_BREAKER_COOLDOWN_SECONDS=60
```

If SFTP credentials are left empty, the poller skips those accounts.

### 2. Frontend

```powershell
cd frontend
npm install
npm run build
Copy-Item .env.local.example .env.local
cd ..
```

Normally `NEXT_PUBLIC_API_BASE_URL` should remain empty. The Next.js server
proxies `/api/*` requests to the backend.

### 3. Ports

```powershell
Copy-Item deploy.env.example deploy.env
```

Edit the local `deploy.env` when different ports are needed:

```env
BACKEND_PORT=7007
FRONTEND_PORT=7008
```

## Run the application

For the normal Windows/production-style startup:

```powershell
.\scripts\start.ps1
```

This command:

- reads ports from `deploy.env`
- regenerates `web.config`
- starts FastAPI and the SFTP poller
- starts the built Next.js application
- writes runtime output under `logs/`
- checks backend health before reporting success

Open:

- Frontend: `http://localhost:7008`
- Backend: `http://localhost:7007`
- Swagger UI: `http://localhost:7007/docs`

Use the ports configured in `deploy.env` if they differ from the defaults.

Stop both services:

```powershell
.\scripts\stop.ps1
```

## Development mode

Run the backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 7007
```

Run the frontend in another terminal:

```powershell
cd frontend
npm run dev -- --port 7008
```

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Backend health and enabled endpoints |
| `POST` | `/api/edi/parse` | Parse an uploaded ERA file |
| `POST` | `/api/edi/export/json` | Export normalized JSON |
| `POST` | `/api/edi/export/csv` | Export claim/service-line CSV |
| `POST` | `/api/edi/export/excel` | Export an Excel workbook |
| `POST` | `/api/edi/save` | Save parsed data to optional MySQL |
| `POST` | `/api/auth/token` | Issue JWT access and refresh tokens |
| `POST` | `/api/auth/refresh` | Rotate a refresh token |
| `GET` | `/api/era/lookup?trace_number=...` | Find stored ERA data by trace number |

### Parse a file

```powershell
curl.exe -X POST "http://localhost:7007/api/edi/parse" `
  -F "file=@sample-files/sample-redacted.835"
```

### Authenticate and look up an ERA

Request tokens:

```http
POST /api/auth/token
Content-Type: application/json

{
  "client_id": "outside_team",
  "client_secret": "configured_client_secret"
}
```

Use the returned access token:

```http
GET /api/era/lookup?trace_number=1234567890
Authorization: Bearer <access_token>
```

Refresh tokens are rotated on use. The old token becomes invalid, and expired
token records are removed from MongoDB by a TTL index.

## Pipeline behavior

The backend starts the pipeline poller during application startup. On each
polling cycle it:

1. checks configured Matrix and DMS SFTP accounts
2. downloads new EDI files into the ignored local `downloads/` directory
3. parses each ERA into normalized data
4. enriches claim data through the Billing API when enabled
5. saves the result to MongoDB
6. records processing state to prevent duplicate work

For a one-time import of every supported EDI file in a local folder:

```powershell
python scripts/import_local.py path\to\edi-folder
```

## Optional MySQL setup

The application works without MySQL unless manual upload persistence is
required. Create the database objects using the scripts under `SQL/` or the
legacy `backend/mysql_schema.sql`, then set `MYSQL_URL` in `backend/.env`.

## Security and production notes

- Keep `backend/.env` and `deploy.env` out of Git.
- Replace every example secret before deployment.
- Use HTTPS at the public reverse proxy.
- Restrict MongoDB, MySQL, SFTP, and Billing API access to trusted networks.
- Review audit logs without recording raw PHI.
- The parser handles common 835 segments but is not a complete
  HIPAA 005010X221A1 compliance validator.

## Troubleshooting

- Check `logs/backend.log` and `logs/frontend.log`.
- Run `npm run build` again after frontend changes.
- Confirm MongoDB is reachable when JWT lookup or the pipeline is enabled.
- Confirm `deploy.env` exists before running `scripts/start.ps1`.
- If ports are busy, run `scripts/stop.ps1` or change the port values.
