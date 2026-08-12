import json
from typing import Literal

import anthropic
from pydantic import BaseModel

from config import settings
from services.errors import ProviderError

PROVIDER = "Anthropic"

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def reload_client() -> None:
    """Recreate the Anthropic client after the API key changes at runtime (e.g. via Settings)."""
    global _client
    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _wrap_anthropic_error(exc: Exception) -> ProviderError:
    if isinstance(exc, anthropic.AuthenticationError):
        return ProviderError(PROVIDER, f"{PROVIDER}: invalid or missing API key — check Settings.")
    if isinstance(exc, anthropic.RateLimitError):
        return ProviderError(PROVIDER, f"{PROVIDER}: rate limit reached — try again shortly.")
    if isinstance(exc, anthropic.APIConnectionError):
        return ProviderError(PROVIDER, f"{PROVIDER} is unreachable right now.")
    if isinstance(exc, anthropic.APIStatusError):
        return ProviderError(PROVIDER, f"{PROVIDER}: request failed (HTTP {exc.status_code}).")
    return ProviderError(PROVIDER, f"{PROVIDER}: unexpected error.")

BRIEF_MODEL = "claude-sonnet-5"
ASK_MODEL = "claude-sonnet-5"
SENTIMENT_MODEL = "claude-haiku-4-5"
EXTRACTION_MODEL = "claude-haiku-4-5"

BRIEF_SYSTEM_PROMPT = (
    "You are a financial analyst assistant. You will be given real, current data "
    "about a stock: price action, fundamentals, recent news headlines with "
    "sentiment scores, and recent SEC filings. Write a single tight paragraph (max 120 words) "
    "summarizing what's happening with this stock right now and why. Ground every claim in "
    "the provided data — do not invent facts, analyst targets, or news you "
    "weren't given. If the data is thin, say so briefly rather than filling "
    "gaps with speculation. End with a neutral one-line risk note, not a buy/sell "
    "recommendation. Never give financial advice."
)

SENTIMENT_SYSTEM_PROMPT = (
    "You score financial news headlines for sentiment. Given a headline, respond "
    "with ONLY a number between -1.0 (very negative for the company) and 1.0 "
    "(very positive), with 0.0 being neutral. No words, no explanation — just the number."
)

ASK_SYSTEM_PROMPT = (
    "You are a financial analyst assistant answering a user's question about a specific "
    "stock. You are given real, current data: price action, fundamentals, recent news with "
    "sentiment scores, recent SEC filings (10-K/10-Q/8-K/Form 4 with links), and — when "
    "available — a company relationship graph (subsidiaries from SEC filings, federal "
    "contracts from USASpending.gov, and supplier/competitor/partner relationships inferred "
    "from news). Answer the question using ONLY this data. If the data doesn't contain enough "
    "information to answer, say so plainly rather than speculating or using outside knowledge. "
    "Cite specific figures, filings, or graph relationships where relevant. Keep the answer "
    "under 150 words. Never give financial advice or price predictions."
)

GRAPH_INSIGHTS_SYSTEM_PROMPT = (
    "You are a financial analyst assistant. You will be given a company's relationship graph: "
    "its subsidiaries (from SEC filings), federal government contracts (from USASpending.gov), "
    "and supplier/competitor/partner relationships inferred from recent news. Write a single "
    "tight paragraph (max 90 words) highlighting what's analytically interesting in this "
    "structure — e.g. notable geographic concentration of subsidiaries, meaningful government "
    "contract exposure, or a competitive/supply relationship worth knowing about. Ground every "
    "claim in the provided data only. If the graph is sparse or unremarkable, say so briefly "
    "rather than padding. Never give financial advice."
)


def _summarize_graph(graph: dict, center_symbol: str) -> dict:
    node_by_id = {n["id"]: n for n in graph.get("nodes", [])}
    subsidiaries = []
    federal_contracts = []
    related_companies = []

    for edge in graph.get("edges", []):
        source = node_by_id.get(edge["source"])
        target = node_by_id.get(edge["target"])
        etype = edge["type"]

        if etype == "SUBSIDIARY_OF" and source:
            subsidiaries.append(source["label"])
        elif etype == "HAS_CONTRACT" and target:
            federal_contracts.append({"agency": target["label"], "amount": edge.get("amount"), "date": edge.get("date")})
        elif etype in ("SUPPLIES_TO", "COMPETES_WITH", "PARTNERS_WITH"):
            other = target if source and source["id"] == center_symbol else source
            if other:
                related_companies.append(
                    {"company": other["label"], "relationship": etype, "evidence": edge.get("evidence")}
                )

    return {
        "subsidiaries": subsidiaries,
        "federal_contracts": federal_contracts,
        "related_companies": related_companies,
    }


def _build_context_payload(
    symbol: str, price: dict, fundamentals: dict, news: list[dict], filings: list[dict], graph: dict | None = None
) -> dict:
    payload = {
        "symbol": symbol,
        "price": price,
        "fundamentals": fundamentals,
        "news": [{"headline": n["headline"], "sentiment_score": n["sentiment_score"]} for n in news],
        "recent_sec_filings": filings,
    }
    if graph:
        payload["company_graph"] = _summarize_graph(graph, symbol)
    return payload


def generate_brief(symbol: str, price: dict, fundamentals: dict, news: list[dict], filings: list[dict] | None = None) -> str:
    payload = _build_context_payload(symbol, price, fundamentals, news, filings or [])
    try:
        response = _client.messages.create(
            model=BRIEF_MODEL,
            max_tokens=400,
            thinking={"type": "disabled"},
            output_config={"effort": "low"},
            system=BRIEF_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
        )
    except anthropic.APIError as exc:
        raise _wrap_anthropic_error(exc) from exc
    return next((b.text for b in response.content if b.type == "text"), "")


def answer_question(
    symbol: str,
    price: dict,
    fundamentals: dict,
    news: list[dict],
    filings: list[dict],
    question: str,
    graph: dict | None = None,
) -> str:
    payload = _build_context_payload(symbol, price, fundamentals, news, filings, graph)
    try:
        response = _client.messages.create(
            model=ASK_MODEL,
            max_tokens=350,
            thinking={"type": "disabled"},
            output_config={"effort": "low"},
            system=ASK_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Data: {json.dumps(payload)}\n\nQuestion: {question}"}],
        )
    except anthropic.APIError as exc:
        raise _wrap_anthropic_error(exc) from exc
    return next((b.text for b in response.content if b.type == "text"), "")


def generate_graph_insights(symbol: str, graph: dict) -> str:
    summary = _summarize_graph(graph, symbol)
    if not any(summary.values()):
        return "No notable subsidiary, government contract, or related-company signal found for this ticker yet."

    try:
        response = _client.messages.create(
            model=SENTIMENT_MODEL,
            max_tokens=250,
            system=GRAPH_INSIGHTS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps({"symbol": symbol, "graph_summary": summary})}],
        )
    except anthropic.APIError as exc:
        raise _wrap_anthropic_error(exc) from exc
    return next((b.text for b in response.content if b.type == "text"), "")


class SubsidiaryExtraction(BaseModel):
    subsidiaries: list[str]


def _subsidiary_extraction_prompt(limit: int) -> str:
    return (
        "You will be given the text of an SEC Exhibit 21 filing, which lists a company's "
        "subsidiaries. Extract just the subsidiary company names, exactly as written — no "
        "jurisdictions, no explanatory text. If the text contains no subsidiary list, return "
        f"an empty array. The filing may list far more than needed — return at most {limit}, "
        "prioritizing the ones listed first (typically the most significant)."
    )


def extract_subsidiaries(exhibit_text: str, limit: int = 15) -> list[str]:
    try:
        response = _client.messages.parse(
            model=EXTRACTION_MODEL,
            max_tokens=3000,
            system=_subsidiary_extraction_prompt(limit),
            messages=[{"role": "user", "content": exhibit_text}],
            output_format=SubsidiaryExtraction,
        )
    except Exception:
        return []
    if response.parsed_output is None:
        return []
    return response.parsed_output.subsidiaries[:limit]


class NewsRelationship(BaseModel):
    other_ticker: str | None
    relationship: Literal["SUPPLIES_TO", "COMPETES_WITH", "PARTNERS_WITH"]
    evidence: str


class RelationshipExtraction(BaseModel):
    relationships: list[NewsRelationship]


RELATIONSHIP_EXTRACTION_PROMPT = (
    "You will be given a stock ticker and a list of recent news headlines about it. "
    "Identify any OTHER publicly traded companies mentioned that have a clear "
    "SUPPLIES_TO, COMPETES_WITH, or PARTNERS_WITH relationship with the given ticker, "
    "based only on what the headline states or clearly implies. For each, give the "
    "other company's stock ticker symbol ONLY if you're confident of it — otherwise "
    "omit that relationship entirely (set other_ticker to null and it will be dropped). "
    "Skip vague or unrelated mentions. Most headlines will yield zero relationships — "
    "that's fine, return an empty array rather than guessing."
)


def extract_relationships(symbol: str, headlines: list[str]) -> list[NewsRelationship]:
    if not headlines:
        return []
    payload = {"symbol": symbol, "headlines": headlines}
    try:
        response = _client.messages.parse(
            model=EXTRACTION_MODEL,
            max_tokens=1000,
            system=RELATIONSHIP_EXTRACTION_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}],
            output_format=RelationshipExtraction,
        )
    except Exception:
        return []
    if response.parsed_output is None:
        return []
    return [r for r in response.parsed_output.relationships if r.other_ticker]


def score_sentiment(headline: str) -> float | None:
    try:
        response = _client.messages.create(
            model=SENTIMENT_MODEL,
            max_tokens=10,
            system=SENTIMENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": headline}],
        )
    except anthropic.APIError as exc:
        raise _wrap_anthropic_error(exc) from exc
    text = next((b.text for b in response.content if b.type == "text"), "0")
    try:
        return max(-1.0, min(1.0, float(text.strip())))
    except ValueError:
        return 0.0
