"use client";

import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";

interface SeverityBarChartProps {
  data: Record<string, number>;
  className?: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#DC2626", // Red
  HIGH: "#F43F5E",     // Rose
  MEDIUM: "#D97706",   // Amber
  LOW: "#3B82F6",      // Blue
};

export function SeverityBarChart({
  data,
  className = "",
}: SeverityBarChartProps) {
  const chartData = ["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => ({
    severity: sev,
    count: data[sev] || 0,
    color: SEVERITY_COLORS[sev] || "#6B7280",
  }));

  const total = Object.values(data).reduce((acc, v) => acc + v, 0);

  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-5 shadow-card ${className}`}>
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <div>
          <h4 className="font-sans font-bold text-gray-900 text-sm">
            Review Queue Severity Breakdown
          </h4>
          <p className="text-xs text-gray-500 font-sans mt-0.5">
            {total} flagged review items categorized by engineering risk
          </p>
        </div>
      </div>

      <div className="mt-4 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="severity"
              tick={{ fontSize: 11, fontFamily: "var(--font-ibm-plex-mono)", fill: "#6B7280" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fontFamily: "var(--font-ibm-plex-mono)", fill: "#6B7280" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="bg-brand-dark text-white p-2 rounded-md text-xs font-mono shadow-lg">
                      <p className="font-bold">{d.severity} Severity</p>
                      <p>Review Items: {d.count}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
