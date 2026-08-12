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
  open: number | null;
  high: number | null;
  low: number | null;
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

export interface TickerContext {
  symbol: string;
  price: TickerPrice;
  fundamentals: TickerFundamentals;
  chart_data: ChartPoint[];
  news: NewsItem[];
  filings: Filing[];
  errors?: Record<string, string>;
}

export interface WatchlistQuote {
  symbol: string;
  last: number | null;
  change: number | null;
  change_pct: number | null;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "Company" | "GovEntity" | string;
  symbol: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "SUBSIDIARY_OF" | "HAS_CONTRACT" | "SUPPLIES_TO" | "COMPETES_WITH" | "PARTNERS_WITH" | string;
  amount?: number | null;
  date?: string | null;
  evidence?: string | null;
}

export interface CompanyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed with status ${res.status}`);
  }
  return res.json();
}

export async function fetchTicker(symbol: string): Promise<TickerContext> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}`);
  return handleResponse<TickerContext>(res);
}

export async function fetchBrief(symbol: string, context: Omit<TickerContext, "symbol" | "chart_data">): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}/brief`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(context),
  });
  const data = await handleResponse<{ ai_brief: string }>(res);
  return data.ai_brief;
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

export async function fetchGraph(symbol: string): Promise<CompanyGraph> {
  const res = await fetch(`${API_BASE}/api/v1/graph/${encodeURIComponent(symbol)}`);
  return handleResponse<CompanyGraph>(res);
}

export async function fetchGraphInsights(symbol: string, graph: CompanyGraph): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/graph/${encodeURIComponent(symbol)}/insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(graph),
  });
  const data = await handleResponse<{ insights: string }>(res);
  return data.insights;
}

export async function askAboutTicker(symbol: string, question: string, graph?: CompanyGraph | null): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/ask/${encodeURIComponent(symbol)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, graph: graph ?? null }),
  });
  const data = await handleResponse<{ answer: string }>(res);
  return data.answer;
}

export type SettingsKey = "alpha_vantage_api_key" | "finnhub_api_key" | "anthropic_api_key" | "marketaux_api_key";

export interface SettingStatus {
  label: string;
  configured: boolean;
  masked: string | null;
}

export type SettingsStatus = Record<SettingsKey, SettingStatus>;

export async function fetchSettings(): Promise<SettingsStatus> {
  const res = await fetch(`${API_BASE}/api/v1/settings`);
  return handleResponse<SettingsStatus>(res);
}

export async function saveSettings(updates: Partial<Record<SettingsKey, string>>): Promise<SettingsStatus> {
  const res = await fetch(`${API_BASE}/api/v1/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  return handleResponse<SettingsStatus>(res);
}

export async function clearSetting(key: SettingsKey): Promise<SettingsStatus> {
  const res = await fetch(`${API_BASE}/api/v1/settings/${key}`, { method: "DELETE" });
  return handleResponse<SettingsStatus>(res);
}
