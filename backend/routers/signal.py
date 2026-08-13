import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db.models import (
    create_trade_signal,
    get_symbol_track_record,
    get_trade_signal,
    get_trade_signals_for_symbol,
    set_signal_decision,
    set_signal_user_outcome,
)
from services import claude_analyst
from services.errors import ProviderError

router = APIRouter(prefix="/api/v1")


class SignalRequest(BaseModel):
    price: dict
    fundamentals: dict
    news: list[dict]
    filings: list[dict]
    technical_indicators: dict


class SignalDecisionRequest(BaseModel):
    decision: Literal["accepted", "rejected"]


class SignalOutcomeRequest(BaseModel):
    outcome: Literal["correct", "incorrect", "mixed"]
    notes: str | None = None


class SignalAskRequest(BaseModel):
    price: dict
    fundamentals: dict
    news: list[dict]
    filings: list[dict]
    technical_indicators: dict
    question: str


@router.post("/ticker/{symbol}/signal")
async def generate_ticker_signal(symbol: str, body: SignalRequest):
    symbol = symbol.upper()
    track_record = get_symbol_track_record(symbol)
    try:
        signal = await asyncio.to_thread(
            claude_analyst.generate_trade_signal,
            symbol,
            body.price,
            body.fundamentals,
            body.news,
            body.filings,
            body.technical_indicators,
            track_record,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    if signal is None:
        raise HTTPException(status_code=502, detail="Anthropic: could not generate a structured trade signal.")

    signal_id = create_trade_signal(
        symbol=symbol,
        direction=signal.direction,
        action=signal.action,
        confidence=signal.confidence,
        summary=signal.summary,
        reasoning=signal.reasoning,
        key_risks=signal.key_risks,
        price_at_signal=body.price.get("last"),
    )

    return {
        "id": signal_id,
        "symbol": symbol,
        **signal.model_dump(),
        "note": claude_analyst.SIGNAL_DISCLAIMER,
        "user_decision": None,
        "user_outcome": None,
        "auto_outcome": None,
    }


def _require_signal(symbol: str, signal_id: int) -> dict:
    row = get_trade_signal(signal_id)
    if row is None or row["symbol"] != symbol.upper():
        raise HTTPException(status_code=404, detail="Trade signal not found")
    return row


@router.post("/ticker/{symbol}/signal/{signal_id}/decision")
def record_signal_decision(symbol: str, signal_id: int, body: SignalDecisionRequest):
    _require_signal(symbol, signal_id)
    set_signal_decision(signal_id, body.decision)
    return get_trade_signal(signal_id)


@router.post("/ticker/{symbol}/signal/{signal_id}/outcome")
def record_signal_outcome(symbol: str, signal_id: int, body: SignalOutcomeRequest):
    _require_signal(symbol, signal_id)
    set_signal_user_outcome(signal_id, body.outcome, body.notes)
    return get_trade_signal(signal_id)


@router.post("/ticker/{symbol}/signal/{signal_id}/ask")
async def ask_about_signal(symbol: str, signal_id: int, body: SignalAskRequest):
    signal = _require_signal(symbol, signal_id)
    try:
        answer = await asyncio.to_thread(
            claude_analyst.answer_signal_question,
            symbol.upper(),
            signal,
            body.price,
            body.fundamentals,
            body.news,
            body.filings,
            body.technical_indicators,
            body.question,
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    return {"answer": answer}


@router.get("/ticker/{symbol}/signal/history")
def signal_history(symbol: str):
    symbol = symbol.upper()
    return {
        "signals": get_trade_signals_for_symbol(symbol),
        "track_record": get_symbol_track_record(symbol),
    }
