import httpx

from config import settings

BASE_URL = "https://www.alphavantage.co/query"


async def get_overview(symbol: str) -> dict:
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


async def get_daily_series(symbol: str) -> dict:
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
