"""Pure-logic tests for the graph provenance/confidence work (Milestone 5). No ArcadeDB
required — these test row parsing and aggregation, the same split other tools use (deterministic
logic tested directly; the live ArcadeDB round-trip is verified manually, matching Milestone
1-3's testing posture for provider-backed code)."""

import asyncio

from services import graph
from intelligence.tools import graph_tool


def _row(rel_rid, rel_type, confidence=None, retrieved_at=None, evidence=None, amount=None, date=None):
    return {
        "c": {"@rid": "#1:0", "@type": "Company", "symbol": "AAPL", "name": "Apple Inc", "country": "USA"},
        "r": {
            "@rid": rel_rid, "@type": rel_type, "@out": "#1:0", "@in": "#3:0",
            "confidence": confidence, "retrieved_at": retrieved_at,
            "evidence": evidence, "amount": amount, "date": date,
        },
        "n": {"@rid": "#3:0", "@type": "Company", "symbol": "TSM", "name": "Taiwan Semiconductor", "country": "Taiwan"},
    }


def test_parse_rows_extracts_nodes_with_country_and_edge_with_confidence():
    nodes, rid_to_id, edges, seen = {}, {}, [], set()
    rows = [_row("#2:0", "SUPPLIES_TO", confidence=0.6, retrieved_at="2026-01-01T00:00:00+00:00", evidence="ev")]

    graph._parse_rows(rows, nodes, rid_to_id, edges, seen)

    assert nodes["AAPL"]["country"] == "USA"
    assert nodes["TSM"]["country"] == "Taiwan"
    assert len(edges) == 1
    assert edges[0]["source"] == "AAPL"
    assert edges[0]["target"] == "TSM"
    assert edges[0]["confidence"] == 0.6


def test_parse_rows_dedupes_by_relationship_rid():
    nodes, rid_to_id, edges, seen = {}, {}, [], set()
    rows = [_row("#2:0", "SUPPLIES_TO"), _row("#2:0", "SUPPLIES_TO")]  # same edge seen twice

    graph._parse_rows(rows, nodes, rid_to_id, edges, seen)

    assert len(edges) == 1


def test_parse_rows_leaves_legacy_edges_confidence_null_not_guessed():
    nodes, rid_to_id, edges, seen = {}, {}, [], set()
    rows = [_row("#2:0", "SUPPLIES_TO")]  # no confidence/retrieved_at — pre-migration edge

    graph._parse_rows(rows, nodes, rid_to_id, edges, seen)

    assert edges[0]["confidence"] is None
    assert edges[0]["retrieved_at"] is None


def test_analyze_falls_back_to_inferred_confidence_for_legacy_edges(monkeypatch):
    async def fake_subgraph(ticker):
        return {
            "nodes": [{"id": "AAPL", "symbol": "AAPL"}, {"id": "TSM", "symbol": "TSM"}],
            "edges": [{"type": "SUPPLIES_TO", "target": "TSM", "confidence": None, "retrieved_at": None, "evidence": "e"}],
        }

    monkeypatch.setattr(graph_tool, "get_company_subgraph", fake_subgraph)

    evidence, finding = asyncio.run(graph_tool.analyze("AAPL"))

    assert evidence[0].confidence == graph.INFERRED_CONFIDENCE
    assert finding.direction == "neutral"  # relationship existence alone is never directional


def test_analyze_returns_confirmed_confidence_when_present(monkeypatch):
    async def fake_subgraph(ticker):
        return {
            "nodes": [],
            "edges": [{"type": "HAS_CONTRACT", "target": "DOD", "confidence": 1.0, "retrieved_at": "2026-01-01T00:00:00+00:00", "amount": 5000, "date": "2026-01-01"}],
        }

    monkeypatch.setattr(graph_tool, "get_company_subgraph", fake_subgraph)

    evidence, finding = asyncio.run(graph_tool.analyze("AAPL"))

    assert evidence[0].confidence == 1.0
    assert evidence[0].evidence_type.value == "GOVERNMENT_CONTRACT"


def test_analyze_skips_structural_subsidiary_edges(monkeypatch):
    async def fake_subgraph(ticker):
        return {"nodes": [], "edges": [{"type": "SUBSIDIARY_OF", "target": "PARENT", "confidence": 1.0}]}

    monkeypatch.setattr(graph_tool, "get_company_subgraph", fake_subgraph)

    evidence, finding = asyncio.run(graph_tool.analyze("SUB"))

    assert evidence == []
    assert finding is None


def test_analyze_handles_graph_unavailable_gracefully(monkeypatch):
    async def fake_subgraph(ticker):
        raise graph.GraphUnavailableError("db down")

    monkeypatch.setattr(graph_tool, "get_company_subgraph", fake_subgraph)

    evidence, finding = asyncio.run(graph_tool.analyze("AAPL"))

    assert evidence == []
    assert finding is None


def test_concentration_summary_counts_relationships_and_countries():
    subgraph = {
        "nodes": [
            {"id": "AAPL", "type": "Company", "country": "USA"},
            {"id": "TSM", "type": "Company", "country": "Taiwan"},
            {"id": "DOD", "type": "GovEntity", "country": None},
        ],
        "edges": [
            {"type": "SUPPLIES_TO", "target": "TSM"},
            {"type": "HAS_CONTRACT", "target": "DOD"},
            {"type": "HAS_CONTRACT", "target": "DOD"},
        ],
    }

    summary = graph_tool.concentration_summary(subgraph)

    assert summary["relationship_counts"] == {"SUPPLIES_TO": 1, "HAS_CONTRACT": 2}
    assert summary["government_agencies"] == ["DOD"]
    assert summary["country_exposure"] == {"USA": 1, "Taiwan": 1}
