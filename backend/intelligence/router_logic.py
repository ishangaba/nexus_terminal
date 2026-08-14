"""Deterministic keyword routing from a free-text question to a tool-category subset.

Deliberately simple — a keyword table, not a classifier or an LLM call. Per
docs/architecture/roadmap.md, this is the single biggest scope-creep risk in the whole roadmap:
resist making this "smarter" before there's real evidence the deterministic version is
insufficient. A question that matches nothing falls back to running every tool, so a routing
miss degrades to "answer broadly" rather than "answer nothing."
"""

TOOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "technical": (
        "technical", "chart", "trend", "momentum", "rsi", "macd", "moving average",
        "support", "resistance", "overbought", "oversold", "breakout",
        "fall", "fell", "drop", "dropped", "rise", "rose", "surge", "plunge", "rally", "crash",
    ),
    "fundamentals": (
        "valuation", "overvalued", "undervalued", "p/e", "pe ratio", "market cap",
        "eps", "fundamentals", "expensive", "cheap", "52-week", "52 week",
    ),
    "news": (
        "news", "headline", "sentiment", "buzz", "media", "why did", "what happened",
    ),
    "sec_filings": (
        "filing", "8-k", "8k", "10-k", "10k", "10-q", "10q", "sec filing", "disclosure",
        "annual report", "quarterly report",
    ),
    "earnings": (
        "earnings", "beat", "miss", "surprise", "insider", "analyst", "recommendation",
        "rating", "price target", "buy rating", "guidance",
    ),
    "macro": (
        "inflation", "cpi", "fed ", "federal reserve", "interest rate", "unemployment",
        "macro", "economy", "recession", "gdp",
    ),
}

ALL_TOOLS: frozenset[str] = frozenset(TOOL_KEYWORDS.keys())


def route(question: str) -> frozenset[str]:
    """Which tool categories does this question call for? Falls back to ALL_TOOLS when nothing
    matches, matching the always-run-everything behavior of POST /api/research/{ticker} — a
    broad question is never under-researched."""
    q = question.lower()
    matched = frozenset(category for category, keywords in TOOL_KEYWORDS.items() if any(kw in q for kw in keywords))
    return matched or ALL_TOOLS
