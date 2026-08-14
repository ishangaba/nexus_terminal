import json
from datetime import datetime, timezone
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from config import settings
from intelligence.models.evidence import Evidence
from intelligence.models.findings import AnalyticalFinding
from intelligence.models.thesis import ResearchThesis
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
# Opus, not Sonnet: these are the app's highest-stakes synthesis calls (a real buy/sell verdict
# and decisive follow-up answers about it), and the cost delta is negligible at this app's volume.
SIGNAL_MODEL = "claude-opus-5"
SIGNAL_ASK_MODEL = "claude-opus-5"
# Research synthesis reasons over pre-computed findings/evidence rather than raw provider data,
# and isn't a standalone trade verdict — same stakes tier as the brief/ask/graph-insights work.
SYNTHESIS_MODEL = "claude-sonnet-5"

SIGNAL_DISCLAIMER = "Informational synthesis of available data — not registered investment advice."

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


SIGNAL_SYSTEM_PROMPT = (
    "You are a trade-signal engine. You will be given real, current data about a stock: "
    "price action, technical indicators (SMA, RSI, MACD, Bollinger Bands), fundamentals, "
    "recent news headlines with sentiment scores, and recent SEC filings. Synthesize ALL of "
    "this into ONE clear, decisive directional call — bullish or bearish (use neutral only if "
    "the data is genuinely and evenly conflicting, not as a default hedge) — and a concrete "
    "suggested action: buy_call, buy_put, or stay_out. Commit to a real answer. Do not "
    "equivocate, do not present both sides as equally likely when the data actually leans one "
    "way, and do not tell the user to consult a financial advisor or do further research of "
    "their own — giving the call IS your job here, not deferring it. Ground every reasoning "
    "point in the specific data you were given: cite actual indicator values, the direction of "
    "sentiment, or specific filing content — not generic statements that could apply to any "
    "stock. List the concrete risks that could invalidate this specific call. Do not add your "
    "own caveat about this not being financial advice — that is handled separately outside "
    "your output."
)

SIGNAL_TRACK_RECORD_ADDENDUM = (
    "You will also be given your own track record of past signals for this stock, if any exist "
    "— use it to calibrate confidence and direction (e.g., don't default to high confidence on "
    "a bearish call if past bearish calls here were frequently wrong)."
)

SIGNAL_ASK_SYSTEM_PROMPT = (
    "You are the same trade-signal engine that generated the trade call the user is now asking "
    "about. You will be given the original signal (direction, action, confidence, summary, "
    "reasoning, key risks) plus the same underlying data it was based on: price action, "
    "technical indicators, fundamentals, recent news with sentiment scores, and recent SEC "
    "filings. Answer the user's follow-up question directly and decisively, grounded in that "
    "data and the signal you already gave. Do not hedge, do not walk back the call, and do not "
    "tell the user to do their own research or consult a financial advisor — you already made "
    "the call, this is you explaining or refining it. If the question asks what would change "
    "the call, name the specific data point or threshold. Keep the answer under 150 words. Do "
    "not add a caveat about this not being financial advice — that is handled separately "
    "outside your output."
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


class TradeSignal(BaseModel):
    direction: Literal["bullish", "bearish", "neutral"]
    action: Literal["buy_call", "buy_put", "stay_out"]
    confidence: Literal["low", "medium", "high"]
    summary: str
    reasoning: list[str]
    key_risks: list[str]


def generate_trade_signal(
    symbol: str,
    price: dict,
    fundamentals: dict,
    news: list[dict],
    filings: list[dict],
    technical_indicators: dict,
    track_record: dict | None = None,
) -> TradeSignal | None:
    payload = _build_context_payload(symbol, price, fundamentals, news, filings)
    payload["technical_indicators"] = technical_indicators

    # Zero-history case (no track_record, or nothing resolved yet) is left as the original,
    # unmodified prompt/payload shape — this is not an error state, just the common case for a
    # symbol's first-ever signal.
    has_track_record = bool(track_record) and track_record.get("resolved_count", 0) > 0
    system_prompt = SIGNAL_SYSTEM_PROMPT
    if has_track_record:
        payload["track_record"] = track_record
        system_prompt = f"{SIGNAL_SYSTEM_PROMPT}\n\n{SIGNAL_TRACK_RECORD_ADDENDUM}"

    try:
        response = _client.messages.parse(
            model=SIGNAL_MODEL,
            # Generous headroom: on Claude Opus 5, max_tokens caps thinking + output combined
            # (thinking is on by default whenever `thinking` is omitted), so a tight cap risks
            # truncating the JSON mid-string on a symbol with a lot to say — 1200 was tuned for
            # Sonnet 5's shorter adaptive-thinking footprint and wasn't enough headroom here.
            max_tokens=4000,
            output_config={"effort": "medium"},
            system=system_prompt,
            # cache_control caches system+payload together as one prefix — pays off if the same
            # signal is quickly regenerated with unchanged inputs, within the cache TTL.
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": json.dumps(payload), "cache_control": {"type": "ephemeral"}}
                    ],
                }
            ],
            output_format=TradeSignal,
        )
    except anthropic.APIError as exc:
        raise _wrap_anthropic_error(exc) from exc
    except ValidationError as exc:
        # response.parse() raises here (rather than returning None) when the model's output was
        # cut off before max_tokens could close out the JSON. Surface it as a retryable
        # ProviderError instead of a raw 500.
        raise ProviderError(PROVIDER, f"{PROVIDER}: response was cut off before it could be parsed — try again.") from exc
    return response.parsed_output


def answer_signal_question(
    symbol: str,
    signal: dict,
    price: dict,
    fundamentals: dict,
    news: list[dict],
    filings: list[dict],
    technical_indicators: dict,
    question: str,
) -> str:
    payload = _build_context_payload(symbol, price, fundamentals, news, filings)
    payload["technical_indicators"] = technical_indicators
    payload["signal_already_given"] = {
        "direction": signal.get("direction"),
        "action": signal.get("action"),
        "confidence": signal.get("confidence"),
        "summary": signal.get("summary"),
        "reasoning": signal.get("reasoning"),
        "key_risks": signal.get("key_risks"),
    }
    try:
        response = _client.messages.create(
            model=SIGNAL_ASK_MODEL,
            # Same headroom reasoning as generate_trade_signal: thinking + output share this cap.
            max_tokens=1500,
            output_config={"effort": "medium"},
            system=SIGNAL_ASK_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        # Shared block (signal + underlying data) is identical across repeat
                        # follow-up questions about the same signal — cache_control here lets a
                        # second/third question in the same session read from cache instead of
                        # re-paying for the whole context. Only the trailing question varies.
                        {"type": "text", "text": json.dumps(payload), "cache_control": {"type": "ephemeral"}},
                        {"type": "text", "text": f"Question: {question}"},
                    ],
                }
            ],
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


RESEARCH_SYNTHESIS_SYSTEM_PROMPT = (
    "You are a research synthesis engine. You will be given a set of ANALYTICAL FINDINGS — "
    "each already produced by a deterministic tool (technical analysis, news sentiment "
    "aggregation, etc.) — plus the underlying EVIDENCE those findings cite. You are not being "
    "given raw, unanalyzed data: the deterministic work is already done. Your job is to "
    "synthesize these findings into one coherent research thesis. "
    "Every finding in the input was successfully computed and is present for a reason — account "
    "for each one in your synthesis. Before writing your summary, verify you have addressed "
    "every finding category you were given (e.g. if a 'technical' finding is present, your "
    "thesis must reflect it — never state or imply that a category of analysis is missing or "
    "unavailable when a finding for it was actually provided). "
    "Ground every claim you make in the findings and evidence you were given — never invent a "
    "fact, a number, or a data point that isn't present in the input. When a finding is a "
    "genuine observation (a computed indicator value, a filing that exists), treat it as fact. "
    "When a finding reflects an interpretation (a sentiment score, a directional read on mixed "
    "signals), treat it as an inference and weigh it accordingly rather than restating it as "
    "certain. If the findings don't cover something relevant (e.g. no fundamentals finding was "
    "provided), do not speculate about it — leave it out rather than filling the gap from "
    "outside knowledge. Where findings disagree with each other, say so explicitly and explain "
    "which one you weighted more heavily and why, rather than silently averaging them. A "
    "finding's own confidence score matters: weigh a high-confidence, risk-free finding more "
    "heavily than a low-confidence one, and reflect that in your stance rather than treating all "
    "findings as equally decisive. Every bullish_factor, bearish_factor, catalyst, risk, and "
    "invalidation_condition should trace back to something in the given findings — do not add "
    "generic boilerplate that could apply to any stock."
)

RESEARCH_QUERY_ADDENDUM = (
    "The user asked a specific question, given below as 'user_question'. Your executive_summary "
    "must directly and specifically answer that question first, before any broader context — "
    "do not just restate a generic thesis and leave the reader to infer the answer. If the given "
    "findings don't contain enough information to fully answer it, say so explicitly rather than "
    "filling the gap from outside knowledge."
)


class ResearchThesisDraft(BaseModel):
    """What Claude actually produces. `ticker`, `evidence_ids`, and `generated_at` on the final
    ResearchThesis are set in Python from data we already have authoritatively — never trusting
    the model for identifiers or timestamps it didn't generate."""

    stance: Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]
    confidence: float
    executive_summary: str
    bullish_factors: list[str]
    bearish_factors: list[str]
    catalysts: list[str]
    key_risks: list[str]
    invalidation_conditions: list[str]


def _serialize_findings(findings: list[AnalyticalFinding]) -> list[dict]:
    return [f.model_dump() for f in findings]


def _serialize_evidence_summary(evidence: list[Evidence]) -> list[dict]:
    return [
        {
            "id": e.id,
            "type": e.evidence_type.value,
            "source": e.source,
            "confidence": e.confidence,
            "value": e.normalized_value if e.normalized_value is not None else e.value,
        }
        for e in evidence
    ]


def synthesize_research(
    ticker: str,
    findings: list[AnalyticalFinding],
    evidence: list[Evidence],
    question: str | None = None,
) -> ResearchThesis:
    payload = {
        "ticker": ticker,
        "findings": _serialize_findings(findings),
        "evidence": _serialize_evidence_summary(evidence),
    }
    system_prompt = RESEARCH_SYNTHESIS_SYSTEM_PROMPT
    if question:
        payload["user_question"] = question
        system_prompt = f"{RESEARCH_SYNTHESIS_SYSTEM_PROMPT}\n\n{RESEARCH_QUERY_ADDENDUM}"

    try:
        response = _client.messages.parse(
            model=SYNTHESIS_MODEL,
            max_tokens=2000,
            output_config={"effort": "medium"},
            system=system_prompt,
            messages=[{"role": "user", "content": json.dumps(payload)}],
            output_format=ResearchThesisDraft,
        )
    except anthropic.APIError as exc:
        raise _wrap_anthropic_error(exc) from exc
    except ValidationError as exc:
        raise ProviderError(PROVIDER, f"{PROVIDER}: response was cut off before it could be parsed — try again.") from exc

    draft = response.parsed_output
    return ResearchThesis(
        ticker=ticker,
        stance=draft.stance,
        confidence=draft.confidence,
        executive_summary=draft.executive_summary,
        bullish_factors=draft.bullish_factors,
        bearish_factors=draft.bearish_factors,
        catalysts=draft.catalysts,
        key_risks=draft.key_risks,
        invalidation_conditions=draft.invalidation_conditions,
        evidence_ids=[e.id for e in evidence],
        generated_at=datetime.now(timezone.utc),
    )


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
