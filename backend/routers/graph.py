import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.models import get_ticker
from services import claude_analyst, finnhub
from services.graph import GraphUnavailableError
from services.graph_builder import get_or_build_graph

router = APIRouter(prefix="/api/v1")


class GraphInsightsRequest(BaseModel):
    nodes: list[dict]
    edges: list[dict]


async def _recent_headlines(symbol: str, limit: int = 8) -> list[str]:
    today = datetime.now(timezone.utc).date()
    week_ago = today - timedelta(days=7)
    try:
        raw_news = await finnhub.get_company_news(symbol, week_ago.isoformat(), today.isoformat())
    except Exception:
        return []
    raw_news = sorted(raw_news, key=lambda item: item.get("datetime", 0), reverse=True)
    return [item["headline"] for item in raw_news[:limit] if item.get("headline")]


@router.get("/graph/{symbol}")
async def read_company_graph(symbol: str):
    symbol = symbol.upper()
    ticker_info = get_ticker(symbol) or {}
    headlines = await _recent_headlines(symbol)

    try:
        subgraph = await get_or_build_graph(
            symbol,
            ticker_info.get("name") or symbol,
            ticker_info.get("sector") or "",
            ticker_info.get("country") or "",
            headlines,
        )
    except GraphUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail=f"Graph database is unavailable: {exc}"
        ) from exc

    return subgraph


@router.post("/graph/{symbol}/insights")
async def read_graph_insights(symbol: str, body: GraphInsightsRequest):
    insights = await asyncio.to_thread(
        claude_analyst.generate_graph_insights, symbol.upper(), {"nodes": body.nodes, "edges": body.edges}
    )
    return {"symbol": symbol.upper(), "insights": insights}
