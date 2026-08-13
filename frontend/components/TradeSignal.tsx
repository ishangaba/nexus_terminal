"use client";

import { useState } from "react";
import {
  askAboutSignal,
  fetchSignalHistory,
  fetchTradeSignal,
  recordSignalDecision,
  recordSignalOutcome,
  SignalHistoryEntry,
  SignalHistoryResponse,
  SignalOutcome,
  TickerContext,
  TradeSignal as TradeSignalData,
} from "@/lib/api";
import { buildTechnicalSnapshot } from "@/lib/technicalSnapshot";
import { decodeHtmlEntities } from "@/lib/text";

interface TradeSignalProps {
  data: TickerContext;
}

const ACTION_LABEL: Record<TradeSignalData["action"], string> = {
  buy_call: "BUY CALL",
  buy_put: "BUY PUT",
  stay_out: "STAY OUT",
};

const ACTION_STYLE: Record<TradeSignalData["action"], string> = {
  buy_call: "bg-emerald-600 text-white",
  buy_put: "bg-rose-600 text-white",
  stay_out: "bg-zinc-500 text-white",
};

const OUTCOME_LABEL: Record<SignalOutcome, string> = {
  correct: "Correct",
  incorrect: "Incorrect",
  mixed: "Mixed",
};

function parseSqliteUtc(ts: string): Date {
  return new Date(`${ts.replace(" ", "T")}Z`);
}

function isPastEvaluationWindow(entry: SignalHistoryEntry): boolean {
  const deadline = parseSqliteUtc(entry.generated_at).getTime() + entry.evaluation_days * 24 * 60 * 60 * 1000;
  return Date.now() >= deadline;
}

function fmtDate(ts: string): string {
  return parseSqliteUtc(ts).toLocaleDateString();
}

export default function TradeSignal({ data }: TradeSignalProps) {
  const [signal, setSignal] = useState<TradeSignalData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [decisionBusy, setDecisionBusy] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [askLoading, setAskLoading] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);

  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<SignalHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyRowBusyId, setHistoryRowBusyId] = useState<number | null>(null);

  async function loadHistory() {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const result = await fetchSignalHistory(data.symbol);
      setHistory(result);
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "Failed to load signal history");
    } finally {
      setHistoryLoading(false);
    }
  }

  function toggleHistory() {
    const next = !showHistory;
    setShowHistory(next);
    if (next && !history) loadHistory();
  }

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    setSignal(null);
    setAnswer(null);
    setQuestion("");
    setAskError(null);
    try {
      const snapshot = buildTechnicalSnapshot(data.chart_data);
      const result = await fetchTradeSignal(
        data.symbol,
        { price: data.price, fundamentals: data.fundamentals, news: data.news, filings: data.filings },
        snapshot
      );
      setSignal(result);
      if (showHistory) loadHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate trade signal");
    } finally {
      setLoading(false);
    }
  }

  async function handleDecision(decision: "accepted" | "rejected") {
    if (!signal) return;
    setDecisionBusy(true);
    try {
      const updated = await recordSignalDecision(data.symbol, signal.id, decision);
      setSignal((prev) => (prev ? { ...prev, user_decision: updated.user_decision } : prev));
      if (showHistory) loadHistory();
    } catch {
      // leave the buttons in place; user can retry
    } finally {
      setDecisionBusy(false);
    }
  }

  async function handleAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!signal) return;
    const trimmed = question.trim();
    if (!trimmed) return;

    setAskLoading(true);
    setAskError(null);
    setAnswer(null);
    try {
      const snapshot = buildTechnicalSnapshot(data.chart_data);
      const result = await askAboutSignal(
        data.symbol,
        signal.id,
        { price: data.price, fundamentals: data.fundamentals, news: data.news, filings: data.filings },
        snapshot,
        trimmed
      );
      setAnswer(result);
    } catch (err) {
      setAskError(err instanceof Error ? err.message : "Failed to get an answer");
    } finally {
      setAskLoading(false);
    }
  }

  async function handleHistoryOutcome(entry: SignalHistoryEntry, outcome: SignalOutcome) {
    setHistoryRowBusyId(entry.id);
    try {
      await recordSignalOutcome(data.symbol, entry.id, outcome);
      await loadHistory();
    } catch {
      // leave the row in place; user can retry
    } finally {
      setHistoryRowBusyId(null);
    }
  }

  return (
    <div className="rounded-lg border border-violet-200 bg-violet-50 p-6 dark:border-violet-900/60 dark:bg-violet-950/20 dark:shadow-[0_0_24px_-8px_rgba(167,139,250,0.25)]">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="flex items-center gap-1.5 text-sm font-medium text-violet-700 dark:text-violet-400">
          <span aria-hidden>✦</span> Trade Signal
        </h3>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="rounded-md bg-gradient-to-r from-violet-600 to-violet-500 px-3 py-1.5 text-xs font-medium text-white shadow-sm hover:from-violet-500 hover:to-violet-400 disabled:opacity-50"
        >
          {loading ? "Analyzing…" : signal ? "Regenerate" : "Generate signal"}
        </button>
      </div>

      {error && <p className="text-sm text-rose-600 dark:text-rose-400">{error}</p>}

      {!signal && !error && !loading && (
        <p className="text-sm text-zinc-500 dark:text-zinc-500">
          Synthesizes price action, technical indicators, fundamentals, news sentiment, and
          filings into a direct call/put recommendation.
        </p>
      )}

      {signal && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-md px-3 py-1 text-sm font-bold tracking-wide ${ACTION_STYLE[signal.action]}`}>
              {ACTION_LABEL[signal.action]}
            </span>
            <span className="text-xs uppercase text-zinc-500 dark:text-zinc-400">
              {signal.direction} · {signal.confidence} confidence
            </span>
          </div>

          {signal.user_decision ? (
            <p className="text-xs text-zinc-500 dark:text-zinc-500">
              You marked this call as <span className="font-medium">{signal.user_decision}</span>.
            </p>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={() => handleDecision("accepted")}
                disabled={decisionBusy}
                className="rounded-md border border-emerald-300 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50 disabled:opacity-50 dark:border-emerald-800 dark:text-emerald-400 dark:hover:bg-emerald-950/40"
              >
                Accept
              </button>
              <button
                onClick={() => handleDecision("rejected")}
                disabled={decisionBusy}
                className="rounded-md border border-zinc-300 px-3 py-1 text-xs font-medium text-zinc-600 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-900"
              >
                Reject
              </button>
            </div>
          )}

          <p className="text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
            {decodeHtmlEntities(signal.summary)}
          </p>

          <div>
            <h4 className="mb-1 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">Reasoning</h4>
            <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
              {signal.reasoning.map((r, i) => (
                <li key={i}>{decodeHtmlEntities(r)}</li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="mb-1 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">Key Risks</h4>
            <ul className="list-disc space-y-1 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
              {signal.key_risks.map((r, i) => (
                <li key={i}>{decodeHtmlEntities(r)}</li>
              ))}
            </ul>
          </div>

          <div className="border-t border-violet-200/60 pt-3 dark:border-violet-900/40">
            <h4 className="mb-2 text-xs font-semibold uppercase text-zinc-500 dark:text-zinc-400">
              Ask about this call
            </h4>
            <form onSubmit={handleAsk} className="flex gap-2">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={`e.g. What would change this ${ACTION_LABEL[signal.action]} call?`}
                maxLength={500}
                className="flex-1 rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-violet-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100 dark:placeholder:text-zinc-600"
              />
              <button
                type="submit"
                disabled={askLoading || !question.trim()}
                className="rounded-md bg-gradient-to-r from-violet-600 to-violet-500 px-4 py-2 text-sm font-medium text-white shadow-sm hover:from-violet-500 hover:to-violet-400 disabled:opacity-50"
              >
                {askLoading ? "Thinking…" : "Ask"}
              </button>
            </form>
            {askError && <p className="mt-2 text-sm text-rose-600 dark:text-rose-400">{askError}</p>}
            {answer && (
              <p className="mt-2 text-sm leading-relaxed text-zinc-800 dark:text-zinc-200">
                {decodeHtmlEntities(answer)}
              </p>
            )}
          </div>

          <p className="text-[11px] text-zinc-400 dark:text-zinc-600">{signal.note}</p>
        </div>
      )}

      <div className="mt-5 border-t border-violet-200/60 pt-3 dark:border-violet-900/40">
        <button
          onClick={toggleHistory}
          className="text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-500 dark:hover:text-zinc-300"
        >
          {showHistory ? "Hide" : "Show"} signal history
          {history ? ` (${history.signals.length})` : ""}
        </button>

        {showHistory && (
          <div className="mt-2">
            {historyLoading && <p className="text-sm text-zinc-500 dark:text-zinc-500">Loading history…</p>}
            {historyError && <p className="text-sm text-rose-600 dark:text-rose-400">{historyError}</p>}

            {history && !historyLoading && (
              <>
                {history.track_record.resolved_count > 0 && (
                  <p className="mb-3 text-xs text-zinc-500 dark:text-zinc-400">
                    {history.track_record.correct_count}/{history.track_record.resolved_count} resolved calls
                    correct
                  </p>
                )}

                {history.signals.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-500">
                    No past signals for {data.symbol} yet.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-200 text-left text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-500">
                          <th className="pb-2 pr-3 font-medium">Date</th>
                          <th className="pb-2 pr-3 font-medium">Action</th>
                          <th className="pb-2 pr-3 font-medium">Decision</th>
                          <th className="pb-2 font-medium">Outcome</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.signals.map((entry) => {
                          const outcomeLabel = entry.auto_outcome
                            ? `${OUTCOME_LABEL[entry.auto_outcome]} (auto)`
                            : entry.user_outcome
                              ? `${OUTCOME_LABEL[entry.user_outcome]} (self-reported)`
                              : null;
                          const canSelfReport =
                            !entry.auto_outcome &&
                            !entry.user_outcome &&
                            entry.action !== "stay_out" &&
                            isPastEvaluationWindow(entry);

                          return (
                            <tr key={entry.id} className="border-b border-zinc-100 last:border-0 dark:border-zinc-900">
                              <td className="py-2 pr-3 text-zinc-500 dark:text-zinc-500">{fmtDate(entry.generated_at)}</td>
                              <td className="py-2 pr-3 font-medium text-zinc-900 dark:text-zinc-100">
                                {ACTION_LABEL[entry.action]}
                              </td>
                              <td className="py-2 pr-3 text-zinc-700 dark:text-zinc-300">
                                {entry.user_decision ?? "—"}
                              </td>
                              <td className="py-2 text-zinc-700 dark:text-zinc-300">
                                {outcomeLabel ??
                                  (canSelfReport ? (
                                    <div className="flex gap-1.5">
                                      {(["correct", "incorrect", "mixed"] as const).map((o) => (
                                        <button
                                          key={o}
                                          onClick={() => handleHistoryOutcome(entry, o)}
                                          disabled={historyRowBusyId === entry.id}
                                          className="rounded border border-zinc-300 px-1.5 py-0.5 text-[11px] text-zinc-600 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-900"
                                        >
                                          {OUTCOME_LABEL[o]}
                                        </button>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="text-zinc-400 dark:text-zinc-600">—</span>
                                  ))}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
