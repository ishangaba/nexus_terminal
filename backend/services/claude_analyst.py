import json

import anthropic

from config import settings

_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

BRIEF_MODEL = "claude-sonnet-5"
ASK_MODEL = "claude-sonnet-5"
SENTIMENT_MODEL = "claude-haiku-4-5"

BRIEF_SYSTEM_PROMPT = (
    "You are a financial analyst assistant. You will be given real, current data "
    "about a stock: price action, fundamentals, recent news headlines with "
    "sentiment scores, and recent SEC filings. Write a single tight paragraph (max 120 words) "
    "summarizing what's happening with this stock right now and why. Ground every claim in "
    "the provided data — do not invent facts, analyst targets, or news you "
    "weren't given. If the data is thin, say so briefly rather than filling "
    "gaps with speculation. End with a neutral one-line risk note, not a buy/sell "
    "recommendation. Never give financial advice."
)

SENTIMENT_SYSTEM_PROMPT = (
    "You score financial news headlines for sentiment. Given a headline, respond "
    "with ONLY a number between -1.0 (very negative for the company) and 1.0 "
    "(very positive), with 0.0 being neutral. No words, no explanation — just the number."
)

ASK_SYSTEM_PROMPT = (
    "You are a financial analyst assistant answering a user's question about a specific "
    "stock. You are given real, current data: price action, fundamentals, recent news with "
    "sentiment scores, and recent SEC filings (10-K/10-Q/8-K/Form 4 with links). Answer the "
    "question using ONLY this data. If the data doesn't contain enough information to answer, "
    "say so plainly rather than speculating or using outside knowledge. Cite specific figures "
    "or filings where relevant. Keep the answer under 150 words. Never give financial advice "
    "or price predictions."
)


def _build_context_payload(symbol: str, price: dict, fundamentals: dict, news: list[dict], filings: list[dict]) -> dict:
    return {
        "symbol": symbol,
        "price": price,
        "fundamentals": fundamentals,
        "news": [{"headline": n["headline"], "sentiment_score": n["sentiment_score"]} for n in news],
        "recent_sec_filings": filings,
    }


def generate_brief(symbol: str, price: dict, fundamentals: dict, news: list[dict], filings: list[dict] | None = None) -> str:
    payload = _build_context_payload(symbol, price, fundamentals, news, filings or [])
    response = _client.messages.create(
        model=BRIEF_MODEL,
        max_tokens=400,
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        system=BRIEF_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def answer_question(
    symbol: str, price: dict, fundamentals: dict, news: list[dict], filings: list[dict], question: str
) -> str:
    payload = _build_context_payload(symbol, price, fundamentals, news, filings)
    response = _client.messages.create(
        model=ASK_MODEL,
        max_tokens=350,
        thinking={"type": "disabled"},
        output_config={"effort": "low"},
        system=ASK_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Data: {json.dumps(payload)}\n\nQuestion: {question}"}],
    )
    return next((b.text for b in response.content if b.type == "text"), "")


def score_sentiment(headline: str) -> float:
    response = _client.messages.create(
        model=SENTIMENT_MODEL,
        max_tokens=10,
        system=SENTIMENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": headline}],
    )
    text = next((b.text for b in response.content if b.type == "text"), "0")
    try:
        return max(-1.0, min(1.0, float(text.strip())))
    except ValueError:
        return 0.0
