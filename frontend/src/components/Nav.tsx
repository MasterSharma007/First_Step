"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/live", label: "Live" },
  { href: "/price-action", label: "Price Action" },
  { href: "/option-chain", label: "Option Chain" },
  { href: "/signals", label: "Signals" },
  { href: "/trades", label: "Trades" },
  { href: "/backtest", label: "Backtest" },
  { href: "/reports", label: "Reports" },
  { href: "/logs", label: "Logs" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-4">
        <span className="font-semibold tracking-tight text-black">
          Bank Nifty <span className="text-blue-600">AI</span>
        </span>
        <nav className="flex gap-1 text-sm">
          {LINKS.map((link) => {
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
                  active
                    ? "bg-blue-600 text-white"
                    : "text-slate-700 hover:bg-sky-100 hover:text-black"
                }`}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
