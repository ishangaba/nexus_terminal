from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class EvidenceType(StrEnum):
    PRICE = "PRICE"
    VOLUME = "VOLUME"
    TECHNICAL_INDICATOR = "TECHNICAL_INDICATOR"
    FUNDAMENTAL = "FUNDAMENTAL"
    EARNINGS = "EARNINGS"
    SEC_FILING = "SEC_FILING"
    NEWS = "NEWS"
    SENTIMENT = "SENTIMENT"
    GOVERNMENT_CONTRACT = "GOVERNMENT_CONTRACT"
    INSIDER_TRANSACTION = "INSIDER_TRANSACTION"
    ANALYST_ESTIMATE = "ANALYST_ESTIMATE"
    MACRO_EVENT = "MACRO_EVENT"
    SUPPLY_CHAIN_RELATIONSHIP = "SUPPLY_CHAIN_RELATIONSHIP"
    COMPETITOR_RELATIONSHIP = "COMPETITOR_RELATIONSHIP"
    # INSTITUTIONAL_HOLDING intentionally omitted — no source wired yet.
    # See docs/architecture/target-state.md §2.


# Confidence convention (not a calibrated score yet — see roadmap.md Milestone 4):
# directly-observed provider data is 1.0; anything Claude-derived (sentiment, inferred
# relationships) is deliberately < 1.0 to mark it as an interpretation, not a fact.
DIRECTLY_OBSERVED_CONFIDENCE = 1.0
LLM_DERIVED_CONFIDENCE = 0.7


class Evidence(BaseModel):
    id: str
    ticker: str
    evidence_type: EvidenceType

    source: str
    source_url: str | None = None

    observed_at: datetime
    retrieved_at: datetime

    value: Any
    normalized_value: Any | None = None

    confidence: float

    metadata: dict = {}
