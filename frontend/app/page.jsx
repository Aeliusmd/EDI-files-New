'use client';

import EdiProcessor from './components/EdiProcessor';

function money(value) {
  const n = Number(value || 0);
  return n.toLocaleString(undefined, { style: 'currency', currency: 'USD' });
}

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

const config = {
  eyebrow: 'X12 Healthcare Remittance',
  title: 'EDI 835 Converter',
  description:
    'Upload an ERA .835 file, view a clean readable table, inspect normalized JSON, and download JSON, CSV, or Excel outputs from your own server.',
  badge: 'FastAPI + Next.js',
  badgeTone: 'green',
  iconLabel: '835',
  accept: '.835,.edi,.txt',
  dropTitle: 'Select or drop your .835 file',
  dropHint: 'Supported: .835, .edi, .txt',
  selectMessage: 'Please select an .835 file first.',
  parseMessage: 'Parsing EDI 835 file...',
  parsePath: '/api/edi/parse',
  exportPath: (format) => `/api/edi/export/${format}`,
  savePath: '/api/edi/save',
  searchPlaceholder: 'Search claim, patient, payer...',
  tableColumns,
  moneyColumns: ['payment_amount', 'claim_billed_amount', 'claim_paid_amount', 'service_paid_amount'],
  getRows: (parsed) => parsed?.flat_rows || [],
  rowKey: (row, index) => `${row.claim_id}-${row.service_line_no}-${index}`,
  summaryCards: (summary) => [
    { label: 'Transactions', value: summary.transaction_count ?? 0 },
    { label: 'Claims', value: summary.claim_count ?? 0 },
    { label: 'Service Lines', value: summary.service_line_count ?? 0 },
    {
      label: 'Total Payment',
      value: money(summary.total_payment_amount),
      highlight: true,
    },
  ],
};

export default function Home() {
  return <EdiProcessor config={config} />;
}
