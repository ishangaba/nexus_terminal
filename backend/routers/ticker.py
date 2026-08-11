from fastapi import APIRouter, HTTPException

from services.aggregator import get_ticker_snapshot

router = APIRouter(prefix="/api/v1")


@router.get("/ticker/{symbol}")
async def read_ticker(symbol: str):
    try:
        return await get_ticker_snapshot(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream data error: {exc}") from exc
