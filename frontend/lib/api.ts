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

export interface Filing {
  form: string;
  filed_date: string;
  url: string;
}

export interface TickerSnapshot {
  symbol: string;
  price: TickerPrice;
  fundamentals: TickerFundamentals;
  chart_data: ChartPoint[];
  news: NewsItem[];
  filings: Filing[];
  ai_brief: string;
}

export interface WatchlistQuote {
  symbol: string;
  last: number | null;
  change: number | null;
  change_pct: number | null;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchTicker(symbol: string): Promise<TickerSnapshot> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}`);
  return handleResponse<TickerSnapshot>(res);
}

export async function fetchWatchlist(): Promise<WatchlistQuote[]> {
  const res = await fetch(`${API_BASE}/api/v1/watchlist`);
  const data = await handleResponse<{ watchlist: WatchlistQuote[] }>(res);
  return data.watchlist;
}

export async function addToWatchlist(symbol: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/watchlist/${encodeURIComponent(symbol)}`, { method: "POST" });
  await handleResponse(res);
}

export async function removeFromWatchlist(symbol: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/watchlist/${encodeURIComponent(symbol)}`, { method: "DELETE" });
  await handleResponse(res);
}

export async function askAboutTicker(symbol: string, question: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/ask/${encodeURIComponent(symbol)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const data = await handleResponse<{ answer: string }>(res);
  return data.answer;
}
