import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { TrustStatus, PublishabilityStatus, SeverityLevel } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatScore(score: number): string {
  return (score * 100).toFixed(1);
}

export function getTrustStatusConfig(status: TrustStatus | string) {
  const s = (status || "").toUpperCase();
  switch (s) {
    case "TRUSTED":
    case "VERIFIED":
      return {
        label: "Verified",
        rawStatus: "TRUSTED",
        colorClass: "bg-semantic-verifiedBg text-semantic-verified border-semantic-verifiedBorder",
        badgeBg: "bg-emerald-500",
        dotColor: "bg-emerald-500",
        textColor: "text-emerald-700",
        icon: "CheckCircle2",
      };
    case "INFERRED":
    case "UNVERIFIED":
      return {
        label: "Inferred",
        rawStatus: "UNVERIFIED",
        colorClass: "bg-semantic-inferredBg text-semantic-inferred border-semantic-inferredBorder",
        badgeBg: "bg-amber-500",
        dotColor: "bg-amber-500",
        textColor: "text-amber-700",
        icon: "Sparkles",
      };
    case "CONFLICTED":
    case "CONFLICT":
      return {
        label: "Conflict",
        rawStatus: "CONFLICTED",
        colorClass: "bg-semantic-conflictedBg text-semantic-conflicted border-semantic-conflictedBorder",
        badgeBg: "bg-rose-500",
        dotColor: "bg-rose-500",
        textColor: "text-rose-700",
        icon: "AlertTriangle",
      };
    case "REVIEW_REQUIRED":
      return {
        label: "Review Req.",
        rawStatus: "REVIEW_REQUIRED",
        colorClass: "bg-amber-50 text-amber-700 border-amber-300",
        badgeBg: "bg-amber-500",
        dotColor: "bg-amber-500",
        textColor: "text-amber-800",
        icon: "Clock",
      };
    case "UNSUPPORTED":
    case "FAIL":
      return {
        label: "Unsupported",
        rawStatus: "UNSUPPORTED",
        colorClass: "bg-semantic-unsupportedBg text-semantic-unsupported border-semantic-unsupportedBorder",
        badgeBg: "bg-purple-500",
        dotColor: "bg-purple-500",
        textColor: "text-purple-700",
        icon: "XCircle",
      };
    case "MISSING":
    case "UNKNOWN":
    default:
      return {
        label: "Unknown",
        rawStatus: "UNKNOWN",
        colorClass: "bg-semantic-unknownBg text-semantic-unknown border-semantic-unknownBorder",
        badgeBg: "bg-gray-400",
        dotColor: "bg-gray-400",
        textColor: "text-gray-600",
        icon: "HelpCircle",
      };
  }
}

export function getPublishabilityConfig(status: PublishabilityStatus | string) {
  const s = (status || "").toUpperCase();
  switch (s) {
    case "PUBLISHABLE":
      return {
        label: "Publishable",
        colorClass: "bg-emerald-50 text-emerald-700 border-emerald-200",
        dotColor: "bg-emerald-500",
      };
    case "PUBLISHABLE_WITH_WARNING":
      return {
        label: "Publish with Warning",
        colorClass: "bg-amber-50 text-amber-700 border-amber-200",
        dotColor: "bg-amber-500",
      };
    case "REVIEW_REQUIRED":
      return {
        label: "Review Required",
        colorClass: "bg-rose-50 text-rose-700 border-rose-200",
        dotColor: "bg-rose-500",
      };
    case "NOT_PUBLISHABLE":
    default:
      return {
        label: "Not Publishable",
        colorClass: "bg-gray-100 text-gray-700 border-gray-200",
        dotColor: "bg-gray-400",
      };
  }
}

export function getSeverityConfig(severity: SeverityLevel | string) {
  const s = (severity || "").toUpperCase();
  switch (s) {
    case "CRITICAL":
      return { label: "Critical", color: "bg-red-100 text-red-800 border-red-300" };
    case "HIGH":
      return { label: "High", color: "bg-rose-100 text-rose-800 border-rose-300" };
    case "MEDIUM":
      return { label: "Medium", color: "bg-amber-100 text-amber-800 border-amber-300" };
    case "LOW":
    default:
      return { label: "Low", color: "bg-blue-50 text-blue-700 border-blue-200" };
  }
}
