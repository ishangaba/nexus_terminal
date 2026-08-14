"""Deterministic SEC filing analysis. No LLM call, no new evidence, no new provider fetch —
reasons over the SEC_FILING evidence evidence_adapters.py already produced from
aggregator.gather_context()'s filings list.

Scope note: this flags filing *type and recency* (e.g. "an 8-K was filed 3 days ago" — a
material event disclosure requirement under SEC rules, so its mere presence is a real signal
worth surfacing). It does not read filing *content* to determine whether the news inside is
good or bad — that's a genuine semantic-interpretation task, appropriately deferred to Claude
synthesis rather than faked here with a coin-flip direction.
"""

from datetime import date

from intelligence.models.evidence import Evidence, EvidenceType
from intelligence.models.findings import AnalyticalFinding

CATEGORY = "sec_filings"
RECENT_8K_WINDOW_DAYS = 14

FORM_DESCRIPTIONS = {
    "10-K": "annual report",
    "10-Q": "quarterly report",
    "8-K": "material event disclosure",
    "4": "insider transaction (Form 4)",
}


def analyze(ticker: str, filings: list[dict], evidence: list[Evidence]) -> AnalyticalFinding | None:
    if not filings:
        return None

    evidence_ids = [e.id for e in evidence if e.evidence_type == EvidenceType.SEC_FILING]
    if not evidence_ids:
        return None

    counts: dict[str, int] = {}
    recent_8k = None
    today = date.today()

    for filing in filings:
        form = filing.get("form")
        counts[form] = counts.get(form, 0) + 1
        if form == "8-K" and filing.get("filed_date"):
            try:
                filed = date.fromisoformat(filing["filed_date"])
                if (today - filed).days <= RECENT_8K_WINDOW_DAYS and (
                    recent_8k is None or filed > date.fromisoformat(recent_8k["filed_date"])
                ):
                    recent_8k = filing
            except ValueError:
                pass

    summary_parts = [f"{n} {FORM_DESCRIPTIONS.get(form, form)}" for form, n in counts.items()]
    risks = []
    if recent_8k is not None:
        risks.append(
            f"An 8-K (material event disclosure) was filed {recent_8k['filed_date']} — worth "
            "reviewing directly, as its content isn't analyzed here."
        )

    return AnalyticalFinding(
        category=CATEGORY,
        summary=f"{len(filings)} recent SEC filing(s): " + ", ".join(summary_parts),
        direction="neutral",  # filing existence isn't directional without reading content
        confidence=0.5 if recent_8k is not None else 0.3,
        evidence_ids=evidence_ids,
        risks=risks,
        metadata={"filing_counts": counts, "recent_8k_filed": recent_8k.get("filed_date") if recent_8k else None},
    )
