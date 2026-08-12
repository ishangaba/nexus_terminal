import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import claude_analyst
from services.aggregator import gather_context

router = APIRouter(prefix="/api/v1")


class BriefRequest(BaseModel):
    price: dict
    fundamentals: dict
    news: list[dict]
    filings: list[dict]


@router.get("/ticker/{symbol}")
async def read_ticker(symbol: str):
    try:
        return await gather_context(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream data error: {exc}") from exc


@router.post("/ticker/{symbol}/brief")
async def generate_ticker_brief(symbol: str, body: BriefRequest):
    ai_brief = await asyncio.to_thread(
        claude_analyst.generate_brief,
        symbol.upper(),
        body.price,
        body.fundamentals,
        body.news,
        body.filings,
    )
    return {"symbol": symbol.upper(), "ai_brief": ai_brief}
