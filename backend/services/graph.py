import httpx

from config import settings


class GraphUnavailableError(Exception):
    pass


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


async def link_subsidiary(parent_symbol: str, subsidiary_name: str) -> None:
    await run_cypher(
        """
        MERGE (parent:Company {symbol: $parent_symbol})
        MERGE (sub:Company {name: $sub_name})
        ON CREATE SET sub.symbol = ''
        MERGE (sub)-[:SUBSIDIARY_OF]->(parent)
        """,
        {"parent_symbol": parent_symbol, "sub_name": subsidiary_name},
    )


async def link_contract(company_symbol: str, gov_entity_name: str, amount: float | None, date: str | None) -> None:
    await run_cypher(
        """
        MERGE (c:Company {symbol: $symbol})
        MERGE (g:GovEntity {name: $gov_name})
        MERGE (c)-[r:HAS_CONTRACT]->(g)
        SET r.amount = $amount, r.date = $date
        """,
        {"symbol": company_symbol, "gov_name": gov_entity_name, "amount": amount, "date": date},
    )


VALID_NEWS_RELATIONSHIPS = {"SUPPLIES_TO", "COMPETES_WITH", "PARTNERS_WITH"}


async def link_news_relationship(from_symbol: str, to_symbol: str, relationship: str, evidence: str) -> None:
    if relationship not in VALID_NEWS_RELATIONSHIPS:
        return
    await run_cypher(
        f"""
        MERGE (a:Company {{symbol: $from_symbol}})
        MERGE (b:Company {{symbol: $to_symbol}})
        MERGE (a)-[r:{relationship}]->(b)
        SET r.evidence = $evidence
        """,
        {"from_symbol": from_symbol, "to_symbol": to_symbol, "evidence": evidence},
    )


async def get_company_subgraph(symbol: str) -> dict:
    """Return the primary company plus everything 1 hop away, as nodes + edges for visualization."""
    rows = await run_cypher(
        """
        MATCH (c:Company {symbol: $symbol})
        OPTIONAL MATCH (c)-[r]-(n)
        RETURN c, r, n
        """,
        {"symbol": symbol},
    )

    nodes: dict[str, dict] = {}
    rid_to_id: dict[str, str] = {}
    edges: list[dict] = []
    seen_edges: set[str] = set()

    def add_node(entity: dict) -> str:
        node_id = entity.get("symbol") or entity.get("name") or entity["@rid"]
        rid_to_id[entity["@rid"]] = node_id
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": entity.get("name") or entity.get("symbol") or node_id,
                "type": entity.get("@type", "Unknown"),
                "symbol": entity.get("symbol"),
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
                }
            )

    return {"nodes": list(nodes.values()), "edges": edges}
