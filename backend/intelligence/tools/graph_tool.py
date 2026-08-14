"""Deterministic synthesis over the company relationship graph (subsidiaries, government
contracts, and Claude-inferred supplier/competitor/partner relationships from news). No new LLM
call here — inference into edges already happened in graph_builder.py at build time; this tool
only reasons over what's already in the graph, the same way sec_tool/fundamentals_tool reason
over already-fetched data rather than re-fetching.

Relationship existence isn't inherently bullish or bearish for the ticker — a competitor
appearing in the graph doesn't say whether that's good or bad news this week — so, like
macro_tool and sec_tool, this always reports a neutral direction. It surfaces WHAT the exposure
is; Claude synthesis decides whether it matters for a given question.
"""

import uuid
from datetime import datetime, timezone

from intelligence.models.evidence import Evidence, EvidenceType
from intelligence.models.findings import AnalyticalFinding
from services.graph import GraphUnavailableError, INFERRED_CONFIDENCE, get_company_subgraph

CATEGORY = "graph"

# SUBSIDIARY_OF is structural (ownership), not a relationship claim worth its own evidence row —
# it's already represented as a node/edge in the graph itself and doesn't need re-surfacing here.
RELATIONSHIP_EVIDENCE_TYPE = {
    "SUPPLIES_TO": EvidenceType.SUPPLY_CHAIN_RELATIONSHIP,
    "PARTNERS_WITH": EvidenceType.SUPPLY_CHAIN_RELATIONSHIP,
    "COMPETES_WITH": EvidenceType.COMPETITOR_RELATIONSHIP,
    "HAS_CONTRACT": EvidenceType.GOVERNMENT_CONTRACT,
}


def _new_id() -> str:
    return uuid.uuid4().hex


async def analyze(ticker: str) -> tuple[list[Evidence], AnalyticalFinding | None]:
    try:
        subgraph = await get_company_subgraph(ticker)
    except GraphUnavailableError:
        return [], None

    retrieved_at = datetime.now(timezone.utc)
    evidence: list[Evidence] = []
    counts: dict[str, int] = {}

    for edge in subgraph["edges"]:
        evidence_type = RELATIONSHIP_EVIDENCE_TYPE.get(edge["type"])
        if evidence_type is None:
            continue
        counts[edge["type"]] = counts.get(edge["type"], 0) + 1

        observed_at = retrieved_at
        if edge.get("retrieved_at"):
            try:
                observed_at = datetime.fromisoformat(edge["retrieved_at"])
            except ValueError:
                pass

        evidence.append(
            Evidence(
                id=_new_id(),
                ticker=ticker,
                evidence_type=evidence_type,
                source="usa_spending" if edge["type"] == "HAS_CONTRACT" else "graph (news-inferred)",
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                value={"target": edge["target"], "type": edge["type"], "evidence": edge.get("evidence")},
                # Falls back to INFERRED_CONFIDENCE for edges written before confidence tracking
                # shipped — an explicit, documented default rather than an implicit null.
                confidence=edge["confidence"] if edge.get("confidence") is not None else INFERRED_CONFIDENCE,
                metadata={"amount": edge.get("amount"), "date": edge.get("date")},
            )
        )

    if not evidence:
        return [], None

    summary_parts = [f"{n} {edge_type.replace('_', ' ').lower()}" for edge_type, n in counts.items()]
    finding = AnalyticalFinding(
        category=CATEGORY,
        summary="Company graph shows: " + ", ".join(summary_parts) + ".",
        direction="neutral",
        confidence=0.5,
        evidence_ids=[e.id for e in evidence],
        risks=[],
        metadata={"relationship_counts": counts},
    )
    return evidence, finding


def concentration_summary(subgraph: dict) -> dict:
    """Pure aggregation over an already-fetched subgraph (1-hop or 2-hop) — relationship-type
    counts, government-agency exposure, and country exposure of connected companies. Used by
    Milestone 6's portfolio intelligence rather than the research orchestrator."""
    by_type: dict[str, int] = {}
    gov_agencies: set[str] = set()
    countries: dict[str, int] = {}

    for edge in subgraph["edges"]:
        by_type[edge["type"]] = by_type.get(edge["type"], 0) + 1
        if edge["type"] == "HAS_CONTRACT":
            gov_agencies.add(edge["target"])

    for node in subgraph["nodes"]:
        if node["type"] == "Company" and node.get("country"):
            countries[node["country"]] = countries.get(node["country"], 0) + 1

    return {
        "relationship_counts": by_type,
        "government_agencies": sorted(gov_agencies),
        "country_exposure": countries,
    }
