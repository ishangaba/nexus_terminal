import httpx

from config import settings
from services.errors import wrap_httpx_error

BASE_URL = "https://api.marketaux.com/v1"
PROVIDER = "Marketaux"

# Free tier caps at 3 articles/request — request the max every time.
FREE_TIER_ARTICLE_LIMIT = 3


async def get_company_news(symbol: str) -> list[dict]:
    if not settings.marketaux_api_key:
        return []

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/news/all",
                params={
                    "symbols": symbol,
                    "filter_entities": "true",
                    "language": "en",
                    "limit": FREE_TIER_ARTICLE_LIMIT,
                    "api_token": settings.marketaux_api_key,
                },
            )
            resp.raise_for_status()
            return resp.json().get("data", [])
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc
