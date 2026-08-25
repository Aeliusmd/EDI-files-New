'use client';

import { useMemo, useRef, useState } from 'react';

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/$/, '');
const apiUrl = (path) => `${API_BASE}${path}`;

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

function StatusBadge({ code }) {
  const value = String(code || '').toUpperCase();
  if (!value) return <span className="status-badge muted">—</span>;
  const tone =
    value === 'A' ? 'accepted' : value === 'E' || value === 'R' ? 'rejected' : 'pending';
  const labels = { A: 'Accepted', E: 'Error', R: 'Rejected', P: 'Partial' };
  return (
    <span className={`status-badge ${tone}`}>
      {value} · {labels[value] || value}
    </span>
  );
}

export default function EdiProcessor({ config }) {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [parsed, setParsed] = useState(null);
  const [viewMode, setViewMode] = useState('table');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [search, setSearch] = useState('');

  const rows = useMemo(() => config.getRows(parsed), [config, parsed]);
  const summary = parsed?.summary || {};
  const envelope = parsed?.envelope || {};

  const filteredRows = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      Object.values(row).some((value) => {
        if (Array.isArray(value) || (value && typeof value === 'object')) {
          return JSON.stringify(value).toLowerCase().includes(q);
        }
        return String(value ?? '').toLowerCase().includes(q);
      })
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
      setMessage(config.selectMessage);
      return;
    }

    setLoading(true);
    setMessage(config.parseMessage);

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(apiUrl(config.parsePath), { method: 'POST', body: form });
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
      setMessage(config.selectMessage);
      return;
    }

    setLoading(true);
    setMessage(`Preparing ${format.toUpperCase()} download...`);

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(apiUrl(config.exportPath(format)), { method: 'POST', body: form });
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

  async function saveOptional() {
    if (!config.savePath || !file) {
      setMessage(config.selectMessage);
      return;
    }

    setLoading(true);
    setMessage('Saving parsed rows to MySQL...');

    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(apiUrl(config.savePath), { method: 'POST', body: form });
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

  function renderCell(key, row) {
    if (config.renderCell) {
      const custom = config.renderCell(key, row);
      if (custom !== undefined) return custom;
    }

    const value = row[key];

    if (config.moneyColumns?.includes(key)) {
      return money(value);
    }

    if (key === 'status999' || key === 'overall_status999') {
      return <StatusBadge code={value} />;
    }

    if (key === 'error_count') {
      const count = Array.isArray(row.errors) ? row.errors.length : Number(value || 0);
      return count > 0 ? <span className="error-count">{count}</span> : '0';
    }

    if (Array.isArray(value)) {
      return value.length ? `${value.length} item(s)` : '';
    }

    if (value && typeof value === 'object') {
      return JSON.stringify(value);
    }

    return String(value ?? '');
  }

  const summaryCards = config.summaryCards(summary, envelope, parsed);

  return (
    <main className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">{config.eyebrow}</p>
          <h1>{config.title}</h1>
          <p className="hero-text">{config.description}</p>
        </div>
        <div className={`status-pill pill-${config.badgeTone || 'green'}`}>{config.badge}</div>
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
            accept={config.accept}
            hidden
            onChange={(event) => onSelectFile(event.target.files)}
          />
          <div className={`upload-icon tone-${config.badgeTone || 'primary'}`}>{config.iconLabel}</div>
          <div>
            <h2>{file ? file.name : config.dropTitle}</h2>
            <p>{file ? `${(file.size / 1024).toFixed(1)} KB ready to parse` : config.dropHint}</p>
          </div>
        </div>

        <div className="actions">
          <button className="primary" onClick={parseFile} disabled={loading || !file}>
            {loading ? 'Working...' : 'View / Parse'}
          </button>
          <button onClick={() => download('json')} disabled={loading || !file}>Download JSON</button>
          <button onClick={() => download('csv')} disabled={loading || !file}>Download CSV</button>
          <button onClick={() => download('excel')} disabled={loading || !file}>Download Excel</button>
          {config.savePath && (
            <button onClick={saveOptional} disabled={loading || !file}>Save to MySQL</button>
          )}
        </div>

        {message && <div className="message">{message}</div>}
      </section>

      {parsed && (
        <>
          <section className={`summary-grid cols-${summaryCards.length}`}>
            {summaryCards.map((card) => (
              <div key={card.label} className={`summary-card${card.highlight ? ' highlight' : ''}`}>
                <span>{card.label}</span>
                <strong>{card.value}</strong>
              </div>
            ))}
          </section>

          {config.envelopeFields?.length > 0 && (
            <section className="envelope-card">
              <h3>Envelope</h3>
              <div className="envelope-grid">
                {config.envelopeFields.map(([key, label]) => (
                  <div key={key} className="envelope-item">
                    <span>{label}</span>
                    <strong>{String(envelope[key] ?? '—')}</strong>
                  </div>
                ))}
              </div>
            </section>
          )}

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
                  placeholder={config.searchPlaceholder}
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
                      {config.tableColumns.map(([key, label]) => (
                        <th key={key}>{label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRows.length === 0 ? (
                      <tr>
                        <td colSpan={config.tableColumns.length} className="empty-row">
                          No rows match your search.
                        </td>
                      </tr>
                    ) : (
                      filteredRows.map((row, index) => (
                        <tr key={config.rowKey(row, index)}>
                          {config.tableColumns.map(([key]) => (
                            <td key={key}>{renderCell(key, row)}</td>
                          ))}
                        </tr>
                      ))
                    )}
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
