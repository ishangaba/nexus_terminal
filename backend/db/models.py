import json
from datetime import datetime, timedelta, timezone

from db.database import get_connection

FUNDAMENTALS_TTL_HOURS = 20
FILINGS_TTL_HOURS = 12
NEWS_TTL_HOURS = 2
GRAPH_BUILD_TTL_HOURS = 24 * 7  # subsidiary/contract data barely changes; rebuild weekly


def upsert_ticker(symbol: str, name: str = "", sector: str = "", country: str = "") -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO ticker (symbol, name, sector, country) VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol) DO UPDATE SET name=excluded.name, sector=excluded.sector, country=excluded.country
            """,
            (symbol, name, sector, country),
        )
        conn.commit()
    finally:
        conn.close()


def get_ticker(symbol: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ticker WHERE symbol = ?", (symbol,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def insert_price_snapshot(symbol: str, last_price: float, change: float, change_pct: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO price_snapshot (symbol, last_price, change, change_pct) VALUES (?, ?, ?, ?)",
            (symbol, last_price, change, change_pct),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_fundamentals(symbol: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM fundamentals_cache WHERE symbol = ?", (symbol,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    fetched_at = datetime.fromisoformat(row["fetched_at"]).replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - fetched_at > timedelta(hours=FUNDAMENTALS_TTL_HOURS):
        return None
    return dict(row)


def upsert_fundamentals_cache(
    symbol: str, pe_ratio: float | None, market_cap: float | None, eps: float | None,
    week_52_high: float | None, week_52_low: float | None,
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO fundamentals_cache (symbol, pe_ratio, market_cap, eps, week_52_high, week_52_low, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET
                pe_ratio=excluded.pe_ratio, market_cap=excluded.market_cap, eps=excluded.eps,
                week_52_high=excluded.week_52_high, week_52_low=excluded.week_52_low,
                fetched_at=CURRENT_TIMESTAMP
            """,
            (symbol, pe_ratio, market_cap, eps, week_52_high, week_52_low),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_chart(symbol: str) -> list | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM chart_cache WHERE symbol = ?", (symbol,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    fetched_at = datetime.fromisoformat(row["fetched_at"]).replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - fetched_at > timedelta(hours=FUNDAMENTALS_TTL_HOURS):
        return None
    return json.loads(row["chart_json"])


def upsert_chart_cache(symbol: str, chart_data: list) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO chart_cache (symbol, chart_json, fetched_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET chart_json=excluded.chart_json, fetched_at=CURRENT_TIMESTAMP
            """,
            (symbol, json.dumps(chart_data)),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_filings(symbol: str) -> list | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM filings_cache WHERE symbol = ?", (symbol,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    fetched_at = datetime.fromisoformat(row["fetched_at"]).replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - fetched_at > timedelta(hours=FILINGS_TTL_HOURS):
        return None
    return json.loads(row["filings_json"])


def upsert_filings_cache(symbol: str, filings: list) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO filings_cache (symbol, filings_json, fetched_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET filings_json=excluded.filings_json, fetched_at=CURRENT_TIMESTAMP
            """,
            (symbol, json.dumps(filings)),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached_news(symbol: str) -> list | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM news_cache WHERE symbol = ?", (symbol,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    fetched_at = datetime.fromisoformat(row["fetched_at"]).replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - fetched_at > timedelta(hours=NEWS_TTL_HOURS):
        return None
    return json.loads(row["news_json"])


def upsert_news_cache(symbol: str, news: list) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO news_cache (symbol, news_json, fetched_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET news_json=excluded.news_json, fetched_at=CURRENT_TIMESTAMP
            """,
            (symbol, json.dumps(news)),
        )
        conn.commit()
    finally:
        conn.close()


def is_graph_stale(symbol: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT built_at FROM graph_build_cache WHERE symbol = ?", (symbol,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return True
    built_at = datetime.fromisoformat(row["built_at"]).replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - built_at > timedelta(hours=GRAPH_BUILD_TTL_HOURS)


def mark_graph_built(symbol: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO graph_build_cache (symbol, built_at) VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(symbol) DO UPDATE SET built_at=CURRENT_TIMESTAMP
            """,
            (symbol,),
        )
        conn.commit()
    finally:
        conn.close()


def add_to_watchlist(symbol: str) -> None:
    conn = get_connection()
    try:
        conn.execute("INSERT OR IGNORE INTO watchlist (symbol) VALUES (?)", (symbol,))
        conn.commit()
    finally:
        conn.close()


def remove_from_watchlist(symbol: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_watchlist() -> list[str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT symbol FROM watchlist ORDER BY added_at").fetchall()
    finally:
        conn.close()
    return [row["symbol"] for row in rows]


def create_position(
    symbol: str, side: str, quantity: float, entry_price: float, entry_date: str, notes: str | None = None
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO position (symbol, side, quantity, entry_price, entry_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (symbol, side, quantity, entry_price, entry_date, notes),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_position(position_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM position WHERE id = ?", (position_id,)).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def get_open_positions() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM position WHERE exit_price IS NULL ORDER BY entry_date"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def get_closed_positions() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM position WHERE exit_price IS NOT NULL ORDER BY exit_date DESC"
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def close_position(position_id: int, exit_price: float, exit_date: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE position SET exit_price = ?, exit_date = ? WHERE id = ? AND exit_price IS NULL",
            (exit_price, exit_date, position_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_position(position_id: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM position WHERE id = ?", (position_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_latest_price_snapshot(symbol: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM price_snapshot WHERE symbol = ? ORDER BY fetched_at DESC LIMIT 1", (symbol,)
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
            """,
            (key, value),
        )
        conn.commit()
    finally:
        conn.close()


def delete_setting(key: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        conn.commit()
    finally:
        conn.close()


def get_all_settings() -> dict[str, str]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
    finally:
        conn.close()
    return {row["key"]: row["value"] for row in rows}


def insert_news_item(
    symbol: str, headline: str, source: str, url: str, published_at: str, sentiment_score: float | None
) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO news_item (symbol, headline, source, url, published_at, sentiment_score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (symbol, headline, source, url, published_at, sentiment_score),
        )
        conn.commit()
    finally:
        conn.close()
