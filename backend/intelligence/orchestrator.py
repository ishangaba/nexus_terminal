"""Research Orchestrator — deterministic. `run_research(ticker)` (no categories) runs every
available tool, unchanged since Milestone 1/2. `run_research(ticker, categories=...)` — used by
POST /api/research/query via router_logic.route() — scopes which tool *findings* run, though the
cheap base evidence (price/fundamentals/filings, already fetched regardless) is always included
for context. This is intentionally NOT a multi-agent framework: it's one function that calls
known tools in a fixed order and hands their output to a single synthesis call — see
docs/architecture/roadmap.md for why a heavier router is a deliberately deferred decision.
"""

import asyncio
import logging

from intelligence.evidence_adapters import evidence_from_context
from intelligence.models.evidence import Evidence
from intelligence.models.findings import AnalyticalFinding
from intelligence.models.thesis import ResearchThesis
from intelligence.router_logic import ALL_TOOLS
from intelligence.tools import earnings_tool, fundamentals_tool, graph_tool, macro_tool, news_tool, sec_tool, technical_tool
from services import claude_analyst, finnhub, fred
from services.aggregator import gather_context

logger = logging.getLogger("orchestrator")


async def _fetch_earnings_data(ticker: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Each of the three Finnhub calls degrades independently — one failing (or the free tier
    someday changing) shouldn't take the other two down with it."""

    async def _safe(coro, label: str) -> list[dict]:
        try:
            return await coro
        except Exception:
            logger.exception("Failed to fetch %s for %s", label, ticker)
            return []

    return await asyncio.gather(
        _safe(finnhub.get_earnings(ticker), "earnings surprises"),
        _safe(finnhub.get_insider_transactions(ticker), "insider transactions"),
        _safe(finnhub.get_recommendation_trends(ticker), "recommendation trends"),
    )


async def _fetch_macro_observations() -> dict[str, dict]:
    """Macro data isn't ticker-specific, so this could be cached/shared across requests in a
    later milestone — Milestone 2 keeps it simple and fetches fresh every time (FRED has no
    meaningful rate limit for this volume)."""
    observations: dict[str, dict] = {}

    async def _one(series_id: str) -> None:
        try:
            obs = await fred.get_series_observations(series_id, limit=1)
            if obs:
                observations[series_id] = obs[0]
        except Exception:
            logger.exception("Failed to fetch FRED series %s", series_id)

    await asyncio.gather(*(_one(series_id) for series_id in fred.KEY_SERIES))
    return observations


async def run_research(
    ticker: str, categories: frozenset[str] | None = None, question: str | None = None
) -> ResearchThesis:
    categories = categories if categories is not None else ALL_TOOLS

    context = await gather_context(ticker)
    ticker = context["symbol"]

    # Base evidence (price/fundamentals/filings) is already fetched regardless of which
    # findings run, and costs nothing extra to include — only the *finding* (the synthesized
    # interpretation) is scoped by category.
    evidence: list[Evidence] = evidence_from_context(context)
    findings: list[AnalyticalFinding] = []

    if "technical" in categories:
        tech_evidence, tech_finding = technical_tool.analyze(ticker, context.get("chart_data", []))
        evidence.extend(tech_evidence)
        if tech_finding is not None:
            findings.append(tech_finding)

    if "news" in categories:
        news_evidence, news_finding = news_tool.analyze(ticker, context.get("news", []))
        evidence.extend(news_evidence)
        if news_finding is not None:
            findings.append(news_finding)

    if "fundamentals" in categories:
        fundamentals_finding = fundamentals_tool.analyze(ticker, context["fundamentals"], context["price"], evidence)
        if fundamentals_finding is not None:
            findings.append(fundamentals_finding)

    if "sec_filings" in categories:
        sec_finding = sec_tool.analyze(ticker, context.get("filings", []), evidence)
        if sec_finding is not None:
            findings.append(sec_finding)

    if "earnings" in categories:
        earnings_surprises, insider_transactions, recommendation_trends = await _fetch_earnings_data(ticker)
        earnings_evidence, earnings_findings = earnings_tool.analyze(
            ticker, earnings_surprises, insider_transactions, recommendation_trends
        )
        evidence.extend(earnings_evidence)
        findings.extend(earnings_findings)

    if "macro" in categories:
        macro_observations = await _fetch_macro_observations()
        macro_evidence, macro_finding = macro_tool.analyze(ticker, macro_observations)
        evidence.extend(macro_evidence)
        if macro_finding is not None:
            findings.append(macro_finding)

    if "graph" in categories:
        try:
            graph_evidence, graph_finding = await graph_tool.analyze(ticker)
        except Exception:
            logger.exception("Failed to fetch graph exposure for %s", ticker)
            graph_evidence, graph_finding = [], None
        evidence.extend(graph_evidence)
        if graph_finding is not None:
            findings.append(graph_finding)

    return await _synthesize(ticker, findings, evidence, question)


async def _synthesize(
    ticker: str, findings: list[AnalyticalFinding], evidence: list[Evidence], question: str | None = None
) -> ResearchThesis:
    return await asyncio.to_thread(claude_analyst.synthesize_research, ticker, findings, evidence, question)
