import asyncio
from datetime import datetime, timedelta, timezone

from db.models import (
    get_cached_chart,
    get_cached_filings,
    get_cached_fundamentals,
    get_cached_news,
    upsert_chart_cache,
    upsert_filings_cache,
    upsert_fundamentals_cache,
    upsert_news_cache,
    upsert_ticker,
)
from services import alpha_vantage, claude_analyst, finnhub, marketaux, sec_edgar
from services.errors import ProviderError

MAX_NEWS_ITEMS = 8
FINNHUB_NEWS_CANDIDATES = 6
CHART_DAYS = 100


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


async def _get_fundamentals(symbol: str) -> tuple[dict, str | None]:
    cached = get_cached_fundamentals(symbol)
    if cached is not None:
        return {
            "pe_ratio": cached["pe_ratio"],
            "market_cap": cached["market_cap"],
            "eps": cached["eps"],
            "52_week_high": cached["week_52_high"],
            "52_week_low": cached["week_52_low"],
        }, None

    empty = {"pe_ratio": None, "market_cap": None, "eps": None, "52_week_high": None, "52_week_low": None}

    try:
        overview = await alpha_vantage.get_overview(symbol)
        _check_alpha_vantage_error(overview)
    except AlphaVantageRateLimitError as exc:
        return empty, f"Alpha Vantage: {exc}"
    except ProviderError as exc:
        return empty, exc.message

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
    }, None


async def get_chart_data(symbol: str) -> tuple[list[dict], str | None]:
    """Cached daily OHLCV series for a symbol. Public: also used by the signal evaluator to
    compute forward returns without spending a separate Alpha Vantage call per lookup."""
    cached = get_cached_chart(symbol)
    if cached is not None:
        return cached, None

    try:
        series = await alpha_vantage.get_daily_series(symbol)
        _check_alpha_vantage_error(series)
    except AlphaVantageRateLimitError as exc:
        return [], f"Alpha Vantage: {exc}"
    except ProviderError as exc:
        return [], exc.message

    daily = series.get("Time Series (Daily)", {})
    chart_data = [
        {
            "date": date,
            "open": _safe_float(values.get("1. open")),
            "high": _safe_float(values.get("2. high")),
            "low": _safe_float(values.get("3. low")),
            "close": _safe_float(values.get("4. close")),
            "volume": _safe_float(values.get("5. volume")),
        }
        for date, values in sorted(daily.items())[-CHART_DAYS:]
    ]

    if chart_data:
        upsert_chart_cache(symbol, chart_data)
    return chart_data, None


def _parse_iso(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


async def _fetch_finnhub_news(symbol: str) -> tuple[list[dict], str | None]:
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)

    try:
        raw_news = await finnhub.get_company_news(symbol, week_ago.isoformat(), today.isoformat())
    except ProviderError as exc:
        return [], exc.message

    raw_news = sorted(raw_news, key=lambda item: item.get("datetime", 0), reverse=True)

    news = []
    for item in raw_news[:FINNHUB_NEWS_CANDIDATES]:
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
    return news, None


async def _fetch_marketaux_news(symbol: str) -> tuple[list[dict], str | None]:
    try:
        raw_news = await marketaux.get_company_news(symbol)
    except ProviderError as exc:
        return [], exc.message
    except Exception:
        return [], None

    return [
        {
            "headline": item.get("title"),
            "source": item.get("source"),
            "published_at": item.get("published_at"),
            "sentiment_score": None,
            "url": item.get("url"),
        }
        for item in raw_news
    ], None


async def _get_news(symbol: str) -> tuple[list[dict], str | None]:
    cached = get_cached_news(symbol)
    if cached is not None:
        return cached, None

    (finnhub_news, finnhub_err), (marketaux_news, marketaux_err) = await asyncio.gather(
        _fetch_finnhub_news(symbol), _fetch_marketaux_news(symbol)
    )

    seen_headlines = set()
    merged = []
    for item in finnhub_news + marketaux_news:
        if not item.get("headline"):
            continue
        key = item["headline"].strip().lower()
        if key in seen_headlines:
            continue
        seen_headlines.add(key)
        merged.append(item)

    merged.sort(key=lambda item: _parse_iso(item.get("published_at")), reverse=True)
    news = merged[:MAX_NEWS_ITEMS]

    sentiment_err = None
    try:
        scores = await asyncio.gather(
            *(asyncio.to_thread(claude_analyst.score_sentiment, item["headline"]) for item in news)
        )
        for item, score in zip(news, scores):
            item["sentiment_score"] = score
    except ProviderError as exc:
        sentiment_err = f"AI sentiment scoring unavailable ({exc.message})"
        for item in news:
            item["sentiment_score"] = None

    errors = [e for e in (finnhub_err, marketaux_err, sentiment_err) if e]
    error_message = "; ".join(errors) if errors else None

    # Only cache clean fetches — caching a partial/failed result would hide the error
    # (and the empty/degraded data) behind the TTL for anyone searching this symbol next.
    if error_message is None:
        upsert_news_cache(symbol, news)
    return news, error_message


async def _get_filings(symbol: str) -> tuple[list[dict], str | None]:
    cached = get_cached_filings(symbol)
    if cached is not None:
        return cached, None

    try:
        filings = await sec_edgar.get_recent_filings(symbol)
    except ProviderError as exc:
        return [], exc.message
    except Exception as exc:
        return [], f"SEC EDGAR: unexpected error ({exc})."

    if filings:
        upsert_filings_cache(symbol, filings)
    return filings, None


def _build_price(quote: dict) -> dict:
    return {
        "last": quote.get("c"),
        "change": quote.get("d"),
        "change_pct": quote.get("dp"),
        "open": quote.get("o"),
        "high": quote.get("h"),
        "low": quote.get("l"),
        "timestamp": datetime.fromtimestamp(quote.get("t", 0), tz=timezone.utc).isoformat()
        if quote.get("t")
        else datetime.now(timezone.utc).isoformat(),
    }


async def get_live_price(symbol: str) -> dict:
    """Just the live quote — used for lightweight price-only refreshes (no chart/news/etc)."""
    symbol = symbol.upper()
    quote = await finnhub.get_quote(symbol)
    if not quote or quote.get("c") in (None, 0):
        raise ValueError(f"No price data found for symbol '{symbol}'")
    return _build_price(quote)


async def gather_context(symbol: str) -> dict:
    """Everything needed to ground an AI brief or a Q&A answer, minus the AI call itself."""
    symbol = symbol.upper()

    quote = await finnhub.get_quote(symbol)
    if not quote or quote.get("c") in (None, 0):
        raise ValueError(f"No price data found for symbol '{symbol}'")

    fundamentals, fundamentals_err = await _get_fundamentals(symbol)
    chart_data, chart_err = await get_chart_data(symbol)
    news, news_err = await _get_news(symbol)
    filings, filings_err = await _get_filings(symbol)

    price = _build_price(quote)

    errors = {
        key: message
        for key, message in {
            "fundamentals": fundamentals_err,
            "chart_data": chart_err,
            "news": news_err,
            "filings": filings_err,
        }.items()
        if message
    }

    return {
        "symbol": symbol,
        "price": price,
        "fundamentals": fundamentals,
        "chart_data": chart_data,
        "news": news,
        "filings": filings,
        "errors": errors,
    }
