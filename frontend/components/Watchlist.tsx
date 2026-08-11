"use client";

import { useEffect, useState } from "react";
import { fetchWatchlist, removeFromWatchlist, WatchlistQuote } from "@/lib/api";

interface WatchlistProps {
  onSelect: (symbol: string) => void;
  refreshKey: number;
}

export default function Watchlist({ onSelect, refreshKey }: WatchlistProps) {
  const [items, setItems] = useState<WatchlistQuote[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await fetchWatchlist();
      setItems(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load watchlist");
    }
  }

  useEffect(() => {
    load();
  }, [refreshKey]);

  async function handleRemove(symbol: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await removeFromWatchlist(symbol);
      setItems((prev) => prev?.filter((item) => item.symbol !== symbol) ?? null);
    } catch {
      // leave the item in place; user can retry
    }
  }

  if (error) {
    return <p className="text-sm text-red-600 dark:text-red-400">{error}</p>;
  }

  if (!items) {
    return <p className="text-sm text-zinc-500">Loading watchlist…</p>;
  }

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm text-zinc-500 dark:border-zinc-700">
        Your watchlist is empty. Search a ticker and add it below.
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
      <h3 className="mb-3 text-sm font-medium text-zinc-500">Watchlist</h3>
      <ul className="flex flex-wrap gap-2">
        {items.map((item) => {
          const isUp = (item.change ?? 0) >= 0;
          return (
            <li key={item.symbol}>
              <button
                onClick={() => onSelect(item.symbol)}
                className="group flex items-center gap-2 rounded-full border border-zinc-200 px-3 py-1.5 text-sm hover:border-blue-400 dark:border-zinc-700"
              >
                <span className="font-medium text-zinc-900 dark:text-zinc-50">{item.symbol}</span>
                {item.last !== null && (
                  <span className={isUp ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}>
                    {item.change_pct !== null ? `${isUp ? "+" : ""}${item.change_pct.toFixed(2)}%` : "—"}
                  </span>
                )}
                <span
                  onClick={(e) => handleRemove(item.symbol, e)}
                  className="ml-1 text-zinc-400 opacity-0 group-hover:opacity-100 hover:text-red-500"
                  aria-label={`Remove ${item.symbol} from watchlist`}
                >
                  ×
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
