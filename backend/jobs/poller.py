import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from db.database import get_connection
from db.models import insert_price_snapshot
from services import finnhub

logger = logging.getLogger("poller")

POLL_INTERVAL_MINUTES = 5


def _tracked_symbols() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT symbol FROM ticker").fetchall()
    finally:
        conn.close()
    return [row["symbol"] for row in rows]


async def _refresh_symbol(symbol: str) -> None:
    quote = await finnhub.get_quote(symbol)
    if quote and quote.get("c"):
        insert_price_snapshot(symbol, quote["c"], quote.get("d", 0), quote.get("dp", 0))


def refresh_watchlist() -> None:
    symbols = _tracked_symbols()
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


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_watchlist, "interval", minutes=POLL_INTERVAL_MINUTES, id="watchlist_poller")
    scheduler.start()
    return scheduler
