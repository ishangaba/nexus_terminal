from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ResearchThesis(BaseModel):
    ticker: str

    stance: Literal["strong_bullish", "bullish", "neutral", "bearish", "strong_bearish"]

    confidence: float

    executive_summary: str

    bullish_factors: list[str]
    bearish_factors: list[str]

    catalysts: list[str]
    key_risks: list[str]
    invalidation_conditions: list[str]

    evidence_ids: list[str]

    generated_at: datetime
