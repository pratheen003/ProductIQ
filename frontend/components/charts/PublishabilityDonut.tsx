"use client";

import React from "react";
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";

interface PublishabilityDonutProps {
  data: Record<string, number>;
  className?: string;
}

const PUB_COLORS: Record<string, string> = {
  PUBLISHABLE: "#16A34A",                // Emerald
  PUBLISHABLE_WITH_WARNING: "#D97706",   // Amber
  REVIEW_REQUIRED: "#DC2626",            // Red
  NOT_PUBLISHABLE: "#6B7280",            // Gray
};

export function PublishabilityDonut({
  data,
  className = "",
}: PublishabilityDonutProps) {
  const chartData = Object.entries(data)
    .filter(([_, count]) => count > 0)
    .map(([key, count]) => ({
      name: key.replace(/_/g, " "),
      rawKey: key,
      value: count,
      color: PUB_COLORS[key] || "#6B7280",
    }));

  const total = Object.values(data).reduce((acc, v) => acc + v, 0);

  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-5 shadow-card ${className}`}>
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <div>
          <h4 className="font-sans font-bold text-gray-900 text-sm">
            Commercial Catalog Readiness
          </h4>
          <p className="text-xs text-gray-500 font-sans mt-0.5">
            Publishability status across all {total} motors
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="w-full sm:w-1/2 h-44 relative">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={46}
                outerRadius={66}
                paddingAngle={4}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-brand-dark text-white p-2 rounded-md text-xs font-mono shadow-lg">
                        <p className="font-bold">{d.name}</p>
                        <p>
                          Count: {d.value} ({Math.round((d.value / (total || 1)) * 100)}%)
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="font-mono font-bold text-lg text-gray-900">{total}</span>
            <span className="font-sans text-[10px] text-gray-400 uppercase">Catalog</span>
          </div>
        </div>

        <div className="w-full sm:w-1/2 space-y-2">
          {chartData.map((item) => (
            <div key={item.name} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: item.color }}
                />
                <span className="font-sans text-gray-700 capitalize text-[11px]">
                  {item.name.toLowerCase()}
                </span>
              </div>
              <span className="font-mono font-bold text-gray-900">
                {item.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
