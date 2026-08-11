import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "nexus.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ticker (
    symbol TEXT PRIMARY KEY,
    name TEXT,
    sector TEXT,
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
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
