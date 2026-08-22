import React from "react";
import { LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  badgeText?: string;
  badgeType?: "positive" | "negative" | "warning" | "neutral" | "brand";
  icon?: LucideIcon;
  className?: string;
}

export function MetricCard({
  title,
  value,
  subtitle,
  badgeText,
  badgeType = "neutral",
  icon: Icon,
  className = "",
}: MetricCardProps) {
  const getBadgeStyle = () => {
    switch (badgeType) {
      case "positive":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "negative":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "warning":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "brand":
        return "bg-brand-dark/10 text-brand-dark border-brand-dark/20";
      default:
        return "bg-gray-100 text-gray-700 border-gray-200";
    }
  };

  return (
    <div
      className={`bg-white rounded-xl p-5 border border-gray-200 shadow-card hover:shadow-elevation transition-all duration-200 flex flex-col justify-between ${className}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-mono font-medium uppercase tracking-wider text-gray-500">
            {title}
          </span>
          <div className="text-2xl font-bold font-mono text-gray-900 mt-1.5 tracking-tight">
            {value}
          </div>
        </div>

        {Icon && (
          <div className="w-10 h-10 rounded-lg bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-600">
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {(subtitle || badgeText) && (
        <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
          {subtitle && <span className="text-gray-500 font-sans">{subtitle}</span>}
          {badgeText && (
            <span
              className={`px-2 py-0.5 rounded text-[11px] font-mono font-medium border ${getBadgeStyle()}`}
            >
              {badgeText}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
