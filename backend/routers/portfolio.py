import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.models import (
    close_position,
    create_position,
    delete_position,
    get_closed_positions,
    get_open_positions,
    get_position,
    get_ticker,
)
from services import finnhub

router = APIRouter(prefix="/api/v1/portfolio")


class PositionCreate(BaseModel):
    symbol: str
    # Short-selling isn't supported yet — the schema allows it for a future migration-free
    # addition, but the P&L/allocation math below only handles long positions correctly.
    side: Literal["long"] = "long"
    quantity: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    entry_date: str
    notes: str | None = None


class PositionClose(BaseModel):
    exit_price: float = Field(gt=0)
    exit_date: str


async def _quote_for(symbol: str) -> dict | None:
    try:
        quote = await finnhub.get_quote(symbol)
    except Exception:
        return None
    if quote.get("c") in (None, 0):
        return None
    return quote


async def _quotes_for(symbols: set[str]) -> dict[str, dict | None]:
    results = await asyncio.gather(*(_quote_for(s) for s in symbols))
    return dict(zip(symbols, results))


def _sector_for(symbol: str) -> str:
    ticker = get_ticker(symbol)
    return (ticker.get("sector") if ticker else None) or "Unknown"


def _open_position_view(row: dict, quote: dict | None) -> dict:
    quantity = row["quantity"]
    cost_basis = row["entry_price"] * quantity
    last_price = quote.get("c") if quote else None

    market_value = unrealized_pnl = unrealized_pnl_pct = None
    quote_error = None
    if last_price is not None:
        market_value = last_price * quantity
        unrealized_pnl = market_value - cost_basis
        unrealized_pnl_pct = (unrealized_pnl / cost_basis * 100) if cost_basis else None
    else:
        quote_error = "Price unavailable for this symbol right now."

    return {
        "id": row["id"],
        "symbol": row["symbol"],
        "side": row["side"],
        "quantity": quantity,
        "entry_price": row["entry_price"],
        "entry_date": row["entry_date"],
        "notes": row["notes"],
        "sector": _sector_for(row["symbol"]),
        "last_price": last_price,
        "market_value": market_value,
        "cost_basis": cost_basis,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "quote_error": quote_error,
    }


def _closed_position_view(row: dict) -> dict:
    quantity = row["quantity"]
    cost_basis = row["entry_price"] * quantity
    realized_pnl = (row["exit_price"] - row["entry_price"]) * quantity
    realized_pnl_pct = (realized_pnl / cost_basis * 100) if cost_basis else None

    return {
        "id": row["id"],
        "symbol": row["symbol"],
        "side": row["side"],
        "quantity": quantity,
        "entry_price": row["entry_price"],
        "entry_date": row["entry_date"],
        "exit_price": row["exit_price"],
        "exit_date": row["exit_date"],
        "notes": row["notes"],
        "realized_pnl": realized_pnl,
        "realized_pnl_pct": realized_pnl_pct,
    }


def _allocation(open_views: list[dict]) -> dict:
    total = sum(p["market_value"] for p in open_views if p["market_value"] is not None)

    def _breakdown(key: str) -> list[dict]:
        totals: dict[str, float] = {}
        for p in open_views:
            if p["market_value"] is None:
                continue
            totals[p[key]] = totals.get(p[key], 0) + p["market_value"]
        return [
            {"name": name, "market_value": value, "pct_of_portfolio": (value / total * 100) if total else 0}
            for name, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)
        ]

    return {"by_symbol": _breakdown("symbol"), "by_sector": _breakdown("sector")}


@router.get("")
async def read_portfolio():
    open_rows = get_open_positions()
    closed_rows = get_closed_positions()

    symbols = {row["symbol"] for row in open_rows}
    quotes = await _quotes_for(symbols) if symbols else {}

    open_views = [_open_position_view(row, quotes.get(row["symbol"])) for row in open_rows]
    closed_views = [_closed_position_view(row) for row in closed_rows]

    # Only aggregate positions we actually have a live price for — mixing a priced position's
    # market value with an unpriced position's cost basis would understate value without
    # understating cost, producing a misleading "loss" that's really just a missing quote.
    priced_views = [p for p in open_views if p["market_value"] is not None]
    total_market_value = sum(p["market_value"] for p in priced_views)
    total_cost_basis = sum(p["cost_basis"] for p in priced_views)
    total_unrealized_pnl = total_market_value - total_cost_basis
    total_realized_pnl = sum(p["realized_pnl"] for p in closed_views)

    summary = {
        "total_market_value": total_market_value,
        "total_cost_basis": total_cost_basis,
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_unrealized_pnl_pct": (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis else 0,
        "total_realized_pnl": total_realized_pnl,
        "open_position_count": len(open_views),
        "closed_position_count": len(closed_views),
    }

    return {
        "summary": summary,
        "open_positions": open_views,
        "closed_positions": closed_views,
        "allocation": _allocation(open_views),
    }


@router.post("/positions")
async def add_position(body: PositionCreate):
    symbol = body.symbol.upper()
    quote = await _quote_for(symbol)
    if quote is None:
        raise HTTPException(status_code=404, detail=f"No price data found for symbol '{symbol}'")

    position_id = create_position(symbol, body.side, body.quantity, body.entry_price, body.entry_date, body.notes)
    row = get_position(position_id)
    return _open_position_view(row, quote)


@router.post("/positions/{position_id}/close")
async def close_position_endpoint(position_id: int, body: PositionClose):
    row = get_position(position_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Position not found")
    if row["exit_price"] is not None:
        raise HTTPException(status_code=409, detail="Position is already closed")

    close_position(position_id, body.exit_price, body.exit_date)
    updated = get_position(position_id)
    return _closed_position_view(updated)


@router.delete("/positions/{position_id}")
def delete_position_endpoint(position_id: int):
    deleted = delete_position(position_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Position not found")
    return {"deleted": True}
