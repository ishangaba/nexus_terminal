"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  TooltipProps,
  XAxis,
  YAxis,
} from "recharts";
import { ChartPoint } from "@/lib/api";

interface PriceChartProps {
  chartData: ChartPoint[];
}

function fmt(value: number | null | undefined): string {
  return value === null || value === undefined ? "—" : `$${value.toFixed(2)}`;
}

function ChartTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const point = payload[0].payload as ChartPoint;

  return (
    <div className="rounded-md border border-zinc-200 bg-white px-3 py-2 text-xs font-mono shadow-md dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-1 font-sans font-medium text-zinc-500 dark:text-zinc-400">{label}</div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
        <span className="font-sans text-zinc-500 dark:text-zinc-500">Open</span>
        <span className="text-right font-medium text-zinc-800 dark:text-zinc-200">{fmt(point.open)}</span>
        <span className="font-sans text-zinc-500 dark:text-zinc-500">High</span>
        <span className="text-right font-medium text-zinc-800 dark:text-zinc-200">{fmt(point.high)}</span>
        <span className="font-sans text-zinc-500 dark:text-zinc-500">Low</span>
        <span className="text-right font-medium text-zinc-800 dark:text-zinc-200">{fmt(point.low)}</span>
        <span className="font-sans text-zinc-500 dark:text-zinc-500">Close</span>
        <span className="text-right font-semibold text-cyan-600 dark:text-cyan-400">{fmt(point.close)}</span>
      </div>
    </div>
  );
}

export default function PriceChart({ chartData }: PriceChartProps) {
  if (!chartData || chartData.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/60">
        No chart data available.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">30-Day Price</h3>
        <div className="flex items-center gap-1.5 text-xs text-zinc-400 dark:text-zinc-500">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-cyan-600/10" />
          Daily range
          <span className="ml-2 inline-block h-0.5 w-3 rounded bg-cyan-600 dark:bg-cyan-400" />
          Close
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={chartData}>
          <CartesianGrid vertical={false} stroke="currentColor" strokeOpacity={0.08} />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={30} />
          <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} width={60} />
          <Tooltip content={<ChartTooltip />} />
          <Area
            dataKey={(point: ChartPoint) => (point.low !== null && point.high !== null ? [point.low, point.high] : null)}
            fill="#0891b2"
            fillOpacity={0.12}
            stroke="none"
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#0891b2"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
