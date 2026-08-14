import json
from datetime import datetime, timedelta, timezone

from db.database import TRADE_SIGNAL_RETURN_COLUMNS, get_connection

FUNDAMENTALS_TTL_HOURS = 20
FILINGS_TTL_HOURS = 12
NEWS_TTL_HOURS = 1
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


def create_trade_signal(
    symbol: str,
    direction: str,
    action: str,
    confidence: str,
    summary: str,
    reasoning: list[str],
    key_risks: list[str],
    price_at_signal: float,
    evaluation_days: int = 5,
) -> int:
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO trade_signal
                (symbol, direction, action, confidence, summary, reasoning_json, key_risks_json,
                 price_at_signal, evaluation_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symbol, direction, action, confidence, summary,
                json.dumps(reasoning), json.dumps(key_risks), price_at_signal, evaluation_days,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _trade_signal_view(row: dict) -> dict:
    view = dict(row)
    view["reasoning"] = json.loads(view.pop("reasoning_json"))
    view["key_risks"] = json.loads(view.pop("key_risks_json"))
    return view


def get_trade_signal(signal_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM trade_signal WHERE id = ?", (signal_id,)).fetchone()
    finally:
        conn.close()
    return _trade_signal_view(dict(row)) if row else None


def get_trade_signals_for_symbol(symbol: str, limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM trade_signal WHERE symbol = ? ORDER BY generated_at DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_trade_signal_view(dict(row)) for row in rows]


def set_signal_decision(signal_id: int, decision: str) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE trade_signal SET user_decision = ? WHERE id = ?", (decision, signal_id)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def set_signal_user_outcome(signal_id: int, outcome: str, notes: str | None = None) -> bool:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE trade_signal SET user_outcome = ?, user_notes = ? WHERE id = ?",
            (outcome, notes, signal_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_unresolved_signals_past_window() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM trade_signal
            WHERE auto_outcome IS NULL
              AND action != 'stay_out'
              AND datetime(generated_at, '+' || evaluation_days || ' days') <= datetime('now')
            """
        ).fetchall()
    finally:
        conn.close()
    return [_trade_signal_view(dict(row)) for row in rows]


def resolve_signal_outcome(signal_id: int, auto_outcome: str, resolution_price: float) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE trade_signal
            SET auto_outcome = ?, resolution_price = ?, auto_resolved_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (auto_outcome, resolution_price, signal_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_symbol_track_record(symbol: str) -> dict:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT COALESCE(auto_outcome, user_outcome) AS outcome
            FROM trade_signal
            WHERE symbol = ? AND (auto_outcome IS NOT NULL OR user_outcome IS NOT NULL)
            """,
            (symbol,),
        ).fetchall()
    finally:
        conn.close()
    outcomes = [row["outcome"] for row in rows]
    return {
        "resolved_count": len(outcomes),
        "correct_count": sum(1 for o in outcomes if o == "correct"),
        "incorrect_count": sum(1 for o in outcomes if o == "incorrect"),
    }


def get_directional_signals() -> list[dict]:
    """All buy_call/buy_put signals — resolved or not — for performance/calibration aggregation.
    stay_out is excluded: there's no directional claim to score against price movement."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM trade_signal WHERE action != 'stay_out' ORDER BY generated_at"
        ).fetchall()
    finally:
        conn.close()
    return [_trade_signal_view(dict(row)) for row in rows]


def get_signals_needing_return_backfill() -> list[dict]:
    """Directional signals with at least one un-populated forward-return horizon.
    Horizons become computable incrementally as calendar days pass, so this is re-checked
    on every poller run rather than resolved once."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT * FROM trade_signal
            WHERE action != 'stay_out'
              AND (return_1d IS NULL OR return_3d IS NULL OR return_5d IS NULL
                   OR return_10d IS NULL OR return_20d IS NULL)
            """
        ).fetchall()
    finally:
        conn.close()
    return [_trade_signal_view(dict(row)) for row in rows]


def update_signal_returns(signal_id: int, **fields) -> None:
    """Partial update of forward-return columns. Only whitelisted columns are ever written —
    this never touches direction/confidence/price_at_signal, the fields a look-ahead-bias bug
    would otherwise be tempted to "correct" after the fact."""
    columns = [c for c in fields if c in TRADE_SIGNAL_RETURN_COLUMNS]
    if not columns:
        return
    set_clause = ", ".join(f"{c} = ?" for c in columns)
    values = [fields[c] for c in columns]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE trade_signal SET {set_clause} WHERE id = ?", (*values, signal_id))
        conn.commit()
    finally:
        conn.close()


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
