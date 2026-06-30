import './globals.css';

export const metadata = {
  title: 'EDI 835 Converter',
  description: 'Convert X12 835 ERA files to JSON, CSV, Excel, and readable tables.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
