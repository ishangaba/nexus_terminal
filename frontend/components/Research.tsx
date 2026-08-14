"use client";

import { useState } from "react";
import { askResearch, ResearchQueryResponse, ResearchStance } from "@/lib/api";
import { decodeHtmlEntities } from "@/lib/text";

interface ResearchProps {
  symbol: string;
}

const STANCE_LABEL: Record<ResearchStance, string> = {
  strong_bullish: "STRONG BULLISH",
  bullish: "BULLISH",
  neutral: "NEUTRAL",
  bearish: "BEARISH",
  strong_bearish: "STRONG BEARISH",
};

const STANCE_STYLE: Record<ResearchStance, string> = {
  strong_bullish: "bg-emerald-700 text-white",
  bullish: "bg-emerald-600 text-white",
  neutral: "bg-zinc-500 text-white",
  bearish: "bg-rose-600 text-white",
  strong_bearish: "bg-rose-700 text-white",
};

const TOOL_LABELS: Record<string, string> = {
  technical: "Technical",
  news: "News",
  fundamentals: "Fundamentals",
  sec_filings: "SEC Filings",
  earnings: "Earnings",
  macro: "Macro",
};

function FactorList({ title, items, sign }: { title: string; items: string[]; sign: "+" | "-" }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h4 className="mb-1 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">{title}</h4>
      <ul className="space-y-1 text-sm text-zinc-700 dark:text-zinc-300">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2">
            <span className={sign === "+" ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"}>
              {sign}
            </span>
            <span>{decodeHtmlEntities(item)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Research({ symbol }: ResearchProps) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<ResearchQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await askResearch(symbol, trimmed);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to research this question");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-lg border border-violet-200 bg-violet-50 p-6 dark:border-violet-900/60 dark:bg-violet-950/20 dark:shadow-[0_0_24px_-8px_rgba(167,139,250,0.25)]">
      <h3 className="mb-3 flex items-center gap-1.5 text-sm font-medium text-violet-700 dark:text-violet-400">
        <span aria-hidden>✦</span> Research
      </h3>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={`e.g. Why did ${symbol} move this week? Is it overvalued?`}
          maxLength={500}
          className="flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="rounded-md bg-gradient-to-r from-violet-600 to-violet-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:from-violet-500 hover:to-violet-400 disabled:opacity-50"
        >
          {loading ? "Researching…" : "Research"}
        </button>
      </form>

      {error && <p className="mt-3 text-sm text-rose-600 dark:text-rose-400">{error}</p>}

      {!result && !error && !loading && (
        <p className="mt-3 text-sm text-zinc-500 dark:text-zinc-500">
          Ask a specific question — deterministic tools (technical, fundamentals, SEC filings,
          earnings/insider/analyst data, macro backdrop) run based on what your question actually
          needs, then Claude synthesizes only the evidence those tools produced.
        </p>
      )}

      {result && (
        <div className="mt-4 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-md px-3 py-1 text-sm font-bold tracking-wide ${STANCE_STYLE[result.thesis.stance]}`}
            >
              {STANCE_LABEL[result.thesis.stance]}
            </span>
            <span className="text-xs uppercase text-zinc-500 dark:text-zinc-400">
              {(result.thesis.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>

          <p className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
            {decodeHtmlEntities(result.thesis.executive_summary)}
          </p>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FactorList title="Bullish factors" items={result.thesis.bullish_factors} sign="+" />
            <FactorList title="Bearish factors" items={result.thesis.bearish_factors} sign="-" />
          </div>

          {result.thesis.catalysts.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">Catalysts</h4>
              <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
                {result.thesis.catalysts.map((c, i) => (
                  <li key={i}>{decodeHtmlEntities(c)}</li>
                ))}
              </ul>
            </div>
          )}

          {result.thesis.key_risks.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">Key Risks</h4>
              <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
                {result.thesis.key_risks.map((r, i) => (
                  <li key={i}>{decodeHtmlEntities(r)}</li>
                ))}
              </ul>
            </div>
          )}

          {result.thesis.invalidation_conditions.length > 0 && (
            <div>
              <h4 className="mb-1 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">
                Would Change This View
              </h4>
              <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
                {result.thesis.invalidation_conditions.map((c, i) => (
                  <li key={i}>{decodeHtmlEntities(c)}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 border-t border-violet-200/60 pt-3 text-xs text-zinc-400 dark:border-violet-900/40 dark:text-zinc-600">
            <span>
              Tools used:{" "}
              {result.tools_used.map((t) => TOOL_LABELS[t] ?? t).join(", ")}
            </span>
            <span>·</span>
            <span>{result.thesis.evidence_ids.length} evidence points</span>
          </div>
        </div>
      )}
    </div>
  );
}
