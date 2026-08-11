"use client";

import { useState } from "react";
import TickerSearch from "@/components/TickerSearch";
import PriceCard from "@/components/PriceCard";
import PriceChart from "@/components/PriceChart";
import NewsFeed from "@/components/NewsFeed";
import AIBrief from "@/components/AIBrief";
import { fetchTicker, TickerSnapshot } from "@/lib/api";

export default function Home() {
  const [data, setData] = useState<TickerSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(symbol: string) {
    setLoading(true);
    setError(null);
    try {
      const snapshot = await fetchTicker(symbol);
      setData(snapshot);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 px-6 py-12 dark:bg-black">
      <main className="mx-auto flex max-w-3xl flex-col items-center gap-8">
        <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50">Nexus Terminal</h1>
        <TickerSearch onSearch={handleSearch} loading={loading} />

        {error && <p className="text-red-600 dark:text-red-400">{error}</p>}

        {data && (
          <div className="w-full space-y-6">
            <PriceCard symbol={data.symbol} price={data.price} fundamentals={data.fundamentals} />
            <PriceChart chartData={data.chart_data} />
            <AIBrief brief={data.ai_brief} />
            <NewsFeed news={data.news} />
          </div>
        )}
      </main>
    </div>
  );
}
