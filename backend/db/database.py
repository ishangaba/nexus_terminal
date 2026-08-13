import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "nexus.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ticker (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
    country TEXT,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS price_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    last_price REAL,
    change REAL,
    change_pct REAL,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    headline TEXT,
    source TEXT,
    url TEXT,
    published_at TEXT,
    sentiment_score REAL,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fundamentals_cache (
    symbol TEXT PRIMARY KEY,
    pe_ratio REAL,
    market_cap REAL,
    eps REAL,
    week_52_high REAL,
    week_52_low REAL,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chart_cache (
    symbol TEXT PRIMARY KEY,
    chart_json TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS watchlist (
    symbol TEXT PRIMARY KEY,
    added_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS filings_cache (
    symbol TEXT PRIMARY KEY,
    filings_json TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS graph_build_cache (
    symbol TEXT PRIMARY KEY,
    built_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS news_cache (
    symbol TEXT PRIMARY KEY,
    news_json TEXT,
    fetched_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS position (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL DEFAULT 'long' CHECK (side IN ('long', 'short')),
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    entry_date TEXT NOT NULL,
    exit_price REAL,
    exit_date TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trade_signal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    direction TEXT NOT NULL,
    action TEXT NOT NULL,
    confidence TEXT NOT NULL,
    summary TEXT NOT NULL,
    reasoning_json TEXT NOT NULL,
    key_risks_json TEXT NOT NULL,
    price_at_signal REAL NOT NULL,
    user_decision TEXT,
    user_outcome TEXT,
    user_notes TEXT,
    auto_outcome TEXT,
    auto_resolved_at TEXT,
    resolution_price REAL,
    evaluation_days INTEGER NOT NULL DEFAULT 5
);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Lightweight additive migrations for columns added after tables already existed."""
    existing_columns = {row["name"] for row in conn.execute("PRAGMA table_info(ticker)")}
    if "country" not in existing_columns:
        conn.execute("ALTER TABLE ticker ADD COLUMN country TEXT")


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()
