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
import { addToWatchlist, fetchTicker, TickerSnapshot } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<TickerSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watchlistRefresh, setWatchlistRefresh] = useState(0);
  const [addingToWatchlist, setAddingToWatchlist] = useState(false);
  const [onWatchlist, setOnWatchlist] = useState(false);

  async function handleSearch(symbol: string) {
    setLoading(true);
    setError(null);
    setOnWatchlist(false);
    try {
      const snapshot = await fetchTicker(symbol);
      setData(snapshot);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Something went wrong. Check that the backend is running.");
    } finally {
      setLoading(false);
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
    <div className="min-h-screen bg-zinc-50 px-6 py-12 dark:bg-black">
      <main className="mx-auto flex max-w-3xl flex-col items-center gap-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Nexus Terminal</h1>
        <TickerSearch onSearch={handleSearch} loading={loading} />

        <div className="w-full">
          <Watchlist onSelect={handleSearch} refreshKey={watchlistRefresh} />
        </div>

        {error && (
          <div className="w-full rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-400">
            {error}
          </div>
        )}

        {loading && <Skeleton />}

        {!loading && data && (
          <div className="w-full space-y-6">
            <div className="flex items-center justify-between">
              <PriceCard symbol={data.symbol} price={data.price} fundamentals={data.fundamentals} />
            </div>
            <button
              onClick={handleAddToWatchlist}
              disabled={addingToWatchlist || onWatchlist}
              className="self-start rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
            >
              {onWatchlist ? "Added to watchlist" : addingToWatchlist ? "Adding…" : `+ Add ${data.symbol} to watchlist`}
            </button>
            <PriceChart chartData={data.chart_data} />
            <AIBrief brief={data.ai_brief} />
            <AskBox symbol={data.symbol} />
            <Filings filings={data.filings} />
            <NewsFeed news={data.news} />
          </div>
        )}
      </main>
    </div>
  );
}
