"""Forward-return computation for trade signals.

Deterministic, pure price-series arithmetic — no LLM calls, no heuristics. This is the one
module in the app where a subtle bug produces confidently wrong performance numbers, so the
rule is simple and non-negotiable: every price used here must come from a bar dated *after*
`generated_at`. `price_at_signal` (already captured at generation time) is the only allowed
reference to anything on-or-before that date. Nothing here ever mutates a signal's original
direction/confidence/price_at_signal — it only ever fills in new, independent columns.

Horizons are computed incrementally: a 20-day return literally cannot exist until 20 days have
passed, so `compute_returns` returns only whatever is currently available. Re-running it later
with a longer price series fills in more; re-running it with the *same* series is a no-op,
since the arithmetic is a pure function of (signal, chart data).
"""

from datetime import date, datetime, timedelta

HORIZON_DAYS = {
    "return_1d": 1,
    "return_3d": 3,
    "return_5d": 5,
    "return_10d": 10,
    "return_20d": 20,
}
MAX_HORIZON_DAYS = max(HORIZON_DAYS.values())
BENCHMARK_HORIZON = "return_5d"

BENCHMARK_SYMBOL = "SPY"

# Alpha Vantage OVERVIEW `Sector` values, normalized upper-case substring match -> SPDR sector
# ETF. Deliberately small and substring-based (real-world sector strings vary in wording); an
# unmapped sector leaves sector_return null rather than guessing at a proxy.
SECTOR_ETF = {
    "TECHNOLOGY": "XLK",
    "HEALTH": "XLV",
    "FINANCIAL": "XLF",
    "ENERGY": "XLE",
    "CONSUMER CYCLICAL": "XLY",
    "CONSUMER DISCRETIONARY": "XLY",
    "CONSUMER DEFENSIVE": "XLP",
    "CONSUMER STAPLES": "XLP",
    "INDUSTRIAL": "XLI",
    "UTILIT": "XLU",
    "REAL ESTATE": "XLRE",
    "BASIC MATERIALS": "XLB",
    "MATERIALS": "XLB",
    "COMMUNICATION": "XLC",
}


def map_sector_etf(sector: str | None) -> str | None:
    if not sector:
        return None
    normalized = sector.strip().upper()
    for keyword, etf in SECTOR_ETF.items():
        if keyword in normalized:
            return etf
    return None


def _parse_date(value: str) -> date:
    return datetime.fromisoformat(value.split(" ")[0].split("T")[0]).date()


def _index_by_date(chart_data: list[dict]) -> dict[date, dict]:
    return {_parse_date(bar["date"]): bar for bar in chart_data if bar.get("date")}


def _price_at_or_after(by_date: dict[date, dict], target: date, field: str = "close") -> tuple[date, float] | None:
    """First available bar on or after `target` (rolls forward over weekends/holidays).
    Never looks backward, so a horizon is either satisfied by a real post-target price or left
    unresolved — it never silently substitutes an earlier, pre-horizon price."""
    for offset in range(10):
        candidate = target + timedelta(days=offset)
        bar = by_date.get(candidate)
        if bar and bar.get(field) is not None:
            return candidate, bar[field]
    return None


def _pct(base: float, value: float) -> float:
    return round((value - base) / base * 100, 4)


def _relative_return(chart_data: list[dict], generated_date: date) -> float | None:
    by_date = _index_by_date(chart_data)
    baseline = _price_at_or_after(by_date, generated_date)
    horizon = _price_at_or_after(by_date, generated_date + timedelta(days=HORIZON_DAYS[BENCHMARK_HORIZON]))
    if not baseline or not horizon:
        return None
    return _pct(baseline[1], horizon[1])


def compute_returns(
    signal: dict,
    ticker_chart: list[dict],
    benchmark_chart: list[dict] | None = None,
    sector_chart: list[dict] | None = None,
) -> dict:
    """Whatever forward-return fields are currently computable for this signal. Only includes
    keys the data actually supports right now — the caller does a partial update, so omitted
    keys simply stay null until a later run has enough price history to fill them in."""
    generated_date = _parse_date(signal["generated_at"])
    price_at_signal = signal["price_at_signal"]
    direction = signal["action"]  # "buy_call" | "buy_put" — stay_out excluded upstream

    by_date = _index_by_date(ticker_chart)
    results: dict = {}

    for column, days in HORIZON_DAYS.items():
        found = _price_at_or_after(by_date, generated_date + timedelta(days=days))
        if found is not None:
            results[column] = _pct(price_at_signal, found[1])

    window_end = min(date.today(), generated_date + timedelta(days=MAX_HORIZON_DAYS))
    window_bars = [
        bar for day, bar in by_date.items()
        if generated_date < day <= window_end and bar.get("high") is not None and bar.get("low") is not None
    ]
    if window_bars:
        highest = max(bar["high"] for bar in window_bars)
        lowest = min(bar["low"] for bar in window_bars)
        if direction == "buy_call":
            results["mfe"] = _pct(price_at_signal, highest)
            results["mae"] = _pct(price_at_signal, lowest)
        else:  # buy_put — favorable direction is a price decline
            results["mfe"] = round((price_at_signal - lowest) / price_at_signal * 100, 4)
            results["mae"] = round((price_at_signal - highest) / price_at_signal * 100, 4)

    if benchmark_chart:
        bench = _relative_return(benchmark_chart, generated_date)
        if bench is not None:
            results["benchmark_return"] = bench

    if sector_chart:
        sect = _relative_return(sector_chart, generated_date)
        if sect is not None:
            results["sector_return"] = sect

    return results


def resolved_outcome(signal: dict) -> str | None:
    return signal.get("auto_outcome") or signal.get("user_outcome")


def is_correct(outcome: str | None) -> bool | None:
    if outcome == "correct":
        return True
    if outcome == "incorrect":
        return False
    return None  # "mixed" or unresolved — excluded from binary accuracy math


def _directional_return(signal: dict, column: str) -> float | None:
    """Raw price return, sign-adjusted so positive always means the call would have profited."""
    raw = signal.get(column)
    if raw is None:
        return None
    return raw if signal["action"] == "buy_call" else -raw


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    return round(ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2, 4)


def performance_summary(signals: list[dict]) -> dict:
    """Aggregate win rate, directional accuracy, and forward-return stats over directional
    (buy_call/buy_put) signals. Returns are direction-adjusted (positive = the call profited),
    since that's what "performance" means here — raw price return alone doesn't say whether a
    bearish call was right."""
    resolved_pairs = [(s, is_correct(resolved_outcome(s))) for s in signals]
    resolved_pairs = [(s, c) for s, c in resolved_pairs if c is not None]

    def _accuracy(subset: list[tuple[dict, bool]]) -> float | None:
        return round(sum(1 for _, c in subset if c) / len(subset), 4) if subset else None

    bullish = [pair for pair in resolved_pairs if pair[0]["action"] == "buy_call"]
    bearish = [pair for pair in resolved_pairs if pair[0]["action"] == "buy_put"]

    horizon_stats = {}
    for column in HORIZON_DAYS:
        directional = [d for s in signals if (d := _directional_return(s, column)) is not None]
        horizon_stats[column] = {
            "n": len(directional),
            "avg_directional_return_pct": _mean(directional),
            "median_directional_return_pct": _median(directional),
        }

    alpha_values = []
    for s in signals:
        directional_5d = _directional_return(s, "return_5d")
        benchmark = s.get("benchmark_return")
        if directional_5d is not None and benchmark is not None:
            alpha_values.append(round(directional_5d - benchmark, 4))

    return {
        "total_signals": len(signals),
        "resolved_count": len(resolved_pairs),
        "win_rate": _accuracy(resolved_pairs),
        "bullish_accuracy": _accuracy(bullish),
        "bullish_n": len(bullish),
        "bearish_accuracy": _accuracy(bearish),
        "bearish_n": len(bearish),
        "horizons": horizon_stats,
        "avg_alpha_vs_benchmark_5d_pct": _mean(alpha_values),
        "alpha_sample_size": len(alpha_values),
    }
