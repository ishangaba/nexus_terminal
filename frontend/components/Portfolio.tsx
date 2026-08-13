"use client";

import { Fragment, useEffect, useState } from "react";
import ErrorNotice from "@/components/ErrorNotice";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import {
  closePosition,
  createPosition,
  deletePosition,
  fetchPortfolio,
  ClosedPosition,
  OpenPosition,
  PortfolioData,
} from "@/lib/api";

const AUTO_REFRESH_MS = 30_000;

function fmtMoney(n: number | null): string {
  if (n === null) return "—";
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function fmtPct(n: number | null): string {
  if (n === null) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function pnlClass(n: number | null): string {
  if (n === null) return "text-zinc-400 dark:text-zinc-600";
  return n >= 0 ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400";
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function Portfolio() {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const [showAddForm, setShowAddForm] = useState(false);
  const [showClosed, setShowClosed] = useState(false);

  const [symbol, setSymbol] = useState("");
  const [quantity, setQuantity] = useState("");
  const [entryPrice, setEntryPrice] = useState("");
  const [entryDate, setEntryDate] = useState(todayISO());
  const [notes, setNotes] = useState("");
  const [adding, setAdding] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [closingId, setClosingId] = useState<number | null>(null);
  const [exitPrice, setExitPrice] = useState("");
  const [exitDate, setExitDate] = useState(todayISO());
  const [closeError, setCloseError] = useState<string | null>(null);
  const [rowBusyId, setRowBusyId] = useState<number | null>(null);

  async function load() {
    try {
      const result = await fetchPortfolio();
      setData(result);
      setLoadError(null);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load portfolio");
    }
  }

  useEffect(() => {
    load();
  }, []);

  useAutoRefresh(load, AUTO_REFRESH_MS);

  async function handleRefresh() {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    setAddError(null);
    try {
      await createPosition({
        symbol: symbol.trim().toUpperCase(),
        quantity: parseFloat(quantity),
        entry_price: parseFloat(entryPrice),
        entry_date: entryDate,
        notes: notes.trim() || undefined,
      });
      setSymbol("");
      setQuantity("");
      setEntryPrice("");
      setEntryDate(todayISO());
      setNotes("");
      setShowAddForm(false);
      await load();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to add position");
    } finally {
      setAdding(false);
    }
  }

  function startClose(position: OpenPosition) {
    setClosingId(position.id);
    setExitPrice(position.last_price !== null ? String(position.last_price) : "");
    setExitDate(todayISO());
    setCloseError(null);
  }

  async function handleClose(e: React.FormEvent, id: number) {
    e.preventDefault();
    setRowBusyId(id);
    setCloseError(null);
    try {
      await closePosition(id, { exit_price: parseFloat(exitPrice), exit_date: exitDate });
      setClosingId(null);
      await load();
    } catch (err) {
      setCloseError(err instanceof Error ? err.message : "Failed to close position");
    } finally {
      setRowBusyId(null);
    }
  }

  async function handleDelete(id: number) {
    setRowBusyId(id);
    try {
      await deletePosition(id);
      await load();
    } catch {
      // leave the position in place; user can retry
    } finally {
      setRowBusyId(null);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900/60 dark:backdrop-blur">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">Portfolio</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="text-xs text-zinc-400 hover:text-zinc-600 disabled:opacity-50 dark:text-zinc-600 dark:hover:text-zinc-300"
          >
            {refreshing ? "Refreshing…" : "↻ Refresh"}
          </button>
          <button
            onClick={() => setShowAddForm((v) => !v)}
            className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-900"
          >
            {showAddForm ? "Cancel" : "+ Add position"}
          </button>
        </div>
      </div>

      {loadError && <ErrorNotice message={loadError} />}

      {showAddForm && (
        <form
          onSubmit={handleAdd}
          className="mb-5 flex flex-wrap items-end gap-2 rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950/40"
        >
          <div>
            <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">Symbol</label>
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="AAPL"
              required
              className="w-24 rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm uppercase text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">Quantity</label>
            <input
              type="number"
              step="any"
              min="0"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
              className="w-24 rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">Entry price</label>
            <input
              type="number"
              step="any"
              min="0"
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              required
              className="w-28 rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">Entry date</label>
            <input
              type="date"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              required
              className="rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </div>
          <div className="flex-1 basis-32">
            <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">Notes (optional)</label>
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
            />
          </div>
          <button
            type="submit"
            disabled={adding}
            className="rounded-md bg-gradient-to-r from-cyan-600 to-cyan-500 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50"
          >
            {adding ? "Adding…" : "Add"}
          </button>
          {addError && (
            <div className="w-full">
              <ErrorNotice message={addError} />
            </div>
          )}
        </form>
      )}

      {!data && !loadError && <p className="text-sm text-zinc-500 dark:text-zinc-500">Loading portfolio…</p>}

      {data && (
        <>
          <div className="mb-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div>
              <div className="text-zinc-500 dark:text-zinc-500">Market Value</div>
              <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
                {fmtMoney(data.summary.total_market_value)}
              </div>
            </div>
            <div>
              <div className="text-zinc-500 dark:text-zinc-500">Unrealized P&L</div>
              <div className={`font-mono font-medium ${pnlClass(data.summary.total_unrealized_pnl)}`}>
                {fmtMoney(data.summary.total_unrealized_pnl)} ({fmtPct(data.summary.total_unrealized_pnl_pct)})
              </div>
            </div>
            <div>
              <div className="text-zinc-500 dark:text-zinc-500">Realized P&L</div>
              <div className={`font-mono font-medium ${pnlClass(data.summary.total_realized_pnl)}`}>
                {fmtMoney(data.summary.total_realized_pnl)}
              </div>
            </div>
            <div>
              <div className="text-zinc-500 dark:text-zinc-500">Positions</div>
              <div className="font-mono font-medium text-zinc-900 dark:text-zinc-100">
                {data.summary.open_position_count} open
              </div>
            </div>
          </div>

          {data.allocation.by_sector.length > 0 && (
            <div className="mb-5">
              <div className="mb-1.5 text-xs font-medium text-zinc-500 dark:text-zinc-500">Sector allocation</div>
              <div className="flex flex-col gap-1.5">
                {data.allocation.by_sector.map((entry) => (
                  <div key={entry.name} className="flex items-center gap-2 text-xs">
                    <span className="w-28 shrink-0 truncate text-zinc-600 dark:text-zinc-400">{entry.name}</span>
                    <div className="h-1.5 flex-1 rounded-full bg-zinc-100 dark:bg-zinc-800">
                      <div
                        className="h-1.5 rounded-full bg-cyan-500"
                        style={{ width: `${Math.min(100, entry.pct_of_portfolio)}%` }}
                      />
                    </div>
                    <span className="w-12 shrink-0 text-right font-mono text-zinc-500 dark:text-zinc-500">
                      {entry.pct_of_portfolio.toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {data.open_positions.length === 0 ? (
            <div className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-500">
              No open positions yet. Add one above to start tracking P&L.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-zinc-200 text-left text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-500">
                    <th className="pb-2 pr-3 font-medium">Symbol</th>
                    <th className="pb-2 pr-3 font-medium">Qty</th>
                    <th className="pb-2 pr-3 font-medium">Entry</th>
                    <th className="pb-2 pr-3 font-medium">Last</th>
                    <th className="pb-2 pr-3 font-medium">Value</th>
                    <th className="pb-2 pr-3 font-medium">Unrealized P&L</th>
                    <th className="pb-2 pr-3 font-medium">Sector</th>
                    <th className="pb-2 font-medium"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.open_positions.map((p) => (
                    <Fragment key={p.id}>
                      <tr className="border-b border-zinc-100 last:border-0 dark:border-zinc-900">
                        <td className="py-2 pr-3 font-medium text-zinc-900 dark:text-zinc-100">{p.symbol}</td>
                        <td className="py-2 pr-3 font-mono text-zinc-700 dark:text-zinc-300">{p.quantity}</td>
                        <td className="py-2 pr-3 font-mono text-zinc-700 dark:text-zinc-300">
                          {fmtMoney(p.entry_price)}
                        </td>
                        <td className="py-2 pr-3 font-mono text-zinc-700 dark:text-zinc-300">
                          {fmtMoney(p.last_price)}
                        </td>
                        <td className="py-2 pr-3 font-mono text-zinc-700 dark:text-zinc-300">
                          {fmtMoney(p.market_value)}
                        </td>
                        <td className={`py-2 pr-3 font-mono ${pnlClass(p.unrealized_pnl)}`}>
                          {fmtMoney(p.unrealized_pnl)} ({fmtPct(p.unrealized_pnl_pct)})
                        </td>
                        <td className="py-2 pr-3 text-zinc-500 dark:text-zinc-500">{p.sector}</td>
                        <td className="py-2 text-right">
                          <button
                            onClick={() => startClose(p)}
                            className="mr-3 text-xs text-cyan-600 hover:underline dark:text-cyan-400"
                          >
                            Close
                          </button>
                          <button
                            onClick={() => handleDelete(p.id)}
                            disabled={rowBusyId === p.id}
                            className="text-xs text-zinc-400 hover:text-rose-500 disabled:opacity-50 dark:text-zinc-600 dark:hover:text-rose-400"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                      {p.quote_error && (
                        <tr key={`${p.id}-error`}>
                          <td colSpan={8} className="pb-2">
                            <ErrorNotice message={`${p.symbol}: ${p.quote_error}`} />
                          </td>
                        </tr>
                      )}
                      {closingId === p.id && (
                        <tr key={`${p.id}-close`}>
                          <td colSpan={8} className="pb-3">
                            <form
                              onSubmit={(e) => handleClose(e, p.id)}
                              className="flex flex-wrap items-end gap-2 rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-950/40"
                            >
                              <div>
                                <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                                  Exit price
                                </label>
                                <input
                                  type="number"
                                  step="any"
                                  min="0"
                                  value={exitPrice}
                                  onChange={(e) => setExitPrice(e.target.value)}
                                  required
                                  className="w-28 rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
                                />
                              </div>
                              <div>
                                <label className="mb-1 block text-xs text-zinc-500 dark:text-zinc-400">
                                  Exit date
                                </label>
                                <input
                                  type="date"
                                  value={exitDate}
                                  onChange={(e) => setExitDate(e.target.value)}
                                  required
                                  className="rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-cyan-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
                                />
                              </div>
                              <button
                                type="submit"
                                disabled={rowBusyId === p.id}
                                className="rounded-md bg-gradient-to-r from-cyan-600 to-cyan-500 px-4 py-1.5 text-sm font-medium text-white shadow-sm hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50"
                              >
                                {rowBusyId === p.id ? "Closing…" : "Confirm close"}
                              </button>
                              <button
                                type="button"
                                onClick={() => setClosingId(null)}
                                className="rounded-md border border-zinc-300 px-3 py-1.5 text-sm text-zinc-600 hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-zinc-900"
                              >
                                Cancel
                              </button>
                              {closeError && (
                                <div className="w-full">
                                  <ErrorNotice message={closeError} />
                                </div>
                              )}
                            </form>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="mt-4">
            <button
              onClick={() => setShowClosed((v) => !v)}
              className="text-xs text-zinc-500 hover:text-zinc-700 dark:text-zinc-500 dark:hover:text-zinc-300"
            >
              {showClosed ? "Hide" : "Show"} closed positions ({data.summary.closed_position_count})
            </button>
            {showClosed && (
              <div className="mt-2">
                {data.closed_positions.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm text-zinc-500 dark:border-zinc-700 dark:text-zinc-500">
                    No closed positions yet.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-zinc-200 text-left text-xs text-zinc-500 dark:border-zinc-800 dark:text-zinc-500">
                          <th className="pb-2 pr-3 font-medium">Symbol</th>
                          <th className="pb-2 pr-3 font-medium">Qty</th>
                          <th className="pb-2 pr-3 font-medium">Entry</th>
                          <th className="pb-2 pr-3 font-medium">Exit</th>
                          <th className="pb-2 pr-3 font-medium">Realized P&L</th>
                          <th className="pb-2 font-medium">Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.closed_positions.map((p: ClosedPosition) => (
                          <tr key={p.id} className="border-b border-zinc-100 last:border-0 dark:border-zinc-900">
                            <td className="py-2 pr-3 font-medium text-zinc-900 dark:text-zinc-100">{p.symbol}</td>
                            <td className="py-2 pr-3 font-mono text-zinc-700 dark:text-zinc-300">{p.quantity}</td>
                            <td className="py-2 pr-3 font-mono text-zinc-700 dark:text-zinc-300">
                              {fmtMoney(p.entry_price)}
                            </td>
                            <td className="py-2 pr-3 font-mono text-zinc-700 dark:text-zinc-300">
                              {fmtMoney(p.exit_price)}
                            </td>
                            <td className={`py-2 pr-3 font-mono ${pnlClass(p.realized_pnl)}`}>
                              {fmtMoney(p.realized_pnl)} ({fmtPct(p.realized_pnl_pct)})
                            </td>
                            <td className="py-2 text-zinc-500 dark:text-zinc-500">{p.notes ?? "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
