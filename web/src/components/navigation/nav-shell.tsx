"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ReactNode } from "react";

const NAV_ITEMS = [
  { href: "/ask", label: "Ask" },
  { href: "/learning", label: "Learning" },
  { href: "/mastery", label: "Mastery" },
  { href: "/knowledge", label: "Knowledge" },
  { href: "/settings", label: "Settings" },
];

export function NavShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell-root">
      <aside className="shell-nav" aria-label="primary navigation">
        <h1 className="shell-title">LearnOS Console</h1>
        <nav className="shell-menu">
          {NAV_ITEMS.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`shell-nav-item ${isActive ? "active" : ""}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <main className="shell-content">{children}</main>
    </div>
  );
}
