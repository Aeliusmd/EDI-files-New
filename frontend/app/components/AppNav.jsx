'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const links = [
  { href: '/', label: '835 ERA', code: '835', hint: 'Remittance / payment' },
  { href: '/edi-277', label: '277 Claim Status', code: '277', hint: 'Claim acknowledgment' },
  { href: '/edi-999', label: '999 Functional Ack', code: '999', hint: '837 file acceptance' },
];

export default function AppNav() {
  const pathname = usePathname();

  return (
    <nav className="app-nav" aria-label="EDI file types">
      {links.map((link) => {
        const active = pathname === link.href;
        return (
          <Link
            key={link.href}
            href={link.href}
            className={`app-nav-link${active ? ' active' : ''}`}
            aria-current={active ? 'page' : undefined}
          >
            <span className="app-nav-code">{link.code}</span>
            <span className="app-nav-text">
              <strong>{link.label}</strong>
              <small>{link.hint}</small>
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
