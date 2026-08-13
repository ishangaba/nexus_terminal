import { ChartPoint } from "./api";
import { calculateSMA, calculateRSI, calculateBollingerBands, calculateMACD } from "./indicators";

export interface TechnicalSnapshot {
  last_close: number | null;
  sma20: number | null;
  sma50: number | null;
  rsi14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  bollinger_upper: number | null;
  bollinger_middle: number | null;
  bollinger_lower: number | null;
}

function lastNonNull<T>(arr: (T | null)[]): T | null {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i] !== null) return arr[i];
  }
  return null;
}

// Grounded in chart_data's confirmed daily closes (not a live intraday tick) — a signal
// grounded in confirmed closes is more defensible than one grounded in a still-moving price.
export function buildTechnicalSnapshot(chartData: ChartPoint[]): TechnicalSnapshot {
  const closes = chartData.map((p) => p.close);
  const sma20 = calculateSMA(closes, 20);
  const sma50 = calculateSMA(closes, 50);
  const rsi14 = calculateRSI(closes, 14);
  const macd = calculateMACD(closes, 12, 26, 9);
  const bb = calculateBollingerBands(closes, 20, 2);

  return {
    last_close: lastNonNull(closes),
    sma20: lastNonNull(sma20),
    sma50: lastNonNull(sma50),
    rsi14: lastNonNull(rsi14),
    macd: lastNonNull(macd.map((m) => m.macd)),
    macd_signal: lastNonNull(macd.map((m) => m.signal)),
    macd_histogram: lastNonNull(macd.map((m) => m.histogram)),
    bollinger_upper: lastNonNull(bb.map((b) => b.upper)),
    bollinger_middle: lastNonNull(bb.map((b) => b.middle)),
    bollinger_lower: lastNonNull(bb.map((b) => b.lower)),
  };
}
