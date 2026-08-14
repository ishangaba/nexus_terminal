import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from db.models import (
    get_signals_needing_return_backfill,
    get_ticker,
    get_unresolved_signals_past_window,
    get_watchlist,
    insert_price_snapshot,
    resolve_signal_outcome,
    update_signal_returns,
)
from intelligence.evaluators import signal_evaluator
from services import aggregator, finnhub

logger = logging.getLogger("poller")

POLL_INTERVAL_MINUTES = 5


async def _refresh_symbol(symbol: str) -> None:
    quote = await finnhub.get_quote(symbol)
    if quote and quote.get("c"):
        insert_price_snapshot(symbol, quote["c"], quote.get("d", 0), quote.get("dp", 0))


def refresh_watchlist() -> None:
    symbols = get_watchlist()
    if not symbols:
        return
    logger.info("Refreshing price snapshots for %d tracked symbol(s)", len(symbols))

    async def run_all():
        for symbol in symbols:
            try:
                await _refresh_symbol(symbol)
            except Exception:
                logger.exception("Failed to refresh %s", symbol)

    asyncio.run(run_all())


async def _resolve_signal(signal: dict) -> None:
    quote = await finnhub.get_quote(signal["symbol"])
    if not quote or not quote.get("c"):
        return
    resolution_price = quote["c"]
    price_at_signal = signal["price_at_signal"]
    price_rose = resolution_price > price_at_signal
    # bullish (buy_call) correct if price rose; bearish (buy_put) correct if price fell.
    # stay_out signals are excluded upstream by get_unresolved_signals_past_window.
    called_correctly = price_rose if signal["action"] == "buy_call" else not price_rose
    resolve_signal_outcome(
        signal["id"], "correct" if called_correctly else "incorrect", resolution_price
    )


def resolve_pending_signals() -> None:
    pending = get_unresolved_signals_past_window()
    if not pending:
        return
    logger.info("Resolving %d trade signal(s) past their evaluation window", len(pending))

    async def run_all():
        for signal in pending:
            try:
                await _resolve_signal(signal)
            except Exception:
                logger.exception("Failed to resolve signal %s (%s)", signal["id"], signal["symbol"])

    asyncio.run(run_all())


async def _backfill_symbol_returns(
    symbol: str, signals: list[dict], benchmark_chart: list[dict] | None
) -> None:
    ticker_chart, chart_err = await aggregator.get_chart_data(symbol)
    if chart_err or not ticker_chart:
        logger.warning("Skipping return backfill for %s: %s", symbol, chart_err or "no chart data")
        return

    ticker_row = get_ticker(symbol)
    sector_etf = signal_evaluator.map_sector_etf(ticker_row.get("sector") if ticker_row else None)
    sector_chart = None
    if sector_etf:
        sector_chart, sector_err = await aggregator.get_chart_data(sector_etf)
        if sector_err:
            sector_chart = None

    for signal in signals:
        updates = signal_evaluator.compute_returns(signal, ticker_chart, benchmark_chart, sector_chart)
        if updates:
            update_signal_returns(signal["id"], **updates)


def backfill_signal_returns() -> None:
    """Fills in forward-return columns for directional signals as price history becomes
    available. Runs daily and re-checks every incomplete signal — a 20-day horizon can't be
    computed until 20 real days have passed, so this converges gradually rather than resolving
    everything in one pass."""
    pending = get_signals_needing_return_backfill()
    if not pending:
        return
    logger.info("Backfilling forward returns for %d trade signal(s)", len(pending))

    by_symbol: dict[str, list[dict]] = {}
    for signal in pending:
        by_symbol.setdefault(signal["symbol"], []).append(signal)

    async def run_all():
        benchmark_chart, benchmark_err = await aggregator.get_chart_data(signal_evaluator.BENCHMARK_SYMBOL)
        if benchmark_err:
            logger.warning(
                "Benchmark (%s) chart unavailable: %s", signal_evaluator.BENCHMARK_SYMBOL, benchmark_err
            )
            benchmark_chart = None
        for symbol, signals in by_symbol.items():
            try:
                await _backfill_symbol_returns(symbol, signals, benchmark_chart)
            except Exception:
                logger.exception("Failed to backfill returns for %s", symbol)

    asyncio.run(run_all())


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_watchlist, "interval", minutes=POLL_INTERVAL_MINUTES, id="watchlist_poller")
    scheduler.add_job(resolve_pending_signals, "interval", hours=24, id="signal_resolver")
    scheduler.add_job(backfill_signal_returns, "interval", hours=24, id="signal_return_backfill")
    scheduler.start()
    return scheduler
