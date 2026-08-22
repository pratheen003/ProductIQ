import React from "react";
import { TrustStatus } from "@/lib/types";
import { getTrustStatusConfig } from "@/lib/utils";
import { CheckCircle2, Sparkles, AlertTriangle, Clock, XCircle, HelpCircle } from "lucide-react";

interface TrustStatusBadgeProps {
  status: TrustStatus | string;
  className?: string;
  showIcon?: boolean;
  size?: "sm" | "md" | "lg";
}

export function TrustStatusBadge({
  status,
  className = "",
  showIcon = true,
  size = "md",
}: TrustStatusBadgeProps) {
  const config = getTrustStatusConfig(status);

  const getIcon = () => {
    switch (config.icon) {
      case "CheckCircle2":
        return <CheckCircle2 className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />;
      case "Sparkles":
        return <Sparkles className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />;
      case "AlertTriangle":
        return <AlertTriangle className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />;
      case "Clock":
        return <Clock className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />;
      case "XCircle":
        return <XCircle className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />;
      default:
        return <HelpCircle className={size === "sm" ? "w-3 h-3" : "w-3.5 h-3.5"} />;
    }
  };

  const sizeClasses = {
    sm: "px-2 py-0.5 text-[11px] gap-1",
    md: "px-2.5 py-1 text-xs gap-1.5",
    lg: "px-3 py-1.5 text-sm gap-2",
  };

  return (
    <span
      className={`inline-flex items-center font-sans font-medium rounded-full border shadow-sm ${config.colorClass} ${sizeClasses[size]} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor} shrink-0`} />
      {showIcon && <span className="shrink-0">{getIcon()}</span>}
      <span className="truncate">{config.label}</span>
    </span>
  );
}
