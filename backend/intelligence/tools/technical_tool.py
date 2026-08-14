"""Deterministic technical-indicator analysis. No LLM call — pure Python math over the same
close-price series the frontend chart already renders (frontend/lib/indicators.ts has the
equivalent TypeScript, used for the interactive chart overlays; this is the server-owned
version used to ground research findings, so the backend never has to trust frontend-computed
values as authoritative)."""

import uuid
from datetime import datetime, timezone

from intelligence.models.evidence import DIRECTLY_OBSERVED_CONFIDENCE, Evidence, EvidenceType
from intelligence.models.findings import AnalyticalFinding

CATEGORY = "technical"


def _new_id() -> str:
    return uuid.uuid4().hex


def sma(closes: list[float | None], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        if any(v is None for v in window):
            continue
        result[i] = sum(window) / period  # type: ignore[arg-type]
    return result


def ema(closes: list[float | None], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(closes)
    k = 2 / (period + 1)
    prev: float | None = None

    for i in range(len(closes)):
        if prev is None:
            if i < period - 1:
                continue
            window = closes[i - period + 1 : i + 1]
            if any(v is None for v in window):
                continue
            prev = sum(window) / period  # type: ignore[arg-type]
            result[i] = prev
            continue
        close = closes[i]
        if close is None:
            prev = None  # gap in data — re-seed from the next available window
            continue
        prev = close * k + prev * (1 - k)
        result[i] = prev
    return result


def bollinger_bands(closes: list[float | None], period: int, std_dev_multiplier: float):
    middles = sma(closes, period)
    result = [{"upper": None, "middle": None, "lower": None} for _ in closes]

    for i in range(period - 1, len(closes)):
        middle = middles[i]
        if middle is None:
            continue
        window = closes[i - period + 1 : i + 1]
        variance = sum((v - middle) ** 2 for v in window) / period  # type: ignore[operator]
        stddev = variance**0.5
        result[i] = {
            "middle": middle,
            "upper": middle + std_dev_multiplier * stddev,
            "lower": middle - std_dev_multiplier * stddev,
        }
    return result


def _rsi_from_averages(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def rsi(closes: list[float | None], period: int) -> list[float | None]:
    """Wilder's smoothing — the standard RSI method."""
    result: list[float | None] = [None] * len(closes)
    avg_gain: float | None = None
    avg_loss: float | None = None
    gain_sum = loss_sum = 0.0
    seeded = 0

    for i in range(1, len(closes)):
        prev, curr = closes[i - 1], closes[i]
        if prev is None or curr is None:
            avg_gain = avg_loss = None
            gain_sum = loss_sum = 0.0
            seeded = 0
            continue

        delta = curr - prev
        gain = delta if delta > 0 else 0.0
        loss = -delta if delta < 0 else 0.0

        if avg_gain is None or avg_loss is None:
            gain_sum += gain
            loss_sum += loss
            seeded += 1
            if seeded == period:
                avg_gain = gain_sum / period
                avg_loss = loss_sum / period
                result[i] = _rsi_from_averages(avg_gain, avg_loss)
            continue

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        result[i] = _rsi_from_averages(avg_gain, avg_loss)

    return result


def macd(closes: list[float | None], fast: int, slow: int, signal: int):
    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = [
        (f - s) if f is not None and s is not None else None for f, s in zip(fast_ema, slow_ema)
    ]
    signal_line = ema(macd_line, signal)
    return [
        {
            "macd": m,
            "signal": s,
            "histogram": (m - s) if m is not None and s is not None else None,
        }
        for m, s in zip(macd_line, signal_line)
    ]


def _last_non_null(values: list) -> object | None:
    for v in reversed(values):
        if v is not None:
            return v
    return None


def analyze(ticker: str, chart_data: list[dict]) -> tuple[list[Evidence], AnalyticalFinding | None]:
    """chart_data: list of {date, open, high, low, close, volume}, oldest first — same shape
    aggregator.gather_context() already returns."""
    closes = [bar.get("close") for bar in chart_data]
    if not closes or all(c is None for c in closes):
        return [], None

    retrieved_at = datetime.now(timezone.utc)
    last_close = _last_non_null(closes)
    last_date_str = chart_data[-1]["date"] if chart_data else None
    try:
        observed_at = (
            datetime.fromisoformat(last_date_str).replace(tzinfo=timezone.utc) if last_date_str else retrieved_at
        )
    except ValueError:
        observed_at = retrieved_at

    sma20 = _last_non_null(sma(closes, 20))
    sma50 = _last_non_null(sma(closes, 50))
    rsi14 = _last_non_null(rsi(closes, 14))
    macd_last = _last_non_null(macd(closes, 12, 26, 9))
    macd_histogram = macd_last["histogram"] if isinstance(macd_last, dict) else None

    computed = {"sma20": sma20, "sma50": sma50, "rsi14": rsi14, "macd_histogram": macd_histogram}

    def make_evidence(name: str, value) -> Evidence | None:
        if value is None:
            return None
        return Evidence(
            id=_new_id(),
            ticker=ticker,
            evidence_type=EvidenceType.TECHNICAL_INDICATOR,
            source="nexus_technical_tool",
            source_url=None,
            observed_at=observed_at,
            retrieved_at=retrieved_at,
            value=value,
            normalized_value=value,
            confidence=DIRECTLY_OBSERVED_CONFIDENCE,  # deterministic math over real prices, not an inference
            metadata={"indicator": name},
        )

    evidence = [e for e in (make_evidence(k, v) for k, v in computed.items()) if e is not None]
    if last_close is not None:
        evidence.append(make_evidence("last_close", last_close))

    # Deterministic direction: majority vote across three independent signals. This is
    # intentionally simple and transparent — not a black-box score — so the reasoning is
    # inspectable from the finding's evidence_ids and risks alone.
    bullish_votes = bearish_votes = 0
    risks: list[str] = []

    if last_close is not None and sma20 is not None and sma50 is not None:
        if last_close > sma20 > sma50:
            bullish_votes += 1
        elif last_close < sma20 < sma50:
            bearish_votes += 1
    else:
        risks.append("Insufficient price history for a full 50-day moving average trend read.")

    if macd_histogram is not None:
        if macd_histogram > 0:
            bullish_votes += 1
        elif macd_histogram < 0:
            bearish_votes += 1

    if rsi14 is not None:
        if rsi14 > 70:
            risks.append(f"RSI(14) at {rsi14:.1f} is in overbought territory (>70).")
            bearish_votes += 1
        elif rsi14 < 30:
            risks.append(f"RSI(14) at {rsi14:.1f} is in oversold territory (<30).")
            bullish_votes += 1
        elif rsi14 > 40 and rsi14 <= 70:
            bullish_votes += 1
        elif rsi14 < 40:
            bearish_votes += 1

    if bullish_votes > bearish_votes:
        direction = "bullish"
    elif bearish_votes > bullish_votes:
        direction = "bearish"
    else:
        direction = "neutral"

    total_votes = bullish_votes + bearish_votes
    agreement = max(bullish_votes, bearish_votes) / total_votes if total_votes else 0.0
    confidence = round(0.5 + 0.3 * agreement, 2)  # 0.5 (no signal) .. 0.8 (full agreement)

    summary_parts = []
    if last_close is not None:
        summary_parts.append(f"Last close {last_close:.2f}")
    if sma20 is not None and sma50 is not None:
        summary_parts.append(f"SMA20 {sma20:.2f} / SMA50 {sma50:.2f}")
    if rsi14 is not None:
        summary_parts.append(f"RSI(14) {rsi14:.1f}")
    if macd_histogram is not None:
        summary_parts.append(f"MACD histogram {macd_histogram:+.3f}")

    finding = AnalyticalFinding(
        category=CATEGORY,
        summary="; ".join(summary_parts) if summary_parts else "Insufficient data for technical analysis.",
        direction=direction,
        confidence=confidence,
        evidence_ids=[e.id for e in evidence],
        risks=risks,
        metadata={"bullish_votes": bullish_votes, "bearish_votes": bearish_votes},
    )

    return evidence, finding
