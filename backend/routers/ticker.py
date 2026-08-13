import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import claude_analyst, finnhub
from services.aggregator import gather_context, get_live_price
from services.errors import ProviderError

router = APIRouter(prefix="/api/v1")

MAX_SEARCH_RESULTS = 8


class BriefRequest(BaseModel):
    price: dict
    fundamentals: dict
    news: list[dict]
    filings: list[dict]


# Registered ahead of /ticker/{symbol} — FastAPI matches path routes in registration order, and
# {symbol} would otherwise greedily capture "search" as a literal ticker symbol.
@router.get("/ticker/search")
async def search_tickers(q: str = ""):
    query = q.strip()
    if not query:
        return {"results": []}

    try:
        raw_results = await finnhub.search_symbols(query)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    # Primary US-listed common stock only — "." in the symbol marks a foreign exchange suffix
    # (e.g. "000651.SZ"), which the rest of the app's data sources (Alpha Vantage, SEC EDGAR,
    # USASpending.gov) don't cover anyway.
    results = [
        {"symbol": item["symbol"], "description": item.get("description", "")}
        for item in raw_results
        if item.get("type") == "Common Stock" and "." not in item.get("symbol", "")
    ]
    return {"results": results[:MAX_SEARCH_RESULTS]}


@router.get("/ticker/{symbol}")
async def read_ticker(symbol: str):
    try:
        return await gather_context(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream data error: {exc}") from exc


@router.get("/ticker/{symbol}/price")
async def read_live_price(symbol: str):
    try:
        return await get_live_price(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc


@router.post("/ticker/{symbol}/brief")
async def generate_ticker_brief(symbol: str, body: BriefRequest):
    try:
        ai_brief = await asyncio.to_thread(
            claude_analyst.generate_brief,
            symbol.upper(),
            body.price,
            body.fundamentals,
            body.news,
            body.filings,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    return {"symbol": symbol.upper(), "ai_brief": ai_brief}
