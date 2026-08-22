"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { ShieldCheck, Search, Bell, Activity } from "lucide-react";

export function Header() {
  const pathname = usePathname();

  const getPageTitle = () => {
    if (pathname === "/") return "Executive Intelligence Dashboard";
    if (pathname.startsWith("/products/")) return "Product Intelligence Detail";
    if (pathname === "/products") return "Industrial Equipment Catalog";
    if (pathname === "/batch") return "Batch Trust & Analytics";
    if (pathname === "/reviews") return "Human Review & Resolution Queue";
    if (pathname === "/ingest") return "Data Ingestion & Extraction Engine";
    return "ProductIQ Intelligence";
  };

  return (
    <header className="h-16 border-b border-gray-200 bg-white px-8 flex items-center justify-between sticky top-0 z-20 shadow-subtle">
      {/* Page Title & Breadcrumbs */}
      <div>
        <h1 className="text-lg font-bold text-gray-900 font-sans tracking-tight">
          {getPageTitle()}
        </h1>
        <p className="text-xs text-gray-500 font-sans">
          Deterministic electromechanical data extraction, validation & trust engine
        </p>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Quick Demo Jump Button */}
        <Link
          href="/products/PIQ-W22SP-4P-1.1"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-mono font-medium bg-brand-dark/5 hover:bg-brand-dark/10 text-brand-dark border border-brand-dark/15 transition-colors"
          title="Open canonical conflict demonstration motor"
        >
          <span className="w-2 h-2 rounded-full bg-rose-500" />
          <span>Demo Conflict: PIQ-W22SP-4P-1.1</span>
        </Link>

        {/* System Health Badge */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-medium font-sans">
          <Activity className="w-3.5 h-3.5 text-emerald-600" />
          <span>Live API</span>
        </div>
      </div>
    </header>
  );
}
