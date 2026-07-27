# EDI 835 Converter — FastAPI + Next.js

A working local system to convert **X12 835 Electronic Remittance Advice / ERA** files into:

- Readable table view
- Normalized JSON
- CSV download
- Excel download
- Optional MySQL save

This project is designed for `.835` files such as:

```text
sample-redacted.835
```

---

## 1. Project Structure

```text
edi-835-converter/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI API endpoints
│   │   ├── parser.py        # EDI 835 parser and normalized row builder
│   │   └── db.py            # Optional MySQL save logic
│   ├── requirements.txt
│   ├── mysql_schema.sql
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.jsx         # Main upload/view/download UI
│   │   ├── layout.jsx
│   │   └── globals.css
│   ├── package.json
│   └── .env.local.example
└── sample-files/
    └── sample .835 files
```

---

## 2. Backend Setup

### Requirements

- Python 3.10+
- pip

### Run backend

```bash
cd backend
python -m venv .venv
```

Activate virtual environment:

**Windows PowerShell:**

```bash
.venv\Scripts\Activate.ps1
```

**Windows CMD:**

```bash
.venv\Scripts\activate.bat
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

Start API:

```bash
uvicorn app.main:app --reload --port 7007
```

Backend URL:

```text
http://localhost:7007
```

Swagger API docs:

```text
http://localhost:7007/docs
```

---

## 3. Frontend Setup

### Requirements

- Node.js 18+
- npm

### Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:7008
```

---

## 4. How to Use

1. Start the backend on port `7007`.
2. Start the frontend on port `7008`.
3. Open `http://localhost:7008`.
4. Upload a `.835` file.
5. Click **View / Parse**.
6. Select output view:
   - Readable Table
   - Normalized JSON
7. Download output:
   - JSON
   - CSV
   - Excel
8. Optional: Click **Save to MySQL** if MySQL is configured.

---

## 5. API Endpoints

### Parse EDI file

```http
POST /api/edi/parse
```

Form-data:

```text
file = your-file.835
```

Returns normalized JSON:

```json
{
  "file_type": "X12 835 Electronic Remittance Advice (ERA)",
  "summary": {},
  "transactions": [],
  "flat_rows": []
}
```

### Export JSON

```http
POST /api/edi/export/json
```

### Export CSV

```http
POST /api/edi/export/csv
```

### Export Excel

```http
POST /api/edi/export/excel
```

### Save to MySQL

```http
POST /api/edi/save
```

---

### External ERA Lookup (JWT — outside team)

Authentication uses **access + refresh tokens** (not static API keys).

#### 1. Get tokens (login)

```http
POST /api/auth/token
Content-Type: application/json

{
  "client_id": "outside_team",
  "client_secret": "your_secret_here"
}
```

Response:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_expires_in": 86400
}
```

- **Access token** — valid 1 hour, use for lookup calls
- **Refresh token** — valid 1 day, use to renew access token without re-sending secret

#### 2. Refresh access token

```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

Returns a new access token and a new refresh token (rotation). Old refresh token is invalidated.

#### 3. Lookup ERA by trace number

```http
GET /api/era/lookup?trace_number=1234567890
Authorization: Bearer <access_token>
```

Returns normalized ERA JSON for matching documents in MongoDB.

**Configure in `backend/.env`:**

```env
JWT_SECRET=your_256bit_random_secret_here
JWT_CLIENTS=outside_team:your_client_secret_here
JWT_EXPIRE_SECONDS=3600
JWT_REFRESH_EXPIRE_SECONDS=86400
```

Expired refresh token records are auto-deleted from MongoDB via a TTL index on `auth_refresh_tokens`.

---

## 6. Optional MySQL Save Setup

The project works without MySQL. MySQL saving is optional.

### Step 1 — Create database/tables

Run:

```sql
source backend/mysql_schema.sql;
```

Or open `backend/mysql_schema.sql` in MySQL Workbench and execute it.

### Step 2 — Configure backend env

Copy:

```bash
cd backend
cp .env.example .env
```

Then update `.env`:

```env
MYSQL_URL=mysql+pymysql://root:password@localhost:3306/edi_835_converter
```

Restart backend:

```bash
uvicorn app.main:app --reload --port 7007
```

---

## 7. Output Meaning

### Summary fields

| Field | Meaning |
|---|---|
| `transaction_count` | Number of ST*835 transaction sets |
| `claim_count` | Number of CLP claim payment records |
| `service_line_count` | Number of SVC service line records |
| `total_payment_amount` | Total BPR payment amount |
| `total_claim_billed_amount` | Total billed amount from CLP |
| `total_claim_paid_amount` | Total paid amount from CLP |
| `total_adjustment_amount` | Total CAS adjustment amount |

### Table fields

The readable table is built from `flat_rows`. Each row represents a claim/service-line combination.

Important columns:

- Payment Date
- Payment Amount
- Payer
- Payee
- Claim ID
- Patient
- Claim Status
- Claim Billed Amount
- Claim Paid Amount
- Procedure Code
- Service Date
- Service Paid Amount
- Adjustment Details

---

## 8. Notes and Limitations

This is a practical working parser for common X12 835 ERA files. It supports important 835 segments such as:

- `ISA`, `GS`, `ST`, `SE`
- `BPR`, `TRN`
- `N1`, `N3`, `N4`, `PER`
- `CLP`, `NM1`, `SVC`
- `CAS`, `REF`, `DTM`, `AMT`, `QTY`, `LQ`

It is not a full HIPAA compliance validator. For production healthcare compliance, add:

- Full 005010X221A1 validation
- PHI/PII logging controls
- Authentication/authorization
- Audit logs
- Encrypted storage
- BAA/HIPAA hosting review

---

## 9. Quick Test with curl

### Internal EDI parse

```bash
curl -X POST http://localhost:7007/api/edi/parse \
  -F "file=@sample-files/sample-redacted.835"
```

### External ERA lookup (JWT)

```bash
# Step 1 — get tokens
curl -X POST http://localhost:7007/api/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"outside_team","client_secret":"YOUR_SECRET"}'

# Step 2 — lookup (replace ACCESS_TOKEN)
curl -X GET "http://localhost:7007/api/era/lookup?trace_number=1234567890" \
  -H "Authorization: Bearer ACCESS_TOKEN"

# Step 3 — refresh when access token expires
curl -X POST http://localhost:7007/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"REFRESH_TOKEN"}'
```

Download Excel:

```bash
curl -X POST http://localhost:7007/api/edi/export/excel \
  -F "file=@sample-files/sample-redacted.835" \
  -o output.xlsx
```

---

## 10. Recommended Next Improvements

- Add login/user roles
- Save uploaded source file in private storage
- Add payer/provider filters
- Add adjustment reason code description lookup
- Add claim-level detail drawer in frontend
- Add full EDI validation report
- Add batch upload
- Add background processing for large files
