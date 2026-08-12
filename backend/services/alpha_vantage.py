import httpx

from config import settings
from services.errors import wrap_httpx_error

BASE_URL = "https://www.alphavantage.co/query"
PROVIDER = "Alpha Vantage"


async def get_overview(symbol: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                BASE_URL,
                params={
                    "function": "OVERVIEW",
                    "symbol": symbol,
                    "apikey": settings.alpha_vantage_api_key,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc


async def get_daily_series(symbol: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                BASE_URL,
                params={
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "apikey": settings.alpha_vantage_api_key,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc
