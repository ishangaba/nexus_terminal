// Pure technical-indicator math over close-price arrays. No framework dependency —
// every function is index-aligned to its input so callers can zip results directly
// against a shared date/time array.

export function calculateSMA(closes: (number | null)[], period: number): (number | null)[] {
  const result: (number | null)[] = new Array(closes.length).fill(null);
  for (let i = period - 1; i < closes.length; i++) {
    const window = closes.slice(i - period + 1, i + 1);
    if (window.some((v) => v === null)) continue;
    const sum = (window as number[]).reduce((a, b) => a + b, 0);
    result[i] = sum / period;
  }
  return result;
}

export function calculateEMA(closes: (number | null)[], period: number): (number | null)[] {
  const result: (number | null)[] = new Array(closes.length).fill(null);
  const k = 2 / (period + 1);
  let prevEma: number | null = null;

  for (let i = 0; i < closes.length; i++) {
    if (prevEma === null) {
      if (i < period - 1) continue;
      const window = closes.slice(i - period + 1, i + 1);
      if (window.some((v) => v === null)) continue;
      const sum = (window as number[]).reduce((a, b) => a + b, 0);
      prevEma = sum / period;
      result[i] = prevEma;
      continue;
    }
    const close = closes[i];
    if (close === null) {
      prevEma = null; // gap in data — re-seed from the next available window
      continue;
    }
    prevEma = close * k + prevEma * (1 - k);
    result[i] = prevEma;
  }
  return result;
}

export interface BollingerBand {
  upper: number | null;
  middle: number | null;
  lower: number | null;
}

export function calculateBollingerBands(
  closes: (number | null)[],
  period: number,
  stdDevMultiplier: number
): BollingerBand[] {
  const sma = calculateSMA(closes, period);
  const result: BollingerBand[] = closes.map(() => ({ upper: null, middle: null, lower: null }));

  for (let i = period - 1; i < closes.length; i++) {
    const middle = sma[i];
    if (middle === null) continue;
    const window = closes.slice(i - period + 1, i + 1) as number[];
    const variance = window.reduce((sum, v) => sum + (v - middle) ** 2, 0) / period;
    const stddev = Math.sqrt(variance);
    result[i] = {
      middle,
      upper: middle + stdDevMultiplier * stddev,
      lower: middle - stdDevMultiplier * stddev,
    };
  }
  return result;
}

function rsiFromAverages(avgGain: number, avgLoss: number): number {
  if (avgLoss === 0) return 100;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

// Wilder's smoothing — the standard RSI method (unqualified "RSI" always means this).
export function calculateRSI(closes: (number | null)[], period: number): (number | null)[] {
  const result: (number | null)[] = new Array(closes.length).fill(null);

  let avgGain: number | null = null;
  let avgLoss: number | null = null;
  let gainSum = 0;
  let lossSum = 0;
  let seededDeltas = 0;

  for (let i = 1; i < closes.length; i++) {
    const prev = closes[i - 1];
    const curr = closes[i];
    if (prev === null || curr === null) {
      avgGain = null;
      avgLoss = null;
      gainSum = 0;
      lossSum = 0;
      seededDeltas = 0;
      continue;
    }

    const delta = curr - prev;
    const gain = delta > 0 ? delta : 0;
    const loss = delta < 0 ? -delta : 0;

    if (avgGain === null || avgLoss === null) {
      gainSum += gain;
      lossSum += loss;
      seededDeltas++;
      if (seededDeltas === period) {
        avgGain = gainSum / period;
        avgLoss = lossSum / period;
        result[i] = rsiFromAverages(avgGain, avgLoss);
      }
      continue;
    }

    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    result[i] = rsiFromAverages(avgGain, avgLoss);
  }

  return result;
}

export interface MACDResult {
  macd: number | null;
  signal: number | null;
  histogram: number | null;
}

// Gerald Appel's original parameters (12/26/9) are the universal default — rarely customized.
export function calculateMACD(
  closes: (number | null)[],
  fastPeriod: number,
  slowPeriod: number,
  signalPeriod: number
): MACDResult[] {
  const fastEMA = calculateEMA(closes, fastPeriod);
  const slowEMA = calculateEMA(closes, slowPeriod);

  const macdLine: (number | null)[] = closes.map((_, i) => {
    const f = fastEMA[i];
    const s = slowEMA[i];
    return f !== null && s !== null ? f - s : null;
  });

  const signalLine = calculateEMA(macdLine, signalPeriod);

  return closes.map((_, i) => {
    const macd = macdLine[i];
    const signal = signalLine[i];
    return {
      macd,
      signal,
      histogram: macd !== null && signal !== null ? macd - signal : null,
    };
  });
}
