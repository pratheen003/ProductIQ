"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Upload,
  Layers,
  BarChart3,
  ShieldAlert,
  Compass,
  Cpu,
  Database,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

const navItems: NavItem[] = [
  { name: "Dashboard", href: "/", icon: Compass },
  { name: "Products", href: "/products", icon: Database },
  { name: "Batch Intelligence", href: "/batch", icon: BarChart3 },
  { name: "Review Queue", href: "/reviews", icon: ShieldAlert, badge: "62" },
  { name: "Data Ingestion", href: "/ingest", icon: Upload },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-brand-dark text-white flex flex-col shrink-0 border-r border-brand-darker select-none h-screen sticky top-0">
      {/* Brand Header */}
      <div className="p-6 border-b border-white/10 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-lg bg-brand-accent flex items-center justify-center shadow-md group-hover:scale-105 transition-transform">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-lg tracking-tight text-white font-sans">
                Product<span className="text-brand-muted">IQ</span>
              </span>
              <span className="px-1.5 py-0.5 text-[10px] uppercase font-mono font-bold bg-white/15 text-white/90 rounded">
                v6.0
              </span>
            </div>
            <p className="text-[11px] text-white/60 leading-tight">
              Industrial Trust Engine
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-6 space-y-1.5 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-mono font-semibold uppercase tracking-wider text-white/40">
          Core Workflows
        </div>

        {navItems.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center justify-between px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 group",
                isActive
                  ? "bg-brand-accent text-white shadow-sm font-semibold"
                  : "text-white/70 hover:text-white hover:bg-white/10"
              )}
            >
              <div className="flex items-center gap-3">
                <item.icon
                  className={cn(
                    "w-4 h-4 transition-colors",
                    isActive
                      ? "text-white"
                      : "text-white/60 group-hover:text-white"
                  )}
                />
                <span className="font-sans">{item.name}</span>
              </div>

              {item.badge && (
                <span
                  className={cn(
                    "px-2 py-0.5 text-xs font-mono font-bold rounded-full",
                    isActive
                      ? "bg-white text-brand-accent"
                      : "bg-white/15 text-white/90"
                  )}
                >
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Backend & Domain Info */}
      <div className="p-4 border-t border-white/10 bg-black/15 space-y-3">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="font-mono text-white/80 text-[11px]">FastAPI Bridge</span>
          </div>
          <span className="text-[10px] font-mono bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded">
            PORT 8000
          </span>
        </div>

        <div className="pt-2 border-t border-white/10 text-[11px] text-white/60 flex items-center justify-between">
          <span>Category: Motors (WEG W22)</span>
          <span className="font-mono text-[10px]">12 SKUs</span>
        </div>
      </div>
    </aside>
  );
}
