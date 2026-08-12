import asyncio
from datetime import datetime, timedelta, timezone

from db.models import (
    get_cached_chart,
    get_cached_filings,
    get_cached_fundamentals,
    upsert_chart_cache,
    upsert_filings_cache,
    upsert_fundamentals_cache,
    upsert_ticker,
)
from services import alpha_vantage, claude_analyst, finnhub, sec_edgar

MAX_NEWS_ITEMS = 8
CHART_DAYS = 30


def _safe_float(value) -> float | None:
    try:
        if value in (None, "", "None", "-"):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


class AlphaVantageRateLimitError(Exception):
    pass


def _check_alpha_vantage_error(response: dict) -> None:
    for key in ("Note", "Information", "Error Message"):
        if key in response:
            raise AlphaVantageRateLimitError(response[key])


async def _get_fundamentals(symbol: str) -> dict:
    cached = get_cached_fundamentals(symbol)
    if cached is not None:
        return {
            "pe_ratio": cached["pe_ratio"],
            "market_cap": cached["market_cap"],
            "eps": cached["eps"],
            "52_week_high": cached["week_52_high"],
            "52_week_low": cached["week_52_low"],
        }

    empty = {"pe_ratio": None, "market_cap": None, "eps": None, "52_week_high": None, "52_week_low": None}

    try:
        overview = await alpha_vantage.get_overview(symbol)
        _check_alpha_vantage_error(overview)
    except AlphaVantageRateLimitError:
        return empty

    pe_ratio = _safe_float(overview.get("PERatio"))
    market_cap = _safe_float(overview.get("MarketCapitalization"))
    eps = _safe_float(overview.get("EPS"))
    week_52_high = _safe_float(overview.get("52WeekHigh"))
    week_52_low = _safe_float(overview.get("52WeekLow"))

    upsert_fundamentals_cache(symbol, pe_ratio, market_cap, eps, week_52_high, week_52_low)
    if overview.get("Name"):
        upsert_ticker(symbol, overview.get("Name", ""), overview.get("Sector", ""), overview.get("Country", ""))

    return {
        "pe_ratio": pe_ratio,
        "market_cap": market_cap,
        "eps": eps,
        "52_week_high": week_52_high,
        "52_week_low": week_52_low,
    }


async def _get_chart_data(symbol: str) -> list[dict]:
    cached = get_cached_chart(symbol)
    if cached is not None:
        return cached

    try:
        series = await alpha_vantage.get_daily_series(symbol)
        _check_alpha_vantage_error(series)
    except AlphaVantageRateLimitError:
        return []

    daily = series.get("Time Series (Daily)", {})
    chart_data = [
        {
            "date": date,
            "open": _safe_float(values.get("1. open")),
            "high": _safe_float(values.get("2. high")),
            "low": _safe_float(values.get("3. low")),
            "close": _safe_float(values.get("4. close")),
        }
        for date, values in sorted(daily.items())[-CHART_DAYS:]
    ]

    if chart_data:
        upsert_chart_cache(symbol, chart_data)
    return chart_data


async def _get_news(symbol: str) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)

    raw_news = await finnhub.get_company_news(symbol, week_ago.isoformat(), today.isoformat())
    raw_news = sorted(raw_news, key=lambda item: item.get("datetime", 0), reverse=True)

    news = []
    for item in raw_news[:MAX_NEWS_ITEMS]:
        published_at = (
            datetime.fromtimestamp(item["datetime"], tz=timezone.utc).isoformat()
            if item.get("datetime")
            else None
        )
        news.append(
            {
                "headline": item.get("headline"),
                "source": item.get("source"),
                "published_at": published_at,
                "sentiment_score": None,
                "url": item.get("url"),
            }
        )

    scores = await asyncio.gather(
        *(asyncio.to_thread(claude_analyst.score_sentiment, item["headline"]) for item in news)
    )
    for item, score in zip(news, scores):
        item["sentiment_score"] = score

    return news


async def _get_filings(symbol: str) -> list[dict]:
    cached = get_cached_filings(symbol)
    if cached is not None:
        return cached

    try:
        filings = await sec_edgar.get_recent_filings(symbol)
    except Exception:
        return []

    if filings:
        upsert_filings_cache(symbol, filings)
    return filings


async def gather_context(symbol: str) -> dict:
    """Everything needed to ground an AI brief or a Q&A answer, minus the AI call itself."""
    symbol = symbol.upper()

    quote = await finnhub.get_quote(symbol)
    if not quote or quote.get("c") in (None, 0):
        raise ValueError(f"No price data found for symbol '{symbol}'")

    fundamentals = await _get_fundamentals(symbol)
    chart_data = await _get_chart_data(symbol)
    news = await _get_news(symbol)
    filings = await _get_filings(symbol)

    price = {
        "last": quote.get("c"),
        "change": quote.get("d"),
        "change_pct": quote.get("dp"),
        "timestamp": datetime.fromtimestamp(quote.get("t", 0), tz=timezone.utc).isoformat()
        if quote.get("t")
        else datetime.now(timezone.utc).isoformat(),
    }

    return {
        "symbol": symbol,
        "price": price,
        "fundamentals": fundamentals,
        "chart_data": chart_data,
        "news": news,
        "filings": filings,
    }
