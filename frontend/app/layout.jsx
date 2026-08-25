import './globals.css';
import AppNav from './components/AppNav';

export const metadata = {
  title: 'EDI Processor — 835 · 277 · 999',
  description: 'Parse and view X12 835 ERA, 277 claim status, and 999 functional acknowledgment files.',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="site-shell">
          <header className="site-header">
            <div className="site-brand">
              <span className="site-brand-mark">EDI</span>
              <div>
                <strong>Healthcare EDI Processor</strong>
                <small>835 · 277 · 999</small>
              </div>
            </div>
            <AppNav />
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
