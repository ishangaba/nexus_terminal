"use client";

import { useEffect, useState } from "react";
import ErrorNotice from "@/components/ErrorNotice";
import {
  fetchSignalCalibration,
  fetchSignalPerformance,
  ConfidenceLevel,
  ReturnHorizon,
  SignalCalibration,
  SignalPerformance,
} from "@/lib/api";

const HORIZON_LABEL: Record<ReturnHorizon, string> = {
  return_1d: "1d",
  return_3d: "3d",
  return_5d: "5d",
  return_10d: "10d",
  return_20d: "20d",
};

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

function fmtPct(n: number | null): string {
  if (n === null) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function pctClass(n: number | null): string {
  if (n === null) return "text-zinc-400 dark:text-zinc-600";
  return n >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400";
}

function fmtRate(n: number | null): string {
  if (n === null) return "—";
  return `${(n * 100).toFixed(0)}%`;
}

export default function ModelPerformance() {
  const [performance, setPerformance] = useState<SignalPerformance | null>(null);
  const [calibration, setCalibration] = useState<SignalCalibration | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [perf, cal] = await Promise.all([fetchSignalPerformance(), fetchSignalCalibration()]);
        setPerformance(perf);
        setCalibration(cal);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load signal performance");
      }
    })();
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
        <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">Model Performance</h3>
        <ErrorNotice message={error} />
      </div>
    );
  }

  if (!performance || !calibration) {
    return null;
  }

  if (performance.total_signals === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
        <h3 className="mb-2 text-sm font-medium text-zinc-500 dark:text-zinc-400">Model Performance</h3>
        <p className="text-sm text-zinc-500 dark:text-zinc-500">
          No trade signals generated yet — track record builds up as signals are resolved.
        </p>
      </div>
    );
  }

  const horizons = Object.entries(performance.horizons) as [ReturnHorizon, SignalPerformance["horizons"][ReturnHorizon]][];

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Model Performance</h3>
        <span className="text-xs text-zinc-400 dark:text-zinc-600">
          {performance.resolved_count} of {performance.total_signals} signal{performance.total_signals === 1 ? "" : "s"} resolved
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
          <div className="text-xs text-zinc-500 dark:text-zinc-500">Win rate</div>
          <div className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">{fmtRate(performance.win_rate)}</div>
        </div>
        <div className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
          <div className="text-xs text-zinc-500 dark:text-zinc-500">Bullish accuracy</div>
          <div className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
            {fmtRate(performance.bullish_accuracy)}{" "}
            <span className="text-xs font-normal text-zinc-400">({performance.bullish_n})</span>
          </div>
        </div>
        <div className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
          <div className="text-xs text-zinc-500 dark:text-zinc-500">Bearish accuracy</div>
          <div className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">
            {fmtRate(performance.bearish_accuracy)}{" "}
            <span className="text-xs font-normal text-zinc-400">({performance.bearish_n})</span>
          </div>
        </div>
        <div className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
          <div className="text-xs text-zinc-500 dark:text-zinc-500">Alpha vs. SPY (5d)</div>
          <div className={`text-lg font-semibold ${pctClass(performance.avg_alpha_vs_benchmark_5d_pct)}`}>
            {fmtPct(performance.avg_alpha_vs_benchmark_5d_pct)}
          </div>
        </div>
      </div>

      <div className="mt-5">
        <h4 className="mb-2 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">
          Forward returns by horizon
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] text-sm">
            <thead>
              <tr className="border-b border-zinc-200 text-left text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-500">
                <th className="py-1.5 pr-3 font-medium">Horizon</th>
                <th className="py-1.5 pr-3 font-medium">n</th>
                <th className="py-1.5 pr-3 font-medium">Avg return</th>
                <th className="py-1.5 font-medium">Median return</th>
              </tr>
            </thead>
            <tbody>
              {horizons.map(([key, stats]) => (
                <tr key={key} className="border-b border-zinc-100 last:border-0 dark:border-zinc-900">
                  <td className="py-1.5 pr-3 text-zinc-700 dark:text-zinc-300">{HORIZON_LABEL[key]}</td>
                  <td className="py-1.5 pr-3 text-zinc-500 dark:text-zinc-500">{stats.n}</td>
                  <td className={`py-1.5 pr-3 font-medium ${pctClass(stats.avg_directional_return_pct)}`}>
                    {fmtPct(stats.avg_directional_return_pct)}
                  </td>
                  <td className={`py-1.5 font-medium ${pctClass(stats.median_directional_return_pct)}`}>
                    {fmtPct(stats.median_directional_return_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-5">
        <h4 className="mb-2 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">
          Confidence calibration
        </h4>
        <div className="grid grid-cols-3 gap-3">
          {(Object.entries(calibration.buckets) as [ConfidenceLevel, SignalCalibration["buckets"][ConfidenceLevel]][]).map(
            ([level, bucket]) => (
              <div key={level} className="rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
                <div className="text-xs text-zinc-500 dark:text-zinc-500">{CONFIDENCE_LABEL[level]} confidence</div>
                <div className="text-lg font-semibold text-zinc-800 dark:text-zinc-100">{fmtRate(bucket.accuracy)}</div>
                <div className="text-xs text-zinc-400 dark:text-zinc-600">
                  {bucket.correct}/{bucket.n} correct
                </div>
              </div>
            )
          )}
        </div>
        {calibration.brier_score !== null && (
          <p className="mt-2 text-xs text-zinc-400 dark:text-zinc-600">
            Brier score: {calibration.brier_score.toFixed(3)} (lower is better calibrated, 0 = perfect, 0.25 = a coin flip)
            {" · "}
            {calibration.brier_sample_size} resolved signal{calibration.brier_sample_size === 1 ? "" : "s"}
          </p>
        )}
      </div>
    </div>
  );
}
