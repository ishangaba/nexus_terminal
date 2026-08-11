const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface TickerPrice {
  last: number;
  change: number;
  change_pct: number;
  timestamp: string;
}

export interface TickerFundamentals {
  pe_ratio: number | null;
  market_cap: number | null;
  eps: number | null;
  "52_week_high": number | null;
  "52_week_low": number | null;
}

export interface ChartPoint {
  date: string;
  close: number | null;
}

export interface NewsItem {
  headline: string;
  source: string;
  published_at: string | null;
  sentiment_score: number | null;
  url: string;
}

export interface TickerSnapshot {
  symbol: string;
  price: TickerPrice;
  fundamentals: TickerFundamentals;
  chart_data: ChartPoint[];
  news: NewsItem[];
  ai_brief: string;
}

export async function fetchTicker(symbol: string): Promise<TickerSnapshot> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with status ${res.status}`);
  }
  return res.json();
}
