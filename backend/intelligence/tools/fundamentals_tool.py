"""Deterministic fundamentals analysis. No LLM call, no new evidence, no new provider fetch —
reasons over the FUNDAMENTAL and PRICE evidence evidence_adapters.py already produced from data
aggregator.gather_context() already fetched.

Scope note: today's fundamentals payload is limited to P/E, market cap, EPS, and the 52-week
range (Alpha Vantage OVERVIEW, 5 fields extracted). Margin/growth/leverage analysis needs richer
fields from that same response and isn't wired up yet — see docs/architecture/roadmap.md. This
tool is deliberately honest about that limit rather than inventing a verdict the data can't
support.
"""

from intelligence.models.evidence import Evidence, EvidenceType
from intelligence.models.findings import AnalyticalFinding

CATEGORY = "fundamentals"


def analyze(
    ticker: str, fundamentals: dict, price: dict, evidence: list[Evidence]
) -> AnalyticalFinding | None:
    last = price.get("last")
    week_low = fundamentals.get("52_week_low")
    week_high = fundamentals.get("52_week_high")

    evidence_ids = [
        e.id for e in evidence if e.evidence_type in (EvidenceType.FUNDAMENTAL, EvidenceType.PRICE)
    ]
    if not evidence_ids:
        return None

    facts = []
    pe_ratio = fundamentals.get("pe_ratio")
    if pe_ratio is not None:
        facts.append(f"P/E {pe_ratio:.2f}")
    eps = fundamentals.get("eps")
    if eps is not None:
        facts.append(f"EPS {eps:.2f}")
    market_cap = fundamentals.get("market_cap")
    if market_cap is not None:
        facts.append(f"market cap {market_cap:,.0f}")

    direction = "neutral"
    confidence = 0.4  # deliberately modest — this is a thin data set (see module docstring)
    risks = [
        "Fundamentals data is limited to headline valuation metrics (P/E, EPS, market cap, "
        "52-week range) — no revenue growth, margin, or leverage detail available yet."
    ]

    range_note = None
    if last is not None and week_low is not None and week_high is not None and week_high > week_low:
        pct = (last - week_low) / (week_high - week_low)
        range_note = f"{pct * 100:.0f}% of the way through the 52-week range (${week_low:.2f}–${week_high:.2f})"
        facts.append(range_note)
        if pct >= 0.7:
            direction = "bullish"
            confidence = 0.45
        elif pct <= 0.3:
            direction = "bearish"
            confidence = 0.45

    if not facts:
        return None

    return AnalyticalFinding(
        category=CATEGORY,
        summary="; ".join(facts),
        direction=direction,
        confidence=confidence,
        evidence_ids=evidence_ids,
        risks=risks,
        metadata={"52_week_range_position": range_note},
    )
