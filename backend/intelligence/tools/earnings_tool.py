"""Deterministic analysis over three Finnhub endpoints verified free-tier during resource
planning: EPS surprises, insider (Form 4) transactions, and analyst recommendation trends. No
LLM call. Each sub-analysis is independent, so it returns up to three separate findings rather
than forcing unrelated signals into one — Claude synthesis weighs each on its own confidence.
"""

import uuid
from datetime import date, datetime, timezone

from intelligence.models.evidence import DIRECTLY_OBSERVED_CONFIDENCE, Evidence, EvidenceType
from intelligence.models.findings import AnalyticalFinding

MAX_INSIDER_TRANSACTIONS = 10


def _new_id() -> str:
    return uuid.uuid4().hex


def _observed_at(date_str: str | None, fallback: datetime) -> datetime:
    if not date_str:
        return fallback
    try:
        parsed = date.fromisoformat(date_str)
        return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc)
    except ValueError:
        return fallback


def _earnings_finding(ticker: str, surprises: list[dict], retrieved_at: datetime) -> tuple[list[Evidence], AnalyticalFinding | None]:
    if not surprises:
        return [], None

    # Sort defensively by period descending rather than trusting API response order.
    ordered = sorted(surprises, key=lambda s: s.get("period") or "", reverse=True)
    evidence = []
    for s in ordered[:4]:
        evidence.append(
            Evidence(
                id=_new_id(),
                ticker=ticker,
                evidence_type=EvidenceType.EARNINGS,
                source="finnhub",
                source_url=None,
                observed_at=_observed_at(s.get("period"), retrieved_at),
                retrieved_at=retrieved_at,
                value=s,
                normalized_value=s.get("surprisePercent"),
                confidence=DIRECTLY_OBSERVED_CONFIDENCE,
                metadata={"period": s.get("period"), "quarter": s.get("quarter"), "year": s.get("year")},
            )
        )

    latest = ordered[0]
    surprise_pct = latest.get("surprisePercent")
    if surprise_pct is None:
        return evidence, None

    if surprise_pct > 2:
        direction = "bullish"
    elif surprise_pct < -2:
        direction = "bearish"
    else:
        direction = "neutral"
    confidence = round(0.5 + min(abs(surprise_pct) / 20, 0.3), 2)

    finding = AnalyticalFinding(
        category="earnings",
        summary=(
            f"Most recent quarter ({latest.get('period')}): actual {latest.get('actual')} vs "
            f"estimate {latest.get('estimate')} ({surprise_pct:+.2f}% surprise)"
        ),
        direction=direction,
        confidence=confidence,
        evidence_ids=[e.id for e in evidence],
        risks=[],
        metadata={"latest_surprise_pct": surprise_pct},
    )
    return evidence, finding


def _insider_finding(ticker: str, transactions: list[dict], retrieved_at: datetime) -> tuple[list[Evidence], AnalyticalFinding | None]:
    if not transactions:
        return [], None

    ordered = sorted(transactions, key=lambda t: t.get("transactionDate") or "", reverse=True)[:MAX_INSIDER_TRANSACTIONS]
    evidence = []
    net_change = 0
    for t in ordered:
        change = t.get("change") or 0
        net_change += change
        evidence.append(
            Evidence(
                id=_new_id(),
                ticker=ticker,
                evidence_type=EvidenceType.INSIDER_TRANSACTION,
                source="finnhub",
                source_url=None,
                observed_at=_observed_at(t.get("transactionDate"), retrieved_at),
                retrieved_at=retrieved_at,
                value=t,
                normalized_value=change,
                confidence=DIRECTLY_OBSERVED_CONFIDENCE,
                metadata={"name": t.get("name"), "transaction_code": t.get("transactionCode")},
            )
        )

    if net_change > 0:
        direction = "bullish"
    elif net_change < 0:
        direction = "bearish"
    else:
        direction = "neutral"

    finding = AnalyticalFinding(
        category="insider_activity",
        summary=(
            f"Net insider share change across {len(ordered)} recent Form 4 filing(s): "
            f"{net_change:+,d} shares"
        ),
        direction=direction,
        confidence=0.4,  # deliberately modest — see risk note
        evidence_ids=[e.id for e in evidence],
        risks=[
            "Aggregates all Form 4 transaction types (open-market buys/sells, option "
            "exercises, gifts) without distinguishing intent — a rough directional signal, "
            "not a precise one."
        ],
        metadata={"net_share_change": net_change},
    )
    return evidence, finding


def _analyst_finding(ticker: str, trends: list[dict], retrieved_at: datetime) -> tuple[list[Evidence], AnalyticalFinding | None]:
    if not trends:
        return [], None

    ordered = sorted(trends, key=lambda t: t.get("period") or "", reverse=True)
    latest = ordered[0]
    evidence = [
        Evidence(
            id=_new_id(),
            ticker=ticker,
            evidence_type=EvidenceType.ANALYST_ESTIMATE,
            source="finnhub",
            source_url=None,
            observed_at=_observed_at(latest.get("period"), retrieved_at),
            retrieved_at=retrieved_at,
            value=latest,
            normalized_value=None,
            confidence=DIRECTLY_OBSERVED_CONFIDENCE,
            metadata={"period": latest.get("period")},
        )
    ]

    strong_buy, buy = latest.get("strongBuy", 0), latest.get("buy", 0)
    hold = latest.get("hold", 0)
    sell, strong_sell = latest.get("sell", 0), latest.get("strongSell", 0)
    total = strong_buy + buy + hold + sell + strong_sell
    if total == 0:
        return evidence, None

    score = (2 * strong_buy + buy - sell - 2 * strong_sell) / total  # roughly in [-2, 2]
    if score > 0.3:
        direction = "bullish"
    elif score < -0.3:
        direction = "bearish"
    else:
        direction = "neutral"
    confidence = round(0.5 + min(abs(score) / 4, 0.3), 2)

    finding = AnalyticalFinding(
        category="analyst_sentiment",
        summary=(
            f"Analyst recommendations for {latest.get('period')}: {strong_buy} strong buy, "
            f"{buy} buy, {hold} hold, {sell} sell, {strong_sell} strong sell ({total} total)"
        ),
        direction=direction,
        confidence=confidence,
        evidence_ids=[e.id for e in evidence],
        risks=[],
        metadata={"score": round(score, 3), "total_analysts": total},
    )
    return evidence, finding


def analyze(
    ticker: str, earnings_surprises: list[dict], insider_transactions: list[dict], recommendation_trends: list[dict]
) -> tuple[list[Evidence], list[AnalyticalFinding]]:
    retrieved_at = datetime.now(timezone.utc)
    all_evidence: list[Evidence] = []
    all_findings: list[AnalyticalFinding] = []

    for evidence, finding in (
        _earnings_finding(ticker, earnings_surprises, retrieved_at),
        _insider_finding(ticker, insider_transactions, retrieved_at),
        _analyst_finding(ticker, recommendation_trends, retrieved_at),
    ):
        all_evidence.extend(evidence)
        if finding is not None:
            all_findings.append(finding)

    return all_evidence, all_findings
