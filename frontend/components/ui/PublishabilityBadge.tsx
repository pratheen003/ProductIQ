import React from "react";
import { PublishabilityStatus } from "@/lib/types";
import { getPublishabilityConfig } from "@/lib/utils";
import { Globe, AlertOctagon, Check, ShieldAlert } from "lucide-react";

interface PublishabilityBadgeProps {
  status: PublishabilityStatus | string;
  className?: string;
}

export function PublishabilityBadge({
  status,
  className = "",
}: PublishabilityBadgeProps) {
  const config = getPublishabilityConfig(status);

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium font-sans rounded-full border shadow-subtle ${config.colorClass} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${config.dotColor} shrink-0`} />
      <span>{config.label}</span>
    </span>
  );
}
