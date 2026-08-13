import type { TechnicalSnapshot } from "./technicalSnapshot";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface TickerPrice {
  last: number;
  change: number;
  change_pct: number;
  open: number | null;
  high: number | null;
  low: number | null;
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
  volume: number | null;
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

export interface TickerSearchResult {
  symbol: string;
  description: string;
}

export async function searchTickers(query: string): Promise<TickerSearchResult[]> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/search?q=${encodeURIComponent(query)}`);
  const data = await handleResponse<{ results: TickerSearchResult[] }>(res);
  return data.results;
}

export async function fetchLivePrice(symbol: string): Promise<TickerPrice> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}/price`);
  return handleResponse<TickerPrice>(res);
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

export type SignalDecision = "accepted" | "rejected";
export type SignalOutcome = "correct" | "incorrect" | "mixed";

export interface TradeSignal {
  id: number;
  symbol: string;
  direction: "bullish" | "bearish" | "neutral";
  action: "buy_call" | "buy_put" | "stay_out";
  confidence: "low" | "medium" | "high";
  summary: string;
  reasoning: string[];
  key_risks: string[];
  note: string;
  user_decision: SignalDecision | null;
  user_outcome: SignalOutcome | null;
  auto_outcome: "correct" | "incorrect" | null;
}

export interface SignalHistoryEntry {
  id: number;
  symbol: string;
  generated_at: string;
  direction: TradeSignal["direction"];
  action: TradeSignal["action"];
  confidence: TradeSignal["confidence"];
  summary: string;
  reasoning: string[];
  key_risks: string[];
  price_at_signal: number;
  user_decision: SignalDecision | null;
  user_outcome: SignalOutcome | null;
  user_notes: string | null;
  auto_outcome: "correct" | "incorrect" | null;
  auto_resolved_at: string | null;
  resolution_price: number | null;
  evaluation_days: number;
}

export interface TrackRecord {
  resolved_count: number;
  correct_count: number;
  incorrect_count: number;
}

export interface SignalHistoryResponse {
  signals: SignalHistoryEntry[];
  track_record: TrackRecord;
}

export async function fetchTradeSignal(
  symbol: string,
  context: Omit<TickerContext, "symbol" | "chart_data">,
  technicalIndicators: TechnicalSnapshot
): Promise<TradeSignal> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}/signal`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...context, technical_indicators: technicalIndicators }),
  });
  return handleResponse<TradeSignal>(res);
}

export async function recordSignalDecision(
  symbol: string,
  signalId: number,
  decision: SignalDecision
): Promise<SignalHistoryEntry> {
  const res = await fetch(
    `${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}/signal/${signalId}/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ decision }),
    }
  );
  return handleResponse<SignalHistoryEntry>(res);
}

export async function recordSignalOutcome(
  symbol: string,
  signalId: number,
  outcome: SignalOutcome,
  notes?: string
): Promise<SignalHistoryEntry> {
  const res = await fetch(
    `${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}/signal/${signalId}/outcome`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outcome, notes }),
    }
  );
  return handleResponse<SignalHistoryEntry>(res);
}

export async function askAboutSignal(
  symbol: string,
  signalId: number,
  context: Omit<TickerContext, "symbol" | "chart_data">,
  technicalIndicators: TechnicalSnapshot,
  question: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}/signal/${signalId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...context, technical_indicators: technicalIndicators, question }),
  });
  const data = await handleResponse<{ answer: string }>(res);
  return data.answer;
}

export async function fetchSignalHistory(symbol: string): Promise<SignalHistoryResponse> {
  const res = await fetch(`${API_BASE}/api/v1/ticker/${encodeURIComponent(symbol)}/signal/history`);
  return handleResponse<SignalHistoryResponse>(res);
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

export type PositionSide = "long";

export interface OpenPosition {
  id: number;
  symbol: string;
  side: PositionSide;
  quantity: number;
  entry_price: number;
  entry_date: string;
  notes: string | null;
  sector: string;
  last_price: number | null;
  market_value: number | null;
  cost_basis: number;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  quote_error: string | null;
}

export interface ClosedPosition {
  id: number;
  symbol: string;
  side: PositionSide;
  quantity: number;
  entry_price: number;
  entry_date: string;
  exit_price: number;
  exit_date: string;
  notes: string | null;
  realized_pnl: number;
  realized_pnl_pct: number | null;
}

export interface PortfolioSummary {
  total_market_value: number;
  total_cost_basis: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  total_realized_pnl: number;
  open_position_count: number;
  closed_position_count: number;
}

export interface AllocationEntry {
  name: string;
  market_value: number;
  pct_of_portfolio: number;
}

export interface PortfolioData {
  summary: PortfolioSummary;
  open_positions: OpenPosition[];
  closed_positions: ClosedPosition[];
  allocation: { by_symbol: AllocationEntry[]; by_sector: AllocationEntry[] };
}

export interface PositionCreateInput {
  symbol: string;
  quantity: number;
  entry_price: number;
  entry_date: string;
  notes?: string;
}

export interface PositionCloseInput {
  exit_price: number;
  exit_date: string;
}

export async function fetchPortfolio(): Promise<PortfolioData> {
  const res = await fetch(`${API_BASE}/api/v1/portfolio`);
  return handleResponse<PortfolioData>(res);
}

export async function createPosition(input: PositionCreateInput): Promise<OpenPosition> {
  const res = await fetch(`${API_BASE}/api/v1/portfolio/positions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<OpenPosition>(res);
}

export async function closePosition(id: number, input: PositionCloseInput): Promise<ClosedPosition> {
  const res = await fetch(`${API_BASE}/api/v1/portfolio/positions/${id}/close`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse<ClosedPosition>(res);
}

export async function deletePosition(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/portfolio/positions/${id}`, { method: "DELETE" });
  await handleResponse(res);
}
