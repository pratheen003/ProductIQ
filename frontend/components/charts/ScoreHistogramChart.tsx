"use client";

import React from "react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from "recharts";
import { ProductSummary } from "@/lib/types";

interface ScoreHistogramChartProps {
  products: ProductSummary[];
  className?: string;
}

export function ScoreHistogramChart({
  products,
  className = "",
}: ScoreHistogramChartProps) {
  const chartData = products.map((p) => ({
    name: p.product_id.replace("PIQ-W22SP-", ""),
    fullName: p.product_id,
    power: `${p.rated_power_kw || "—"} kW`,
    score: Math.round(p.trust_score * 100),
    status: p.overall_trust_status,
  }));

  const getBarColor = (score: number) => {
    if (score >= 80) return "#16A34A";
    if (score >= 50) return "#D97706";
    return "#BE5CA9"; // Brand accent
  };

  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-5 shadow-card ${className}`}>
      <div className="flex items-center justify-between pb-3 border-b border-gray-100">
        <div>
          <h4 className="font-sans font-bold text-gray-900 text-sm">
            Dataset Trust Scores by Motor SKU
          </h4>
          <p className="text-xs text-gray-500 font-sans mt-0.5">
            Deterministic score derived from completeness, validity & conflict penalty
          </p>
        </div>
      </div>

      <div className="mt-4 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fontFamily: "var(--font-ibm-plex-mono)", fill: "#6B7280" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 10, fontFamily: "var(--font-ibm-plex-mono)", fill: "#6B7280" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const d = payload[0].payload;
                  return (
                    <div className="bg-brand-dark text-white p-2 rounded-md text-xs font-mono shadow-lg">
                      <p className="font-bold">{d.fullName}</p>
                      <p>Power: {d.power}</p>
                      <p>Trust Score: {d.score}/100</p>
                      <p>Status: {d.status}</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar dataKey="score" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.score)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
