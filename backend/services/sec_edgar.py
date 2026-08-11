import httpx

HEADERS = {"User-Agent": "Nexus Terminal (personal project) contact:thegoodstuff4804@gmail.com"}
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"

INTERESTING_FORMS = {"10-K", "10-Q", "8-K", "4"}

_ticker_cik_cache: dict[str, str] | None = None


async def _load_ticker_map() -> dict[str, str]:
    global _ticker_cik_cache
    if _ticker_cik_cache is not None:
        return _ticker_cik_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(TICKER_MAP_URL, headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()

    _ticker_cik_cache = {entry["ticker"].upper(): str(entry["cik_str"]).zfill(10) for entry in data.values()}
    return _ticker_cik_cache


async def get_recent_filings(symbol: str, limit: int = 5) -> list[dict]:
    mapping = await _load_ticker_map()
    cik = mapping.get(symbol.upper())
    if not cik:
        return []

    async with httpx.AsyncClient() as client:
        resp = await client.get(SUBMISSIONS_URL.format(cik=cik), headers=HEADERS)
        resp.raise_for_status()
        data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    filings = []
    for form, date, accession, doc in zip(forms, dates, accession_numbers, primary_docs):
        if form not in INTERESTING_FORMS:
            continue
        accession_nodash = accession.replace("-", "")
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/{doc}"
        filings.append({"form": form, "filed_date": date, "url": url})
        if len(filings) >= limit:
            break

    return filings
