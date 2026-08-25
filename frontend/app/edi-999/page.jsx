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
  ['file_837_control_number', '837 Control #'],
  ['status999', 'IK5 Status'],
  ['overall_status999', 'AK9 Overall'],
  ['file_type', '837 Type'],
  ['group_control_id', 'AK1 Group ID'],
  ['ak1_functional_id', 'AK1 Functional ID'],
  ['error_count', 'Errors'],
  ['status999_error_codes', 'IK5 Error Codes'],
  ['ak9_included_count', 'AK9 Included'],
  ['ak9_received_count', 'AK9 Received'],
  ['ak9_accepted_count', 'AK9 Accepted'],
  ['transaction_control_number', '999 Tx Control #'],
];

const config = {
  eyebrow: 'X12 Functional Acknowledgment',
  title: 'EDI 999 Processor',
  description:
    'Upload a .999 functional acknowledgment file, review each IK5 acceptance line, and export JSON, CSV, or Excel.',
  badge: '999 · Functional Ack',
  badgeTone: 'amber',
  iconLabel: '999',
  accept: '.999',
  dropTitle: 'Select or drop your .999 file',
  dropHint: 'Supported: .999 implementation acknowledgment files',
  selectMessage: 'Please select a .999 file first.',
  parseMessage: 'Parsing EDI 999 file...',
  parsePath: '/api/edi/999/parse',
  exportPath: (format) => `/api/edi/999/export/${format}`,
  searchPlaceholder: 'Search control number, status A/E/R...',
  tableColumns,
  envelopeFields,
  getRows: (parsed) =>
    (parsed?.flat_rows || []).map((row) => ({
      ...row,
      error_count: Array.isArray(row.errors) ? row.errors.length : 0,
      status999_error_codes: Array.isArray(row.status999_error_codes)
        ? row.status999_error_codes.join(', ')
        : row.status999_error_codes,
      ak9_error_codes: Array.isArray(row.ak9_error_codes)
        ? row.ak9_error_codes.join(', ')
        : row.ak9_error_codes,
    })),
  rowKey: (row, index) => `${row.file_837_control_number}-${row.status999}-${index}`,
  renderCell: (key, row) => {
    if (key === 'status999_error_codes' || key === 'ak9_error_codes') {
      return String(row[key] || '');
    }
    return undefined;
  },
  summaryCards: (summary, envelope, parsed) => {
    const rows = parsed?.flat_rows || [];
    const accepted = rows.filter((r) => String(r.status999 || '').toUpperCase() === 'A').length;
    const rejected = rows.filter((r) =>
      ['E', 'R'].includes(String(r.status999 || '').toUpperCase())
    ).length;

    return [
      { label: 'Acknowledgments', value: summary.ack_count ?? rows.length },
      { label: 'Accepted (A)', value: accepted },
      { label: 'Rejected / Error', value: rejected },
      {
        label: 'Group Control #',
        value: envelope.group_control_number || '—',
        highlight: true,
      },
    ];
  },
};

export default function Edi999Page() {
  return <EdiProcessor config={config} />;
}
