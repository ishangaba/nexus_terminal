"""Adapters from the existing aggregator's dict output into normalized Evidence objects.

Deliberately additive: `aggregator.gather_context()` is untouched. These functions only wrap
its output — they change nothing about how data is fetched or cached.
"""

import uuid
from datetime import datetime, timezone

from intelligence.models.evidence import (
    LLM_DERIVED_CONFIDENCE,
    DIRECTLY_OBSERVED_CONFIDENCE,
    Evidence,
    EvidenceType,
)


def _new_id() -> str:
    return uuid.uuid4().hex


def _parse_observed_at(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return fallback


def price_evidence(ticker: str, price: dict, retrieved_at: datetime) -> Evidence:
    return Evidence(
        id=_new_id(),
        ticker=ticker,
        evidence_type=EvidenceType.PRICE,
        source="finnhub",
        source_url=None,
        observed_at=_parse_observed_at(price.get("timestamp"), retrieved_at),
        retrieved_at=retrieved_at,
        value=price,
        normalized_value=price.get("last"),
        confidence=DIRECTLY_OBSERVED_CONFIDENCE,
    )


def fundamentals_evidence(ticker: str, fundamentals: dict, retrieved_at: datetime) -> Evidence:
    # Alpha Vantage's OVERVIEW response doesn't carry a clean per-field "as of" date in what
    # aggregator.py currently extracts, so observed_at is approximated as retrieved_at. Revisit
    # if a future milestone starts passing through AV's LatestQuarter field.
    return Evidence(
        id=_new_id(),
        ticker=ticker,
        evidence_type=EvidenceType.FUNDAMENTAL,
        source="alpha_vantage",
        source_url=None,
        observed_at=retrieved_at,
        retrieved_at=retrieved_at,
        value=fundamentals,
        normalized_value=None,
        confidence=DIRECTLY_OBSERVED_CONFIDENCE,
    )


def news_and_sentiment_evidence(ticker: str, news: list[dict], retrieved_at: datetime) -> list[Evidence]:
    """One NEWS evidence per headline (confidence 1.0 — the headline objectively exists), plus
    one SENTIMENT evidence per item that has a score (confidence < 1.0 — it's a Claude
    interpretation of the headline, not an observed fact)."""
    evidence: list[Evidence] = []
    for item in news:
        observed_at = _parse_observed_at(item.get("published_at"), retrieved_at)
        news_id = _new_id()
        evidence.append(
            Evidence(
                id=news_id,
                ticker=ticker,
                evidence_type=EvidenceType.NEWS,
                source=item.get("source") or "unknown",
                source_url=item.get("url"),
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                value=item.get("headline"),
                normalized_value=None,
                confidence=DIRECTLY_OBSERVED_CONFIDENCE,
                metadata={"headline": item.get("headline"), "source": item.get("source")},
            )
        )
        if item.get("sentiment_score") is not None:
            evidence.append(
                Evidence(
                    id=_new_id(),
                    ticker=ticker,
                    evidence_type=EvidenceType.SENTIMENT,
                    source="claude",
                    source_url=item.get("url"),
                    observed_at=observed_at,
                    retrieved_at=retrieved_at,
                    value=item["sentiment_score"],
                    normalized_value=item["sentiment_score"],
                    confidence=LLM_DERIVED_CONFIDENCE,
                    metadata={"headline": item.get("headline"), "related_news_evidence_id": news_id},
                )
            )
    return evidence


def filings_evidence(ticker: str, filings: list[dict], retrieved_at: datetime) -> list[Evidence]:
    evidence = []
    for filing in filings:
        observed_at = retrieved_at
        filed_date = filing.get("filed_date")
        if filed_date:
            try:
                observed_at = datetime.fromisoformat(filed_date).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        evidence.append(
            Evidence(
                id=_new_id(),
                ticker=ticker,
                evidence_type=EvidenceType.SEC_FILING,
                source="sec_edgar",
                source_url=filing.get("url"),
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                value=filing,
                normalized_value=filing.get("form"),
                confidence=DIRECTLY_OBSERVED_CONFIDENCE,
                metadata={"form": filing.get("form")},
            )
        )
    return evidence


def evidence_from_context(context: dict) -> list[Evidence]:
    """Build PRICE/FUNDAMENTAL/SEC_FILING evidence from one aggregator.gather_context() result.

    Deliberately excludes NEWS/SENTIMENT and TECHNICAL_INDICATOR — those evidence types each
    have exactly one producer (news_tool.py and technical_tool.py respectively) so the same
    articles or indicator values never get wrapped into Evidence twice with different IDs.
    """
    ticker = context["symbol"]
    retrieved_at = datetime.now(timezone.utc)

    return [
        price_evidence(ticker, context["price"], retrieved_at),
        fundamentals_evidence(ticker, context["fundamentals"], retrieved_at),
        *filings_evidence(ticker, context.get("filings", []), retrieved_at),
    ]
