# EDI 835 Converter Backend

FastAPI backend for parsing X12 835 Electronic Remittance Advice files and exporting JSON, CSV, and Excel.

## Run

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open API docs:

```text
http://localhost:8000/docs
```

## Optional MySQL save

1. Create a MySQL database using `mysql_schema.sql`.
2. Copy `.env.example` to `.env`.
3. Set `MYSQL_URL`.
4. Restart the backend.

Example:

```env
MYSQL_URL=mysql+pymysql://root:password@localhost:3306/edi_835_converter
```
