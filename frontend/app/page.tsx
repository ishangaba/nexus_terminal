"use client";

import { useState } from "react";
import TickerSearch from "@/components/TickerSearch";
import PriceCard from "@/components/PriceCard";
import PriceChart from "@/components/PriceChart";
import NewsFeed from "@/components/NewsFeed";
import AIBrief from "@/components/AIBrief";
import Watchlist from "@/components/Watchlist";
import Skeleton from "@/components/Skeleton";
import Filings from "@/components/Filings";
import AskBox from "@/components/AskBox";
import SentimentGauge from "@/components/SentimentGauge";
import MarketStatus from "@/components/MarketStatus";
import ThemeToggle from "@/components/ThemeToggle";
import Logo from "@/components/Logo";
import Hero from "@/components/Hero";
import GraphView from "@/components/GraphView";
import SettingsPanel from "@/components/SettingsPanel";
import {
  addToWatchlist,
  fetchBrief,
  fetchGraph,
  fetchGraphInsights,
  fetchTicker,
  CompanyGraph,
  TickerContext,
} from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<TickerContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [brief, setBrief] = useState<string | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);

  const [graph, setGraph] = useState<CompanyGraph | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphError, setGraphError] = useState<string | null>(null);

  const [graphInsights, setGraphInsights] = useState<string | null>(null);
  const [graphInsightsLoading, setGraphInsightsLoading] = useState(false);

  const [watchlistRefresh, setWatchlistRefresh] = useState(0);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);
  const [onWatchlist, setOnWatchlist] = useState(false);

  const [showSettings, setShowSettings] = useState(false);

  async function loadBrief(context: TickerContext) {
    setBriefLoading(true);
    setBriefError(null);
    setBrief(null);
    try {
      const result = await fetchBrief(context.symbol, {
        price: context.price,
        fundamentals: context.fundamentals,
        news: context.news,
        filings: context.filings,
      });
      setBrief(result);
    } catch (err) {
      setBriefError(err instanceof Error ? err.message : "Failed to generate AI brief");
    } finally {
      setBriefLoading(false);
    }
  }

  async function loadGraph(symbol: string) {
    setGraphLoading(true);
    setGraphError(null);
    setGraph(null);
    setGraphInsights(null);
    try {
      const result = await fetchGraph(symbol);
      setGraph(result);
      if (result.nodes.length > 1) loadGraphInsights(symbol, result);
    } catch (err) {
      setGraphError(err instanceof Error ? err.message : "Failed to load company graph");
    } finally {
      setGraphLoading(false);
    }
  }

  async function loadGraphInsights(symbol: string, companyGraph: CompanyGraph) {
    setGraphInsightsLoading(true);
    try {
      const result = await fetchGraphInsights(symbol, companyGraph);
      setGraphInsights(result);
    } catch {
      // non-critical; the graph visualization still stands on its own
    } finally {
      setGraphInsightsLoading(false);
    }
  }

  async function handleSearch(symbol: string, isRefresh = false) {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
      setData(null);
    }
    setError(null);
    setOnWatchlist(false);

    try {
      const context = await fetchTicker(symbol);
      setData(context);
      loadBrief(context);
      if (!isRefresh) loadGraph(context.symbol);
    } catch (err) {
      if (!isRefresh) setData(null);
      setError(err instanceof Error ? err.message : "Something went wrong. Check that the backend is running.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function handleAddToWatchlist() {
    if (!data) return;
    setAddingToWatchlist(true);
    try {
      await addToWatchlist(data.symbol);
      setOnWatchlist(true);
      setWatchlistRefresh((n) => n + 1);
    } catch {
      // no-op; button stays actionable for retry
    } finally {
      setAddingToWatchlist(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-8 sm:px-6 sm:py-10">
      <main className="mx-auto flex max-w-6xl flex-col gap-6">
        <header className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Logo size={30} />
            <h1 className="bg-gradient-to-r from-cyan-500 to-violet-500 bg-clip-text text-2xl font-semibold text-transparent dark:from-cyan-400 dark:to-violet-400">
              Nexus Terminal
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <MarketStatus />
            <button
              onClick={() => setShowSettings(true)}
              aria-label="Open settings"
              title="API key settings"
              className="rounded-full border border-zinc-200 p-1.5 text-zinc-500 hover:border-zinc-300 hover:text-zinc-700 dark:border-zinc-700 dark:text-zinc-400 dark:hover:border-zinc-600 dark:hover:text-zinc-200"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} className="h-4 w-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            <ThemeToggle />
          </div>
        </header>

        {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}

        <TickerSearch onSearch={handleSearch} loading={loading} />

        <Watchlist onSelect={handleSearch} refreshKey={watchlistRefresh} />

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-400">
            {error}
          </div>
        )}

        {loading && <Skeleton />}

        {!loading && !data && !error && <Hero onQuickStart={handleSearch} />}

        {!loading && data && (
          <div className="flex flex-col gap-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <PriceCard
                symbol={data.symbol}
                price={data.price}
                fundamentals={data.fundamentals}
                fundamentalsError={data.errors?.fundamentals}
              />
              <div className="flex gap-2">
                <button
                  onClick={() => handleSearch(data.symbol, true)}
                  disabled={refreshing}
                  className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
                >
                  {refreshing ? "Refreshing…" : "↻ Refresh"}
                </button>
                <button
                  onClick={handleAddToWatchlist}
                  disabled={addingToWatchlist || onWatchlist}
                  className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
                >
                  {onWatchlist ? "Added to watchlist" : addingToWatchlist ? "Adding…" : `+ Add to watchlist`}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="lg:col-span-2">
                <PriceChart chartData={data.chart_data} error={data.errors?.chart_data} />
              </div>
              <SentimentGauge news={data.news} />

              <div className="flex flex-col gap-6 lg:col-span-2">
                <AIBrief brief={brief} loading={briefLoading} error={briefError} />
                <AskBox symbol={data.symbol} graph={graph} />
              </div>
              <Filings filings={data.filings} error={data.errors?.filings} />

              <div className="lg:col-span-3">
                {graphLoading && (
                  <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/60">
                    <span className="flex items-center gap-1.5">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-cyan-500" />
                      Building company graph (subsidiaries, gov contracts, related companies)… this can take
                      up to ~20s the first time, then it&apos;s cached for a week.
                    </span>
                  </div>
                )}
                {!graphLoading && graphError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-400">
                    {graphError}
                  </div>
                )}
                {!graphLoading && !graphError && graph && (
                  <GraphView
                    graph={graph}
                    centerSymbol={data.symbol}
                    onSelect={handleSearch}
                    insights={graphInsights}
                    insightsLoading={graphInsightsLoading}
                  />
                )}
              </div>

              <div className="lg:col-span-3">
                <NewsFeed news={data.news} error={data.errors?.news} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
