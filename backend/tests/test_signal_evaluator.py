"""Look-ahead-bias correctness tests for the signal evaluator.

The property under test throughout: a forward return can only ever be derived from a price
dated strictly *after* the signal's `generated_at`. Every test here plants a deliberately wrong
value on-or-before the generation date and asserts it never leaks into the result.
"""

import copy

from intelligence.evaluators import signal_evaluator as ev


def make_signal(generated_at="2024-01-01 00:00:00", price_at_signal=100.0, action="buy_call"):
    return {
        "id": 1,
        "symbol": "TEST",
        "generated_at": generated_at,
        "direction": "bullish" if action == "buy_call" else "bearish",
        "action": action,
        "confidence": "medium",
        "price_at_signal": price_at_signal,
    }


def bar(date, close, high=None, low=None):
    return {
        "date": date,
        "open": close,
        "high": high if high is not None else close,
        "low": low if low is not None else close,
        "close": close,
        "volume": 1000,
    }


def test_horizon_never_uses_a_price_dated_on_or_before_generation():
    signal = make_signal()
    chart = [
        bar("2023-12-30", close=9999),  # planted decoy, well before generation
        bar("2024-01-01", close=8888),  # planted decoy, same day as generation
        bar("2024-01-02", close=110),  # the only legitimate 1d-horizon price
    ]

    result = ev.compute_returns(signal, chart)

    assert result["return_1d"] == 10.0  # (110 - 100) / 100 * 100, using only the 01-02 bar


def test_missing_future_data_leaves_horizon_absent_not_fabricated():
    signal = make_signal()
    chart = [
        bar("2024-01-01", close=100),
        bar("2024-01-02", close=101),  # only 1 day of future data exists
    ]

    result = ev.compute_returns(signal, chart)

    assert "return_1d" in result
    assert "return_5d" not in result
    assert "return_20d" not in result


def test_recomputing_with_identical_data_is_idempotent():
    signal = make_signal()
    chart = [bar("2024-01-01", close=100), bar("2024-01-04", close=97), bar("2024-01-06", close=103)]

    first = ev.compute_returns(signal, chart)
    second = ev.compute_returns(signal, chart)

    assert first == second


def test_compute_returns_never_mutates_the_signal_dict():
    signal = make_signal()
    original = copy.deepcopy(signal)
    chart = [bar("2024-01-01", close=100), bar("2024-01-04", close=90)]

    ev.compute_returns(signal, chart)

    assert signal == original


def test_buy_put_mfe_mae_direction_is_flipped():
    # bearish call: price dropping is favorable (MFE positive), price rising is adverse (MAE negative)
    signal = make_signal(action="buy_put")
    chart = [
        bar("2024-01-01", close=100),
        bar("2024-01-02", close=100, high=100, low=90),  # favorable dip
        bar("2024-01-03", close=100, high=115, low=100),  # adverse spike
    ]

    result = ev.compute_returns(signal, chart)

    assert result["mfe"] == 10.0  # (100 - 90) / 100 * 100
    assert result["mae"] == -15.0  # (100 - 115) / 100 * 100


def test_buy_call_mfe_mae_direction_is_unflipped():
    signal = make_signal(action="buy_call")
    chart = [
        bar("2024-01-01", close=100),
        bar("2024-01-02", close=100, high=112, low=100),  # favorable rally
        bar("2024-01-03", close=100, high=100, low=85),  # adverse drop
    ]

    result = ev.compute_returns(signal, chart)

    assert result["mfe"] == 12.0
    assert result["mae"] == -15.0


def test_benchmark_return_uses_same_horizon_and_ignores_pre_generation_prices():
    signal = make_signal()
    chart = [bar("2024-01-01", close=100), bar("2024-01-06", close=105)]  # 5d horizon
    benchmark_chart = [
        bar("2023-06-01", close=1),  # decoy, irrelevant date
        bar("2024-01-01", close=400),
        bar("2024-01-06", close=420),
    ]

    result = ev.compute_returns(signal, chart, benchmark_chart=benchmark_chart)

    assert result["benchmark_return"] == 5.0  # (420 - 400) / 400 * 100


def test_map_sector_etf_unmapped_sector_returns_none():
    assert ev.map_sector_etf("Some Made Up Sector") is None
    assert ev.map_sector_etf(None) is None
    assert ev.map_sector_etf("Consumer Cyclical") == "XLY"


def test_performance_summary_direction_adjusts_bearish_returns():
    signals = [
        {**make_signal(action="buy_call"), "return_5d": 8.0, "auto_outcome": "correct"},
        {**make_signal(action="buy_put"), "return_5d": -6.0, "auto_outcome": "correct"},
    ]

    summary = ev.performance_summary(signals)

    # buy_call +8 stays +8; buy_put -6 flips to +6 (a correct bearish call profits when price falls)
    assert summary["horizons"]["return_5d"]["avg_directional_return_pct"] == 7.0
    assert summary["win_rate"] == 1.0
