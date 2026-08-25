'use client';

import EdiProcessor from '../components/EdiProcessor';

const envelopeFields = [
  ['sender_id', 'Sender ID'],
  ['receiver_id', 'Receiver ID'],
  ['group_control_number', 'Group Control #'],
  ['group_date', 'Group Date'],
  ['functional_group', 'Functional Group'],
  ['implementation_version', 'Implementation'],
];

const tableColumns = [
  ['patient_acc_no', 'Patient Account'],
  ['patient_name', 'Patient'],
  ['claim_status_cat_code', 'Status Cat'],
  ['claim_status_code', 'Status Code'],
  ['claim_status_code_full', 'Full Status'],
  ['status_date', 'Status Date'],
  ['payer_name', 'Payer'],
  ['submitter_name', 'Submitter'],
  ['provider_name', 'Provider'],
  ['service_date', 'Service Date'],
  ['received_date', 'Received Date'],
  ['process_date', 'Process Date'],
  ['payer_trace', 'Payer Trace'],
  ['insured_id', 'Member ID'],
  ['transaction_control_number', 'Tx Control #'],
];

const config = {
  eyebrow: 'X12 Claim Status Response',
  title: 'EDI 277 Processor',
  description:
    'Upload a .277 claim status file, review STC status lines in a readable table, and export JSON, CSV, or Excel.',
  badge: '277 · Claim Status',
  badgeTone: 'blue',
  iconLabel: '277',
  accept: '.277',
  dropTitle: 'Select or drop your .277 file',
  dropHint: 'Supported: .277 claim status response files',
  selectMessage: 'Please select a .277 file first.',
  parseMessage: 'Parsing EDI 277 file...',
  parsePath: '/api/edi/277/parse',
  exportPath: (format) => `/api/edi/277/export/${format}`,
  searchPlaceholder: 'Search patient, payer, status code...',
  tableColumns,
  envelopeFields,
  getRows: (parsed) => parsed?.flat_rows || [],
  rowKey: (row, index) => `${row.patient_acc_no}-${row.claim_status_code_full}-${index}`,
  summaryCards: (summary, envelope) => [
    { label: 'Status Records', value: summary.record_count ?? 0 },
    { label: 'Group Control #', value: envelope.group_control_number || '—' },
    { label: 'Group Date', value: envelope.group_date || '—' },
    {
      label: 'Functional Group',
      value: envelope.functional_group || 'HN',
      highlight: true,
    },
  ],
};

export default function Edi277Page() {
  return <EdiProcessor config={config} />;
}
