"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  CrosshairMode,
  LineStyle,
  IChartApi,
  ISeriesApi,
  Time,
} from "lightweight-charts";
import ErrorNotice from "@/components/ErrorNotice";
import { ChartPoint, TickerPrice } from "@/lib/api";
import { calculateSMA, calculateBollingerBands, calculateRSI, calculateMACD } from "@/lib/indicators";

// Historical bars are cached and stable; today's bar (while the market's open) isn't "closed"
// yet, so we splice in the live quote's O/H/L/C purely for display — the cached series itself
// is never touched. Volume isn't in the quote, so we carry forward whatever was last cached.
function mergeLiveCandle(validData: ChartPoint[], livePrice?: TickerPrice): ChartPoint[] {
  if (!livePrice || livePrice.open === null || livePrice.high === null || livePrice.low === null) {
    return validData;
  }
  const liveDate = livePrice.timestamp.slice(0, 10);
  const lastBar = validData[validData.length - 1];

  const liveCandle: ChartPoint = {
    date: liveDate,
    open: livePrice.open,
    high: livePrice.high,
    low: livePrice.low,
    close: livePrice.last,
    volume: lastBar && lastBar.date === liveDate ? lastBar.volume : null,
  };

  if (lastBar && lastBar.date === liveDate) {
    return [...validData.slice(0, -1), liveCandle];
  }
  if (!lastBar || liveDate > lastBar.date) {
    return [...validData, liveCandle];
  }
  return validData;
}

interface PriceChartProps {
  chartData: ChartPoint[];
  livePrice?: TickerPrice;
  error?: string;
}

type IndicatorKey = "volume" | "ma" | "bollinger" | "rsi" | "macd";

const CHIPS: { key: IndicatorKey; label: string; color: string }[] = [
  { key: "volume", label: "Volume", color: "#0891b2" },
  { key: "ma", label: "MA (20/50)", color: "#0891b2" },
  { key: "bollinger", label: "Bollinger", color: "#71717a" },
  { key: "rsi", label: "RSI", color: "#0ea5e9" },
  { key: "macd", label: "MACD", color: "#0ea5e9" },
];

const COLORS = {
  emerald: "#10b981",
  emeraldFaint: "rgba(16,185,129,0.5)",
  rose: "#f43f5e",
  roseFaint: "rgba(244,63,94,0.5)",
  cyan: "#0891b2",
  amber: "#d97706",
  sky: "#0ea5e9",
  zincDashed: "#a1a1aa",
  zincSolid: "#71717a",
};

const MAIN_PANE_HEIGHT = 260;
const SUB_PANE_HEIGHT = 120;

function getThemeColors(isDark: boolean) {
  return {
    background: "transparent",
    textColor: isDark ? "#a1a1aa" : "#71717a",
    gridColor: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)",
  };
}

function fmt(n: number | null | undefined, digits = 2): string {
  return n === null || n === undefined || Number.isNaN(n) ? "—" : n.toFixed(digits);
}

function zipLine(times: string[], values: (number | null)[]) {
  return times
    .map((time, i) => ({ time: time as Time, value: values[i] }))
    .filter((d): d is { time: Time; value: number } => d.value !== null);
}

export default function PriceChart({ chartData, livePrice, error }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const legendRef = useRef<HTMLDivElement | null>(null);

  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const sma20Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const sma50Ref = useRef<ISeriesApi<"Line"> | null>(null);
  const bbUpperRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbMiddleRef = useRef<ISeriesApi<"Line"> | null>(null);
  const bbLowerRef = useRef<ISeriesApi<"Line"> | null>(null);
  const rsiRef = useRef<ISeriesApi<"Line"> | null>(null);
  const rsiPaneAssignedRef = useRef<number | null>(null);
  const macdLineRef = useRef<ISeriesApi<"Line"> | null>(null);
  const macdSignalRef = useRef<ISeriesApi<"Line"> | null>(null);
  const macdHistRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const macdPaneAssignedRef = useRef<number | null>(null);
  const latestDataRef = useRef<ChartPoint[]>([]);
  const heightRef = useRef(MAIN_PANE_HEIGHT);

  const [active, setActive] = useState<Record<IndicatorKey, boolean>>({
    volume: true,
    ma: false,
    bollinger: false,
    rsi: false,
    macd: false,
  });

  const validData = useMemo(() => {
    const historical = chartData.filter((p) => p.open !== null && p.high !== null && p.low !== null && p.close !== null);
    return mergeLiveCandle(historical, livePrice);
  }, [chartData, livePrice]);
  const closes = useMemo(() => validData.map((p) => p.close as number), [validData]);

  const indicators = useMemo(
    () => ({
      sma20: calculateSMA(closes, 20),
      sma50: calculateSMA(closes, 50),
      bb: calculateBollingerBands(closes, 20, 2),
      rsi: calculateRSI(closes, 14),
      macd: calculateMACD(closes, 12, 26, 9),
    }),
    [closes]
  );

  // Effect 1: create/destroy the chart once on mount.
  useEffect(() => {
    if (!containerRef.current) return;
    const theme = getThemeColors(document.documentElement.classList.contains("dark"));

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: MAIN_PANE_HEIGHT,
      layout: { background: { color: theme.background }, textColor: theme.textColor },
      grid: { vertLines: { color: theme.gridColor }, horzLines: { color: theme.gridColor } },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      crosshair: { mode: CrosshairMode.Normal },
    });
    chartRef.current = chart;
    heightRef.current = MAIN_PANE_HEIGHT;

    // We manage height ourselves (per-pane split changes with which indicators are active),
    // so we can't use the library's `autoSize` — it re-normalizes pane proportions on every
    // resize it manages, fighting any custom split. Track width responsiveness manually instead.
    const resizeObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) chart.resize(width, heightRef.current);
    });
    resizeObserver.observe(containerRef.current);

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: COLORS.emerald,
      downColor: COLORS.rose,
      borderVisible: false,
      wickUpColor: COLORS.emerald,
      wickDownColor: COLORS.rose,
    });
    candleSeriesRef.current = candleSeries;

    function renderLegend(bar: { open: number; high: number; low: number; close: number } | null) {
      if (!legendRef.current) return;
      if (!bar) {
        legendRef.current.textContent = "";
        return;
      }
      legendRef.current.textContent = `O ${fmt(bar.open)}  H ${fmt(bar.high)}  L ${fmt(bar.low)}  C ${fmt(bar.close)}`;
    }

    function handleCrosshairMove(param: Parameters<Parameters<IChartApi["subscribeCrosshairMove"]>[0]>[0]) {
      const live = param.time ? (param.seriesData.get(candleSeries) as { open: number; high: number; low: number; close: number } | undefined) : undefined;
      if (live) {
        renderLegend(live);
        return;
      }
      const last = latestDataRef.current[latestDataRef.current.length - 1];
      renderLegend(last ? { open: last.open!, high: last.high!, low: last.low!, close: last.close! } : null);
    }
    chart.subscribeCrosshairMove(handleCrosshairMove);
    handleCrosshairMove({ time: undefined, seriesData: new Map() } as never);

    function handleThemeChange() {
      const t = getThemeColors(document.documentElement.classList.contains("dark"));
      chart.applyOptions({
        layout: { background: { color: t.background }, textColor: t.textColor },
        grid: { vertLines: { color: t.gridColor }, horzLines: { color: t.gridColor } },
      });
    }
    window.addEventListener("theme-change", handleThemeChange);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener("theme-change", handleThemeChange);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      sma20Ref.current = null;
      sma50Ref.current = null;
      bbUpperRef.current = null;
      bbMiddleRef.current = null;
      bbLowerRef.current = null;
      rsiRef.current = null;
      rsiPaneAssignedRef.current = null;
      macdLineRef.current = null;
      macdSignalRef.current = null;
      macdHistRef.current = null;
      macdPaneAssignedRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Effect 2: push candle data whenever it changes.
  useEffect(() => {
    latestDataRef.current = validData;
    if (!candleSeriesRef.current) return;
    candleSeriesRef.current.setData(
      validData.map((p) => ({ time: p.date as Time, open: p.open!, high: p.high!, low: p.low!, close: p.close! }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [validData]);

  // Effect 3: sync toggleable indicator series against current state.
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || validData.length === 0) return;
    const times = validData.map((p) => p.date);

    if (active.volume) {
      if (!volumeSeriesRef.current) {
        const series = chart.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "volume" });
        series.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
        volumeSeriesRef.current = series;
      }
      volumeSeriesRef.current.setData(
        validData.map((p) => ({
          time: p.date as Time,
          value: p.volume ?? 0,
          color: (p.close ?? 0) >= (p.open ?? 0) ? COLORS.emeraldFaint : COLORS.roseFaint,
        }))
      );
    } else if (volumeSeriesRef.current) {
      chart.removeSeries(volumeSeriesRef.current);
      volumeSeriesRef.current = null;
    }

    if (active.ma) {
      if (!sma20Ref.current) {
        sma20Ref.current = chart.addSeries(LineSeries, { color: COLORS.cyan, lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
      }
      if (!sma50Ref.current) {
        sma50Ref.current = chart.addSeries(LineSeries, { color: COLORS.amber, lineWidth: 2, priceLineVisible: false, lastValueVisible: false });
      }
      sma20Ref.current.setData(zipLine(times, indicators.sma20));
      sma50Ref.current.setData(zipLine(times, indicators.sma50));
    } else {
      if (sma20Ref.current) { chart.removeSeries(sma20Ref.current); sma20Ref.current = null; }
      if (sma50Ref.current) { chart.removeSeries(sma50Ref.current); sma50Ref.current = null; }
    }

    if (active.bollinger) {
      if (!bbUpperRef.current) bbUpperRef.current = chart.addSeries(LineSeries, { color: COLORS.zincDashed, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
      if (!bbMiddleRef.current) bbMiddleRef.current = chart.addSeries(LineSeries, { color: COLORS.zincSolid, lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
      if (!bbLowerRef.current) bbLowerRef.current = chart.addSeries(LineSeries, { color: COLORS.zincDashed, lineWidth: 1, lineStyle: LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false });
      bbUpperRef.current.setData(zipLine(times, indicators.bb.map((b) => b.upper)));
      bbMiddleRef.current.setData(zipLine(times, indicators.bb.map((b) => b.middle)));
      bbLowerRef.current.setData(zipLine(times, indicators.bb.map((b) => b.lower)));
    } else {
      [bbUpperRef, bbMiddleRef, bbLowerRef].forEach((ref) => {
        if (ref.current) { chart.removeSeries(ref.current); ref.current = null; }
      });
    }

    // RSI and MACD each want a sub-pane; assign indices 1 then 2 based on who's active,
    // so turning on only MACD doesn't leave a blank pane 1.
    let nextPane = 1;
    const rsiPane = active.rsi ? nextPane++ : null;
    const macdPane = active.macd ? nextPane++ : null;

    if (active.rsi && rsiPane !== null) {
      if (rsiRef.current && rsiPaneAssignedRef.current !== rsiPane) {
        chart.removeSeries(rsiRef.current);
        rsiRef.current = null;
      }
      if (!rsiRef.current) {
        rsiRef.current = chart.addSeries(LineSeries, { color: COLORS.sky, lineWidth: 2 }, rsiPane);
        rsiPaneAssignedRef.current = rsiPane;
        rsiRef.current.createPriceLine({ price: 70, color: COLORS.zincDashed, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: "70" });
        rsiRef.current.createPriceLine({ price: 30, color: COLORS.zincDashed, lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: "30" });
      }
      rsiRef.current.setData(zipLine(times, indicators.rsi));
    } else if (rsiRef.current) {
      chart.removeSeries(rsiRef.current);
      rsiRef.current = null;
      rsiPaneAssignedRef.current = null;
    }

    if (active.macd && macdPane !== null) {
      if (macdLineRef.current && macdPaneAssignedRef.current !== macdPane) {
        chart.removeSeries(macdLineRef.current);
        if (macdSignalRef.current) chart.removeSeries(macdSignalRef.current);
        if (macdHistRef.current) chart.removeSeries(macdHistRef.current);
        macdLineRef.current = null;
        macdSignalRef.current = null;
        macdHistRef.current = null;
      }
      if (!macdLineRef.current) {
        macdLineRef.current = chart.addSeries(LineSeries, { color: COLORS.sky, lineWidth: 2 }, macdPane);
        macdSignalRef.current = chart.addSeries(LineSeries, { color: COLORS.amber, lineWidth: 2 }, macdPane);
        macdHistRef.current = chart.addSeries(HistogramSeries, {}, macdPane);
        macdPaneAssignedRef.current = macdPane;
      }
      macdLineRef.current.setData(zipLine(times, indicators.macd.map((m) => m.macd)));
      macdSignalRef.current!.setData(zipLine(times, indicators.macd.map((m) => m.signal)));
      macdHistRef.current!.setData(
        validData
          .map((p, i) => {
            const h = indicators.macd[i].histogram;
            return h === null ? null : { time: p.date as Time, value: h, color: h >= 0 ? COLORS.emerald : COLORS.rose };
          })
          .filter((d): d is { time: Time; value: number; color: string } => d !== null)
      );
    } else {
      [macdLineRef, macdSignalRef, macdHistRef].forEach((ref) => {
        if (ref.current) { chart.removeSeries(ref.current as never); ref.current = null; }
      });
      macdPaneAssignedRef.current = null;
    }

    const subPaneCount = (active.rsi ? 1 : 0) + (active.macd ? 1 : 0);
    const newHeight = MAIN_PANE_HEIGHT + subPaneCount * SUB_PANE_HEIGHT;
    heightRef.current = newHeight;
    if (containerRef.current) chart.resize(containerRef.current.clientWidth, newHeight);
    // Stretch factors (relative proportions), not setHeight (unreliable pixel-absolute API) —
    // main:sub = MAIN_PANE_HEIGHT:SUB_PANE_HEIGHT, stable regardless of total height changes.
    chart.panes()[0]?.setStretchFactor(MAIN_PANE_HEIGHT / SUB_PANE_HEIGHT);
    if (rsiPane !== null) chart.panes()[rsiPane]?.setStretchFactor(1);
    if (macdPane !== null) chart.panes()[macdPane]?.setStretchFactor(1);
  }, [active, validData, indicators]);

  if (!chartData || chartData.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/60">
        No chart data available.
        {error && <ErrorNotice message={error} />}
      </div>
    );
  }

  const subPaneCount = (active.rsi ? 1 : 0) + (active.macd ? 1 : 0);
  const totalHeight = MAIN_PANE_HEIGHT + subPaneCount * SUB_PANE_HEIGHT;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Price Chart</h3>
        <div className="flex flex-wrap gap-1.5">
          {CHIPS.map((chip) => {
            const isActive = active[chip.key];
            return (
              <button
                key={chip.key}
                onClick={() => setActive((a) => ({ ...a, [chip.key]: !a[chip.key] }))}
                className={
                  isActive
                    ? "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors"
                    : "rounded-full border border-zinc-300 px-2.5 py-1 text-xs font-medium text-zinc-600 transition-colors hover:border-zinc-400 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600"
                }
                style={
                  isActive
                    ? { borderColor: chip.color, color: chip.color, backgroundColor: `${chip.color}1a` }
                    : undefined
                }
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      </div>

      <div ref={legendRef} className="mb-2 h-4 font-mono text-xs text-zinc-500 dark:text-zinc-400" />

      <div ref={containerRef} className="w-full" style={{ height: totalHeight }} />

      {error && <ErrorNotice message={error} />}
    </div>
  );
}
