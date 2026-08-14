from typing import Literal

from pydantic import BaseModel


class AnalyticalFinding(BaseModel):
    category: str

    summary: str

    direction: Literal["bullish", "bearish", "neutral"]

    confidence: float

    evidence_ids: list[str]

    risks: list[str] = []

    metadata: dict = {}
