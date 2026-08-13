"use client";

import { useEffect, useRef, useState } from "react";
import { searchTickers, TickerSearchResult } from "@/lib/api";

interface TickerSearchProps {
  onSearch: (symbol: string) => void;
  loading: boolean;
}

const DEBOUNCE_MS = 300;

export default function TickerSearch({ onSearch, loading }: TickerSearchProps) {
  const [value, setValue] = useState("");
  const [results, setResults] = useState<TickerSearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const [highlighted, setHighlighted] = useState(-1);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const skipNextSearch = useRef(false);

  useEffect(() => {
    const trimmed = value.trim();
    if (skipNextSearch.current) {
      skipNextSearch.current = false;
      return;
    }
    if (!trimmed) {
      setResults([]);
      setOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const matches = await searchTickers(trimmed);
        setResults(matches);
        setOpen(matches.length > 0);
        setHighlighted(-1);
      } catch {
        // silent — typeahead is a convenience, not critical; typing a symbol and hitting
        // Search still works even if the lookup call fails
        setResults([]);
        setOpen(false);
      } finally {
        setSearching(false);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [value]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function selectResult(result: TickerSearchResult) {
    skipNextSearch.current = true;
    setValue(result.symbol);
    setOpen(false);
    setResults([]);
    onSearch(result.symbol);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (open && highlighted >= 0 && results[highlighted]) {
      selectResult(results[highlighted]);
      return;
    }
    const symbol = value.trim().toUpperCase();
    if (symbol) {
      setOpen(false);
      onSearch(symbol);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((i) => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((i) => (i <= 0 ? results.length - 1 : i - 1));
    } else if (e.key === "Escape") {
      setOpen(false);
      setHighlighted(-1);
    }
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => results.length > 0 && setOpen(true)}
            placeholder="Search by ticker or company name (e.g. AAPL or Apple)"
            autoComplete="off"
            role="combobox"
            aria-expanded={open}
            aria-autocomplete="list"
            className="w-full rounded-md border border-zinc-300 bg-white px-4 py-2 text-lg text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100 dark:placeholder:text-zinc-600"
          />
          {searching && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400 dark:text-zinc-600">
              …
            </span>
          )}

          {open && results.length > 0 && (
            <ul className="absolute z-20 mt-1 w-full overflow-hidden rounded-md border border-zinc-200 bg-white shadow-lg dark:border-zinc-700 dark:bg-zinc-900">
              {results.map((result, i) => (
                <li key={result.symbol}>
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => selectResult(result)}
                    onMouseEnter={() => setHighlighted(i)}
                    className={`flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm ${
                      i === highlighted
                        ? "bg-cyan-50 dark:bg-cyan-950/40"
                        : "hover:bg-zinc-50 dark:hover:bg-zinc-800/60"
                    }`}
                  >
                    <span className="font-mono font-medium text-zinc-900 dark:text-zinc-100">{result.symbol}</span>
                    <span className="truncate text-zinc-500 dark:text-zinc-400">{result.description}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-gradient-to-r from-cyan-600 to-cyan-500 px-5 py-2 font-medium text-white shadow-sm hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50"
        >
          {loading ? "Loading…" : "Search"}
        </button>
      </form>
    </div>
  );
}
