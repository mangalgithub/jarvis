"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useDashboard } from "@/context/DashboardContext";

interface AnalyticsChartProps {
  data: any[];
  dataKey: string;
  color: string;
  title: string;
}

export function AnalyticsChart({ data, dataKey, color, title }: AnalyticsChartProps) {
  const { isDarkMode } = useDashboard();

  return (
    <div className="h-[300px] w-full mt-4">
      <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500 mb-4 px-2">
        {title}
      </h3>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id={`gradient-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            vertical={false}
            stroke={isDarkMode ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)"}
          />
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fontWeight: 600, fill: isDarkMode ? "#94a3b8" : "#64748b" }}
            dy={10}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 10, fontWeight: 600, fill: isDarkMode ? "#94a3b8" : "#64748b" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: isDarkMode ? "#0f172a" : "#ffffff",
              borderRadius: "12px",
              border: "none",
              boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
              fontSize: "12px",
              fontWeight: "600"
            }}
            itemStyle={{ color: color }}
            cursor={{ stroke: color, strokeWidth: 2, strokeDasharray: "5 5" }}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={3}
            fillOpacity={1}
            fill={`url(#gradient-${dataKey})`}
            animationDuration={1500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
