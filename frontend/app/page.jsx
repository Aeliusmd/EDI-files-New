'use client';

import { useMemo, useRef, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:7007';

const tableColumns = [
  ['transaction_no', 'Tx #'],
  ['payment_date', 'Payment Date'],
  ['payment_amount', 'Payment'],
  ['payer_name', 'Payer'],
  ['payee_name', 'Payee'],
  ['claim_id', 'Claim ID'],
  ['patient_name', 'Patient'],
  ['claim_status', 'Status'],
  ['claim_billed_amount', 'Claim Billed'],
  ['claim_paid_amount', 'Claim Paid'],
  ['procedure_code', 'Procedure'],
  ['service_date', 'Service Date'],
  ['service_paid_amount', 'Service Paid'],
  ['service_adjustment_details', 'Service Adjustments'],
];

function money(value) {
  const n = Number(value || 0);
  return n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}

function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default function Home() {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [parsed, setParsed] = useState(null);
  const [viewMode, setViewMode] = useState('table');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [search, setSearch] = useState('');

  const rows = parsed?.flat_rows || [];
  const summary = parsed?.summary || {};

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      Object.values(row).some((value) => String(value ?? '').toLowerCase().includes(q))
    );
  }, [rows, search]);

  function onSelectFile(selected) {
    const nextFile = selected?.[0];
    setFile(nextFile || null);
    setParsed(null);
    setMessage(nextFile ? `${nextFile.name} selected` : '');
  }

  async function parseFile() {
    if (!file) {
      setMessage('Please select an .835 file first.');
      return;
    }

    setLoading(true);
    setMessage('Parsing EDI 835 file...');

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API_BASE}/api/edi/parse`, { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to parse file');
      setParsed(data);
      setViewMode('table');
      setMessage('File parsed successfully.');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function download(format) {
    if (!file) {
      setMessage('Please select an .835 file first.');
      return;
    }

    setLoading(true);
    setMessage(`Preparing ${format.toUpperCase()} download...`);

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API_BASE}/api/edi/export/${format}`, { method: 'POST', body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Failed to export ${format}`);
      }
      const blob = await res.blob();
      const ext = format === 'excel' ? 'xlsx' : format;
      const base = file.name.replace(/\.[^.]+$/, '');
      downloadBlob(blob, `${base}.${ext}`);
      setMessage(`${format.toUpperCase()} downloaded.`);
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function saveToMysql() {
    if (!file) {
      setMessage('Please select an .835 file first.');
      return;
    }

    setLoading(true);
    setMessage('Saving parsed rows to MySQL...');

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API_BASE}/api/edi/save`, { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Save failed');
      if (!data.success) {
        setMessage(data.database?.message || 'MySQL is not configured.');
      } else {
        setMessage(`Saved to MySQL. Import ID: ${data.database.import_id}, rows: ${data.database.saved_rows}`);
      }
    } catch (error) {
      setMessage(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">X12 Healthcare Remittance</p>
          <h1>EDI 835 Converter</h1>
          <p className="hero-text">
            Upload an ERA .835 file, view a clean readable table, inspect normalized JSON,
            and download JSON, CSV, or Excel outputs from your own server.
          </p>
        </div>
        <div className="status-pill">FastAPI + Next.js</div>
      </section>

      <section className="upload-card">
        <div
          className="drop-zone"
          onClick={() => fileRef.current?.click()}
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            onSelectFile(event.dataTransfer.files);
          }}
        >
          <input
            ref={fileRef}
            type="file"
            accept=".835,.edi,.txt"
            hidden
            onChange={(event) => onSelectFile(event.target.files)}
          />
          <div className="upload-icon">835</div>
          <div>
            <h2>{file ? file.name : 'Select or drop your .835 file'}</h2>
            <p>{file ? `${(file.size / 1024).toFixed(1)} KB ready to parse` : 'Supported: .835, .edi, .txt'}</p>
          </div>
        </div>

        <div className="actions">
          <button className="primary" onClick={parseFile} disabled={loading || !file}>
            {loading ? 'Working...' : 'View / Parse'}
          </button>
          <button onClick={() => download('json')} disabled={loading || !file}>Download JSON</button>
          <button onClick={() => download('csv')} disabled={loading || !file}>Download CSV</button>
          <button onClick={() => download('excel')} disabled={loading || !file}>Download Excel</button>
          <button onClick={saveToMysql} disabled={loading || !file}>Save to MySQL</button>
        </div>

        {message && <div className="message">{message}</div>}
      </section>

      {parsed && (
        <>
          <section className="summary-grid">
            <div className="summary-card">
              <span>Transactions</span>
              <strong>{summary.transaction_count ?? 0}</strong>
            </div>
            <div className="summary-card">
              <span>Claims</span>
              <strong>{summary.claim_count ?? 0}</strong>
            </div>
            <div className="summary-card">
              <span>Service Lines</span>
              <strong>{summary.service_line_count ?? 0}</strong>
            </div>
            <div className="summary-card highlight">
              <span>Total Payment</span>
              <strong>{money(summary.total_payment_amount)}</strong>
            </div>
          </section>

          <section className="viewer-card">
            <div className="viewer-header">
              <div>
                <h2>Converted Output</h2>
                <p>{filteredRows.length} readable row(s)</p>
              </div>
              <div className="view-controls">
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search claim, patient, payer..."
                />
                <select value={viewMode} onChange={(event) => setViewMode(event.target.value)}>
                  <option value="table">Readable Table</option>
                  <option value="json">Normalized JSON</option>
                </select>
              </div>
            </div>

            {viewMode === 'json' ? (
              <pre className="json-view">{JSON.stringify(parsed, null, 2)}</pre>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {tableColumns.map(([key, label]) => <th key={key}>{label}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.map((row, index) => (
                      <tr key={`${row.claim_id}-${row.service_line_no}-${index}`}>
                        {tableColumns.map(([key]) => (
                          <td key={key}>
                            {['payment_amount', 'claim_billed_amount', 'claim_paid_amount', 'service_paid_amount'].includes(key)
                              ? money(row[key])
                              : String(row[key] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
