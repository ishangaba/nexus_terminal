import httpx

from config import settings
from services.errors import wrap_httpx_error

BASE_URL = "https://finnhub.io/api/v1"
PROVIDER = "Finnhub"


async def get_quote(symbol: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/quote",
                params={"symbol": symbol, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc


async def get_company_news(symbol: str, from_date: str, to_date: str) -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/company-news",
                params={
                    "symbol": symbol,
                    "from": from_date,
                    "to": to_date,
                    "token": settings.finnhub_api_key,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc


async def get_company_profile(symbol: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/stock/profile2",
                params={"symbol": symbol, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc
