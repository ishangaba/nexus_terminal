import re

import httpx

from services.errors import wrap_httpx_error

HEADERS = {"User-Agent": "Nexus Terminal (personal project) contact:thegoodstuff4804@gmail.com"}
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
PROVIDER = "SEC EDGAR"

INTERESTING_FORMS = {"10-K", "10-Q", "8-K", "4"}
EXHIBIT_21_PATTERN = re.compile(r"ex.*21", re.IGNORECASE)
MAX_EXHIBIT_TEXT_CHARS = 12000

_ticker_cik_cache: dict[str, str] | None = None


async def _load_ticker_map() -> dict[str, str]:
    global _ticker_cik_cache
    if _ticker_cik_cache is not None:
        return _ticker_cik_cache

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(TICKER_MAP_URL, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc

    _ticker_cik_cache = {entry["ticker"].upper(): str(entry["cik_str"]).zfill(10) for entry in data.values()}
    return _ticker_cik_cache


async def _get_cik(symbol: str) -> str | None:
    mapping = await _load_ticker_map()
    return mapping.get(symbol.upper())


async def _get_submissions(cik: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(SUBMISSIONS_URL.format(cik=cik), headers=HEADERS)
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise wrap_httpx_error(PROVIDER, exc) from exc


async def get_recent_filings(symbol: str, limit: int = 5) -> list[dict]:
    cik = await _get_cik(symbol)
    if not cik:
        return []

    data = await _get_submissions(cik)
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


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&#160;|&nbsp;", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


async def get_latest_exhibit21_text(symbol: str) -> str | None:
    """Fetch and clean the Exhibit 21 (subsidiaries) text from the most recent 10-K, if one exists."""
    cik = await _get_cik(symbol)
    if not cik:
        return None

    data = await _get_submissions(cik)
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accession_numbers = recent.get("accessionNumber", [])

    accession = next((accn for form, accn in zip(forms, accession_numbers) if form == "10-K"), None)
    if not accession:
        return None

    accession_nodash = accession.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/index.json"

    async with httpx.AsyncClient() as client:
        index_resp = await client.get(index_url, headers=HEADERS)
        if index_resp.status_code != 200:
            return None
        items = index_resp.json().get("directory", {}).get("item", [])

        exhibit_doc = next((item["name"] for item in items if EXHIBIT_21_PATTERN.search(item["name"])), None)
        if not exhibit_doc:
            return None

        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/{exhibit_doc}"
        doc_resp = await client.get(doc_url, headers=HEADERS)
        doc_resp.raise_for_status()

    return _strip_html(doc_resp.text)[:MAX_EXHIBIT_TEXT_CHARS]
