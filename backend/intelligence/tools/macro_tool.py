"""Deterministic macro-backdrop context from FRED. No LLM call.

Deliberately always reports direction="neutral": CPI/unemployment/Fed-funds-rate data is real,
current, and directly observed, but whether e.g. a rate hike is bullish or bearish for *this
specific ticker* depends on sector/business-model context this tool doesn't have — that
judgment belongs in Claude synthesis, which sees this finding alongside the company-specific
ones. Faking a directional call here would be exactly the kind of unsupported inference the
whole evidence-grounded design is meant to prevent.
"""

import uuid
from datetime import datetime, timezone

from intelligence.models.evidence import DIRECTLY_OBSERVED_CONFIDENCE, Evidence, EvidenceType
from intelligence.models.findings import AnalyticalFinding
from services.fred import KEY_SERIES

CATEGORY = "macro"


def _new_id() -> str:
    return uuid.uuid4().hex


def analyze(ticker: str, macro_observations: dict[str, dict]) -> tuple[list[Evidence], AnalyticalFinding | None]:
    """macro_observations: series_id -> latest FRED observation dict ({"date", "value", ...})."""
    retrieved_at = datetime.now(timezone.utc)
    evidence = []
    summary_parts = []

    for series_id, label in KEY_SERIES.items():
        obs = macro_observations.get(series_id)
        if not obs or obs.get("value") in (None, "."):  # FRED uses "." for missing values
            continue
        try:
            value = float(obs["value"])
        except (TypeError, ValueError):
            continue

        observed_at = retrieved_at
        if obs.get("date"):
            try:
                y, m, d = (int(p) for p in obs["date"].split("-"))
                observed_at = datetime(y, m, d, tzinfo=timezone.utc)
            except ValueError:
                pass

        evidence.append(
            Evidence(
                id=_new_id(),
                ticker=ticker,
                evidence_type=EvidenceType.MACRO_EVENT,
                source="fred",
                source_url=f"https://fred.stlouisfed.org/series/{series_id}",
                observed_at=observed_at,
                retrieved_at=retrieved_at,
                value=obs,
                normalized_value=value,
                confidence=DIRECTLY_OBSERVED_CONFIDENCE,
                metadata={"series_id": series_id, "label": label},
            )
        )
        summary_parts.append(f"{label}: {value:g} ({obs.get('date')})")

    if not evidence:
        return [], None

    finding = AnalyticalFinding(
        category=CATEGORY,
        summary="; ".join(summary_parts),
        direction="neutral",
        confidence=0.5,
        evidence_ids=[e.id for e in evidence],
        risks=[],
        metadata={"note": "Macro backdrop is descriptive, not a directional call on this ticker."},
    )
    return evidence, finding
