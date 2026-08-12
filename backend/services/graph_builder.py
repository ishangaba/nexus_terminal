import asyncio
import logging

from db.models import get_ticker, is_graph_stale, mark_graph_built
from services import claude_analyst, graph, sec_edgar, usa_spending

logger = logging.getLogger("graph_builder")

MAX_SUBSIDIARIES = 15
MAX_CONTRACTS = 5


async def _build_subsidiaries(symbol: str) -> None:
    try:
        exhibit_text = await sec_edgar.get_latest_exhibit21_text(symbol)
    except Exception:
        logger.exception("Failed to fetch Exhibit 21 for %s", symbol)
        return
    if not exhibit_text:
        return

    try:
        subsidiaries = await asyncio.to_thread(claude_analyst.extract_subsidiaries, exhibit_text, MAX_SUBSIDIARIES)
    except Exception:
        logger.exception("Failed to extract subsidiaries for %s", symbol)
        return

    for name in subsidiaries:
        await graph.link_subsidiary(symbol, name)


async def _build_contracts(symbol: str, company_name: str) -> None:
    if not company_name:
        return
    try:
        contracts = await usa_spending.get_federal_contracts(company_name, limit=MAX_CONTRACTS)
    except Exception:
        logger.exception("Failed to fetch federal contracts for %s", symbol)
        return

    for contract in contracts:
        if contract["agency"]:
            await graph.link_contract(symbol, contract["agency"], contract["amount"], contract["date"])


async def _build_news_relationships(symbol: str, headlines: list[str]) -> None:
    if not headlines:
        return
    try:
        relationships = await asyncio.to_thread(claude_analyst.extract_relationships, symbol, headlines)
    except Exception:
        logger.exception("Failed to extract news relationships for %s", symbol)
        return

    for rel in relationships:
        await graph.link_news_relationship(symbol, rel.other_ticker.upper(), rel.relationship, rel.evidence)


async def build_company_graph(symbol: str, company_name: str, sector: str, country: str, headlines: list[str]) -> None:
    symbol = symbol.upper()
    await graph.ensure_company(symbol, company_name, sector, country)
    await asyncio.gather(
        _build_subsidiaries(symbol),
        _build_contracts(symbol, company_name),
        _build_news_relationships(symbol, headlines),
    )
    mark_graph_built(symbol)


async def get_or_build_graph(symbol: str, company_name: str, sector: str, country: str, headlines: list[str]) -> dict:
    symbol = symbol.upper()
    if is_graph_stale(symbol):
        await build_company_graph(symbol, company_name, sector, country, headlines)
    return await graph.get_company_subgraph(symbol)
