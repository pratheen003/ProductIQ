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
  CheckCircle2,
  Table,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
}

const motorNavItems: NavItem[] = [
  { name: "Motor Dashboard", href: "/", icon: Compass },
  { name: "Motor Catalog", href: "/products", icon: Database },
  { name: "Batch Intelligence", href: "/batch", icon: BarChart3 },
  { name: "Review Queue", href: "/reviews", icon: ShieldAlert, badge: "62" },
  { name: "Pipeline Ingest", href: "/ingest", icon: Upload },
];

const catalogNavItems: NavItem[] = [
  { name: "Catalog Dashboard", href: "/catalog", icon: Layers },
  { name: "1,000 Items Explorer", href: "/catalog/products", icon: Table, badge: "1k" },
  { name: "Gold Standard (n=2)", href: "/catalog/gold-standard", icon: CheckCircle2 },
  { name: "Compliance & Metrics", href: "/catalog/eval", icon: Sparkles },
];

export function Sidebar() {
  const pathname = usePathname();

  const isLinkActive = (href: string) => {
    if (href === "/" || href === "/catalog") {
      return pathname === href;
    }
    return pathname.startsWith(href);
  };

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
                v6.2
              </span>
            </div>
            <p className="text-[11px] text-white/60 leading-tight">
              Industrial Trust Engine
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto">
        {/* Catalog Intelligence Section */}
        <div>
          <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-brand-accent/90 flex items-center justify-between">
            <span>Unilog Catalog</span>
            <span className="text-[9px] bg-brand-accent/20 px-1.5 py-0.5 rounded text-brand-accent font-mono font-bold">
              PIVOT
            </span>
          </div>
          <div className="space-y-1">
            {catalogNavItems.map((item) => {
              const active = isLinkActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    active
                      ? "bg-brand-accent text-white shadow-sm"
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={cn("w-4 h-4", active ? "text-white" : "text-white/60")} />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={cn(
                        "px-1.5 py-0.5 text-[10px] font-bold rounded font-mono",
                        active ? "bg-white/20 text-white" : "bg-white/10 text-white/70"
                      )}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        </div>

        {/* Motor Intelligence Section */}
        <div>
          <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-white/40 flex items-center justify-between">
            <span>Electric Motors</span>
            <span className="text-[9px] bg-white/10 px-1.5 py-0.5 rounded text-white/50 font-mono">
              FROZEN
            </span>
          </div>
          <div className="space-y-1">
            {motorNavItems.map((item) => {
              const active = isLinkActive(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                    active
                      ? "bg-white/20 text-white font-semibold"
                      : "text-white/60 hover:bg-white/10 hover:text-white"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={cn("w-4 h-4", active ? "text-white" : "text-white/50")} />
                    <span>{item.name}</span>
                  </div>
                  {item.badge && (
                    <span
                      className={cn(
                        "px-1.5 py-0.5 text-[10px] font-bold rounded font-mono",
                        active ? "bg-white/30 text-white" : "bg-white/10 text-white/60"
                      )}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-white/10 bg-brand-darker/50">
        <div className="flex items-center justify-between text-xs text-white/50">
          <span>Dual Pipeline Active</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Verified
          </span>
        </div>
      </div>
    </aside>
  );
}
