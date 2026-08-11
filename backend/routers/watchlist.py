import asyncio

from fastapi import APIRouter, HTTPException

from db.models import add_to_watchlist, get_watchlist, remove_from_watchlist
from services import finnhub

router = APIRouter(prefix="/api/v1/watchlist")


async def _quote_for(symbol: str) -> dict:
    try:
        quote = await finnhub.get_quote(symbol)
    except Exception:
        quote = {}
    return {
        "symbol": symbol,
        "last": quote.get("c"),
        "change": quote.get("d"),
        "change_pct": quote.get("dp"),
    }


@router.get("")
async def read_watchlist():
    symbols = get_watchlist()
    quotes = await asyncio.gather(*(_quote_for(symbol) for symbol in symbols))
    return {"watchlist": quotes}


@router.post("/{symbol}")
def add_watchlist_item(symbol: str):
    add_to_watchlist(symbol.upper())
    return {"watchlist": get_watchlist()}


@router.delete("/{symbol}")
def delete_watchlist_item(symbol: str):
    removed = remove_from_watchlist(symbol.upper())
    if not removed:
        raise HTTPException(status_code=404, detail=f"'{symbol.upper()}' is not on the watchlist")
    return {"watchlist": get_watchlist()}
