import asyncio
from datetime import datetime, timezone

import httpx

from config import settings


class GraphUnavailableError(Exception):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_cypher(command: str, params: dict | None = None) -> list[dict]:
    url = f"{settings.arcadedb_url}/api/v1/command/{settings.arcadedb_database}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                json={"language": "cypher", "command": command, "params": params or {}},
                auth=(settings.arcadedb_user, settings.arcadedb_password),
            )
            resp.raise_for_status()
            return resp.json().get("result", [])
    except httpx.HTTPError as exc:
        raise GraphUnavailableError(str(exc)) from exc


async def ensure_company(symbol: str, name: str = "", sector: str = "", country: str = "") -> None:
    await run_cypher(
        """
        MERGE (c:Company {symbol: $symbol})
        SET c.name = CASE WHEN $name <> '' THEN $name ELSE c.name END,
            c.sector = CASE WHEN $sector <> '' THEN $sector ELSE c.sector END,
            c.country = CASE WHEN $country <> '' THEN $country ELSE c.country END
        """,
        {"symbol": symbol, "name": name, "sector": sector, "country": country},
    )


async def ensure_gov_entity(name: str) -> None:
    await run_cypher("MERGE (g:GovEntity {name: $name})", {"name": name})


# Confidence convention (matches intelligence/models/evidence.py): 1.0 for edges sourced from a
# primary record (SEC Exhibit 21, USASpending.gov contract data); < 1.0 for edges Claude
# inferred from a news headline, since that's an interpretation rather than a confirmed fact.
CONFIRMED_CONFIDENCE = 1.0
INFERRED_CONFIDENCE = 0.6


async def link_subsidiary(parent_symbol: str, subsidiary_name: str, confidence: float = CONFIRMED_CONFIDENCE) -> None:
    await run_cypher(
        """
        MERGE (parent:Company {symbol: $parent_symbol})
        MERGE (sub:Company {name: $sub_name})
        ON CREATE SET sub.symbol = ''
        MERGE (sub)-[r:SUBSIDIARY_OF]->(parent)
        SET r.confidence = $confidence, r.retrieved_at = $retrieved_at
        """,
        {
            "parent_symbol": parent_symbol, "sub_name": subsidiary_name,
            "confidence": confidence, "retrieved_at": _now_iso(),
        },
    )


async def link_contract(
    company_symbol: str, gov_entity_name: str, amount: float | None, date: str | None,
    confidence: float = CONFIRMED_CONFIDENCE,
) -> None:
    await run_cypher(
        """
        MERGE (c:Company {symbol: $symbol})
        MERGE (g:GovEntity {name: $gov_name})
        MERGE (c)-[r:HAS_CONTRACT]->(g)
        SET r.amount = $amount, r.date = $date, r.confidence = $confidence, r.retrieved_at = $retrieved_at
        """,
        {
            "symbol": company_symbol, "gov_name": gov_entity_name, "amount": amount, "date": date,
            "confidence": confidence, "retrieved_at": _now_iso(),
        },
    )


VALID_NEWS_RELATIONSHIPS = {"SUPPLIES_TO", "COMPETES_WITH", "PARTNERS_WITH"}


async def link_news_relationship(
    from_symbol: str, to_symbol: str, relationship: str, evidence: str,
    confidence: float = INFERRED_CONFIDENCE,
) -> None:
    if relationship not in VALID_NEWS_RELATIONSHIPS:
        return
    await run_cypher(
        f"""
        MERGE (a:Company {{symbol: $from_symbol}})
        MERGE (b:Company {{symbol: $to_symbol}})
        MERGE (a)-[r:{relationship}]->(b)
        SET r.evidence = $evidence, r.confidence = $confidence, r.retrieved_at = $retrieved_at
        """,
        {
            "from_symbol": from_symbol, "to_symbol": to_symbol, "evidence": evidence,
            "confidence": confidence, "retrieved_at": _now_iso(),
        },
    )


async def _fetch_1hop_rows(symbol: str) -> list[dict]:
    return await run_cypher(
        """
        MATCH (c:Company {symbol: $symbol})
        OPTIONAL MATCH (c)-[r]-(n)
        RETURN c, r, n
        """,
        {"symbol": symbol},
    )


def _parse_rows(
    rows: list[dict], nodes: dict[str, dict], rid_to_id: dict[str, str],
    edges: list[dict], seen_edges: set[str],
) -> None:
    """Shared row -> nodes/edges parsing, used by both the 1-hop and 2-hop traversals so the
    ArcadeDB response shape is only ever interpreted in one place."""

    def add_node(entity: dict) -> str:
        node_id = entity.get("symbol") or entity.get("name") or entity["@rid"]
        rid_to_id[entity["@rid"]] = node_id
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": entity.get("name") or entity.get("symbol") or node_id,
                "type": entity.get("@type", "Unknown"),
                "symbol": entity.get("symbol"),
                "country": entity.get("country") or None,
            }
        return node_id

    for row in rows:
        center = row.get("c")
        if not center:
            continue
        add_node(center)

        rel = row.get("r")
        other = row.get("n")
        if rel and other:
            add_node(other)
            edge_key = rel["@rid"]
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)
            edges.append(
                {
                    "source": rid_to_id.get(rel["@out"], rid_to_id.get(center["@rid"])),
                    "target": rid_to_id.get(rel["@in"], rid_to_id.get(other["@rid"])),
                    "type": rel.get("@type", "RELATED_TO"),
                    "amount": rel.get("amount"),
                    "date": rel.get("date"),
                    "evidence": rel.get("evidence"),
                    # None on edges written before this migration shipped — they self-heal to a
                    # real value on the next weekly rebuild (build_company_graph re-MERGEs and
                    # re-SETs every edge it touches), so no separate backfill script is needed.
                    "confidence": rel.get("confidence"),
                    "retrieved_at": rel.get("retrieved_at"),
                }
            )


async def get_company_subgraph(symbol: str) -> dict:
    """Return the primary company plus everything 1 hop away, as nodes + edges for visualization."""
    nodes: dict[str, dict] = {}
    rid_to_id: dict[str, str] = {}
    edges: list[dict] = []
    seen_edges: set[str] = set()

    rows = await _fetch_1hop_rows(symbol)
    _parse_rows(rows, nodes, rid_to_id, edges, seen_edges)

    return {"nodes": list(nodes.values()), "edges": edges}


MAX_2HOP_NEIGHBORS = 8  # caps fan-out so a densely-connected company doesn't trigger dozens of extra queries


async def get_2hop_exposure(symbol: str) -> dict:
    """1-hop subgraph plus a second hop out from each directly-connected company — e.g. "who's
    2 hops from a Taiwan-exposed supplier". Implemented as chained 1-hop queries rather than a
    variable-length Cypher path, reusing the same well-tested row parsing instead of trusting an
    untested traversal syntax against ArcadeDB's Cypher dialect."""
    nodes: dict[str, dict] = {}
    rid_to_id: dict[str, str] = {}
    edges: list[dict] = []
    seen_edges: set[str] = set()

    rows = await _fetch_1hop_rows(symbol)
    _parse_rows(rows, nodes, rid_to_id, edges, seen_edges)

    first_hop_symbols = [n["symbol"] for n in nodes.values() if n["symbol"] and n["symbol"] != symbol]
    first_hop_symbols = first_hop_symbols[:MAX_2HOP_NEIGHBORS]

    second_hop_results = await asyncio.gather(
        *(_fetch_1hop_rows(s) for s in first_hop_symbols), return_exceptions=True
    )
    for result in second_hop_results:
        if isinstance(result, BaseException):
            continue
        _parse_rows(result, nodes, rid_to_id, edges, seen_edges)

    return {"nodes": list(nodes.values()), "edges": edges}


async def get_portfolio_exposure(symbols: list[str]) -> dict:
    """For each portfolio symbol, fetch its 1-hop neighborhood, then surface which non-portfolio
    nodes are shared by more than one holding — the concentration signal a single-company view
    can't show (e.g. three holdings all sharing the same government customer or supplier)."""
    unique_symbols = list(dict.fromkeys(s.upper() for s in symbols))
    subgraphs = await asyncio.gather(
        *(get_company_subgraph(s) for s in unique_symbols), return_exceptions=True
    )

    shared: dict[str, dict] = {}
    for symbol, result in zip(unique_symbols, subgraphs):
        if isinstance(result, BaseException):
            continue
        for node in result["nodes"]:
            if node["id"] == symbol or node["symbol"] == symbol:
                continue
            entry = shared.setdefault(node["id"], {"node": node, "held_by": set()})
            entry["held_by"].add(symbol)

    concentrated = [
        {"node": entry["node"], "held_by": sorted(entry["held_by"]), "holding_count": len(entry["held_by"])}
        for entry in shared.values()
        if len(entry["held_by"]) > 1
    ]
    concentrated.sort(key=lambda e: e["holding_count"], reverse=True)

    return {"symbols": unique_symbols, "shared_exposures": concentrated}
