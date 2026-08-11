"use client";

import { useState } from "react";

interface TickerSearchProps {
  onSearch: (symbol: string) => void;
  loading: boolean;
}

export default function TickerSearch({ onSearch, loading }: TickerSearchProps) {
  const [value, setValue] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const symbol = value.trim().toUpperCase();
    if (symbol) onSearch(symbol);
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full max-w-md gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Enter ticker (e.g. AAPL)"
        className="flex-1 rounded-md border border-zinc-300 px-4 py-2 text-lg uppercase focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-zinc-700 dark:bg-zinc-900"
      />
      <button
        type="submit"
        disabled={loading}
        className="rounded-md bg-blue-600 px-5 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? "Loading…" : "Search"}
      </button>
    </form>
  );
}
