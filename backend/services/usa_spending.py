from datetime import date, timedelta

import httpx

from services.errors import wrap_httpx_error

SEARCH_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
PROVIDER = "USASpending.gov"
AWARD_TYPE_CODES = ["A", "B", "C", "D"]  # contracts (definitive, BPA call, delivery order, IDV)
LOOKBACK_YEARS = 3


async def get_federal_contracts(company_name: str, limit: int = 5) -> list[dict]:
    if not company_name:
        return []

    start_date = (date.today() - timedelta(days=365 * LOOKBACK_YEARS)).isoformat()
    end_date = date.today().isoformat()

    payload = {
        "filters": {
            "recipient_search_text": [company_name],
            "award_type_codes": AWARD_TYPE_CODES,
            "time_period": [{"start_date": start_date, "end_date": end_date}],
        },
        "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency", "Start Date", "Description"],
        "page": 1,
        "limit": limit,
        "sort": "Award Amount",
        "order": "desc",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(SEARCH_URL, json=payload)
            if resp.status_code != 200:
                return []
            data = resp.json()
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc

    contracts = []
    for award in data.get("results", []):
        contracts.append(
            {
                "agency": award.get("Awarding Agency"),
                "amount": award.get("Award Amount"),
                "date": award.get("Start Date"),
                "description": (award.get("Description") or "")[:200] or None,
            }
        )
    return contracts
