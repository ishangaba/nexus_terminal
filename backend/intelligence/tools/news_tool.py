"""Deterministic news aggregation: dedup + recency-weighted sentiment. No new LLM call — reuses
the per-headline sentiment scores already computed by claude_analyst.score_sentiment() during
aggregation. Semantic clustering (grouping multiple articles about the same underlying event) is
deliberately deferred — that's a genuine semantic task, not a fit for this deterministic pass;
see docs/architecture/roadmap.md Milestone 2+."""

from datetime import datetime, timezone

from intelligence.evidence_adapters import news_and_sentiment_evidence
from intelligence.models.evidence import Evidence, EvidenceType
from intelligence.models.findings import AnalyticalFinding

CATEGORY = "news_sentiment"
RECENCY_HALF_LIFE_DAYS = 3.0
BULLISH_THRESHOLD = 0.1
BEARISH_THRESHOLD = -0.1


def _dedupe(news: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped = []
    for item in news:
        headline = (item.get("headline") or "").strip().lower()
        if not headline or headline in seen:
            continue
        seen.add(headline)
        deduped.append(item)
    return deduped


def _recency_weight(published_at: str | None, now: datetime) -> float:
    if not published_at:
        return 0.5  # unknown recency — don't let it dominate, but don't discard it either
    try:
        observed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.5
    age_days = max(0.0, (now - observed).total_seconds() / 86400)
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)


def analyze(ticker: str, news: list[dict]) -> tuple[list[Evidence], AnalyticalFinding | None]:
    deduped = _dedupe(news)
    if not deduped:
        return [], None

    now = datetime.now(timezone.utc)
    evidence = news_and_sentiment_evidence(ticker, deduped, now)

    scored = [item for item in deduped if item.get("sentiment_score") is not None]
    weighted_sum = 0.0
    weight_total = 0.0
    for item in scored:
        w = _recency_weight(item.get("published_at"), now)
        weighted_sum += item["sentiment_score"] * w
        weight_total += w

    weighted_avg = weighted_sum / weight_total if weight_total > 0 else 0.0

    if weighted_avg > BULLISH_THRESHOLD:
        direction = "bullish"
    elif weighted_avg < BEARISH_THRESHOLD:
        direction = "bearish"
    else:
        direction = "neutral"

    # Confidence grows with both sample size and how far the weighted average sits from
    # neutral — a single strongly-worded headline shouldn't carry the same weight as a
    # consistent multi-article signal.
    sample_component = min(len(scored) / 8, 1.0)  # saturates around 8 scored articles
    strength_component = min(abs(weighted_avg), 1.0)
    confidence = round(0.5 + 0.3 * sample_component * strength_component, 2) if scored else 0.5

    sentiment_evidence_ids = [e.id for e in evidence if e.evidence_type == EvidenceType.SENTIMENT]
    news_evidence_ids = [e.id for e in evidence if e.evidence_type == EvidenceType.NEWS]

    risks = []
    if len(scored) < 3:
        risks.append(f"Only {len(scored)} scored headline(s) — sentiment read has a small sample.")

    finding = AnalyticalFinding(
        category=CATEGORY,
        summary=(
            f"{len(deduped)} recent headline(s), recency-weighted avg sentiment "
            f"{weighted_avg:+.2f} ({len(scored)} scored)"
        ),
        direction=direction,
        confidence=confidence,
        evidence_ids=news_evidence_ids + sentiment_evidence_ids,
        risks=risks,
        metadata={"weighted_avg_sentiment": round(weighted_avg, 3), "article_count": len(deduped)},
    )

    return evidence, finding
