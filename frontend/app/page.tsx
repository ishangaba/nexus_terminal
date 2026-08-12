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
import { addToWatchlist, fetchBrief, fetchTicker, TickerContext } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<TickerContext | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [brief, setBrief] = useState<string | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);

  const [watchlistRefresh, setWatchlistRefresh] = useState(0);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);
  const [onWatchlist, setOnWatchlist] = useState(false);

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
            <ThemeToggle />
          </div>
        </header>

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
              <PriceCard symbol={data.symbol} price={data.price} fundamentals={data.fundamentals} />
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
                <PriceChart chartData={data.chart_data} />
              </div>
              <SentimentGauge news={data.news} />

              <div className="flex flex-col gap-6 lg:col-span-2">
                <AIBrief brief={brief} loading={briefLoading} error={briefError} />
                <AskBox symbol={data.symbol} />
              </div>
              <Filings filings={data.filings} />

              <div className="lg:col-span-3">
                <NewsFeed news={data.news} />
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
