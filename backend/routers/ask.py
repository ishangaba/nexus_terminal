import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services import claude_analyst
from services.aggregator import gather_context

router = APIRouter(prefix="/api/v1")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@router.post("/ask/{symbol}")
async def ask_about_ticker(symbol: str, body: AskRequest):
    try:
        context = await gather_context(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upstream data error: {exc}") from exc

    answer = await asyncio.to_thread(
        claude_analyst.answer_question,
        context["symbol"],
        context["price"],
        context["fundamentals"],
        context["news"],
        context["filings"],
        body.question,
    )

    return {"symbol": context["symbol"], "question": body.question, "answer": answer}
