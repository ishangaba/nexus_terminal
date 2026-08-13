import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from db.models import (
    get_unresolved_signals_past_window,
    get_watchlist,
    insert_price_snapshot,
    resolve_signal_outcome,
)
from services import finnhub

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


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_watchlist, "interval", minutes=POLL_INTERVAL_MINUTES, id="watchlist_poller")
    scheduler.add_job(resolve_pending_signals, "interval", hours=24, id="signal_resolver")
    scheduler.start()
    return scheduler
