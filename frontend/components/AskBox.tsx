"use client";

import { useState } from "react";
import { askAboutTicker } from "@/lib/api";
import { decodeHtmlEntities } from "@/lib/text";

interface AskBoxProps {
  symbol: string;
}

export default function AskBox({ symbol }: AskBoxProps) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setAnswer(null);
    try {
      const result = await askAboutTicker(symbol, trimmed);
      setAnswer(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get an answer");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <h3 className="mb-3 flex items-center gap-1.5 text-sm font-medium text-zinc-500 dark:text-zinc-400">
        <span aria-hidden className="text-violet-500 dark:text-violet-400">✦</span> Ask about {symbol}
      </h3>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={`e.g. What's driving ${symbol} today?`}
          maxLength={500}
          className="flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="rounded-md bg-gradient-to-r from-violet-600 to-violet-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:from-violet-500 hover:to-violet-400 disabled:opacity-50"
        >
          {loading ? "Thinking…" : "Ask"}
        </button>
      </form>

      {error && <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{error}</p>}
      {answer && (
        <p className="mt-3 text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">{decodeHtmlEntities(answer)}</p>
      )}
    </div>
  );
}
