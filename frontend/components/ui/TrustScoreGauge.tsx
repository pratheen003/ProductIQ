"use client";

import React from "react";
import { formatScore } from "@/lib/utils";

interface TrustScoreGaugeProps {
  score: number; // 0.0 to 1.0
  breakdown?: {
    completeness_score?: number;
    validity_score?: number;
    diversity_score?: number;
    conflict_penalty?: number;
  };
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function TrustScoreGauge({
  score,
  breakdown,
  size = "md",
  className = "",
}: TrustScoreGaugeProps) {
  const percentage = Math.round(score * 100);

  // Determine ring color
  const getRingColor = () => {
    if (percentage >= 80) return "#16A34A"; // Emerald
    if (percentage >= 50) return "#D97706"; // Amber
    return "#DC2626"; // Rose / Conflicted
  };

  const ringColor = getRingColor();
  const radius = size === "lg" ? 54 : size === "md" ? 44 : 32;
  const strokeWidth = size === "lg" ? 8 : size === "md" ? 7 : 5;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;
  const svgSize = (radius + strokeWidth) * 2 + 10;

  return (
    <div className={`flex flex-col items-center justify-center ${className}`}>
      <div className="relative flex items-center justify-center">
        <svg
          width={svgSize}
          height={svgSize}
          className="transform -rotate-90"
        >
          {/* Background circle */}
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            stroke="#E5E7EB"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Progress circle */}
          <circle
            cx={svgSize / 2}
            cy={svgSize / 2}
            r={radius}
            stroke={ringColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            className="transition-all duration-700 ease-out"
          />
        </svg>

        {/* Center score text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span
            className={`font-mono font-bold tracking-tight text-gray-900 ${
              size === "lg"
                ? "text-3xl"
                : size === "md"
                ? "text-2xl"
                : "text-base"
            }`}
          >
            {percentage}
          </span>
          <span
            className={`font-sans font-medium text-gray-500 uppercase ${
              size === "lg"
                ? "text-xs"
                : size === "md"
                ? "text-[10px]"
                : "text-[8px]"
            }`}
          >
            / 100
          </span>
        </div>
      </div>

      {/* Breakdown Pills */}
      {breakdown && size !== "sm" && (
        <div className="mt-3 flex items-center gap-3 text-[11px] font-mono text-gray-600">
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Comp: {Math.round((breakdown.completeness_score || 0) * 100)}%</span>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span>Val: {Math.round((breakdown.validity_score || 0) * 100)}%</span>
          </div>
          {(breakdown.conflict_penalty || 0) > 0 && (
            <div className="flex items-center gap-1 text-rose-600">
              <span className="w-2 h-2 rounded-full bg-rose-500" />
              <span>Pen: -{Math.round((breakdown.conflict_penalty || 0) * 100)}%</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
