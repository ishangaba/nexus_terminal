import httpx

from config import settings
from services.errors import wrap_httpx_error

BASE_URL = "https://api.stlouisfed.org/fred"
PROVIDER = "FRED"

# A small, fixed set of the most broadly relevant macro series — not an exhaustive FRED catalog
# (800,000+ series exist). CPI (inflation), unemployment, and the Fed funds rate cover the
# macro backdrop most research questions actually care about.
KEY_SERIES = {
    "CPIAUCSL": "CPI (all urban consumers)",
    "UNRATE": "Unemployment rate",
    "FEDFUNDS": "Federal funds effective rate",
}


async def get_series_observations(series_id: str, limit: int = 1) -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{BASE_URL}/series/observations",
                params={
                    "series_id": series_id,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": limit,
                    "api_key": settings.fred_api_key,
                },
            )
            resp.raise_for_status()
            return resp.json().get("observations", [])
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc
