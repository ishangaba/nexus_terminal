from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from intelligence.orchestrator import run_research
from intelligence.router_logic import route
from services.errors import ProviderError

router = APIRouter(prefix="/api/research")


class ResearchQueryRequest(BaseModel):
    ticker: str
    question: str = Field(min_length=1, max_length=500)


# Registered ahead of /{ticker} — FastAPI matches path routes in registration order, and
# {ticker} would otherwise greedily capture "query" as a literal ticker symbol (same pitfall as
# /ticker/search vs /ticker/{symbol} in routers/ticker.py).
@router.post("/query")
async def research_query(body: ResearchQueryRequest):
    categories = route(body.question)
    try:
        thesis = await run_research(body.ticker.upper(), categories=categories, question=body.question)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research pipeline error: {exc}") from exc

    return {"thesis": thesis, "tools_used": sorted(categories)}


@router.post("/{ticker}")
async def research_ticker(ticker: str):
    try:
        thesis = await run_research(ticker.upper())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Research pipeline error: {exc}") from exc

    return thesis
