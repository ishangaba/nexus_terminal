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


async def search_symbols(query: str) -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/search",
                params={"q": query, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            return resp.json().get("result", [])
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc


async def get_earnings(symbol: str) -> list[dict]:
    """EPS actual/estimate/surprise per reported quarter. Verified free-tier."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/stock/earnings",
                params={"symbol": symbol, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc


async def get_insider_transactions(symbol: str) -> list[dict]:
    """Structured Form 4 data (name, shares, transaction code/price/date). Verified free-tier —
    a richer alternative to showing Form 4 as a bare SEC filing link."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/stock/insider-transactions",
                params={"symbol": symbol, "token": settings.finnhub_api_key},
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc


async def get_recommendation_trends(symbol: str) -> list[dict]:
    """Analyst buy/hold/sell counts by period. Verified free-tier (price targets are not —
    that endpoint returns 403 on the free plan, so it's not used here)."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/stock/recommendation",
                params={"symbol": symbol, "token": settings.finnhub_api_key},
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
