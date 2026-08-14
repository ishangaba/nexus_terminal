"""Correctness tests for the return-backfill DB layer: the whitelist that keeps
update_signal_returns from ever touching a signal's original verdict, and the convergence
behavior of the needing-backfill query."""

from db.models import (
    create_trade_signal,
    get_signals_needing_return_backfill,
    get_trade_signal,
    update_signal_returns,
)


def test_update_signal_returns_only_touches_whitelisted_columns(temp_db):
    signal_id = create_trade_signal(
        symbol="TEST", direction="bullish", action="buy_call", confidence="high",
        summary="s", reasoning=["r"], key_risks=["k"], price_at_signal=100.0,
    )

    # direction/action/confidence/price_at_signal are NOT valid return columns — attempting to
    # smuggle them through must be silently dropped, not applied.
    update_signal_returns(
        signal_id,
        return_1d=5.0,
        direction="bearish",
        action="buy_put",
        price_at_signal=1.0,
    )

    signal = get_trade_signal(signal_id)
    assert signal["return_1d"] == 5.0
    assert signal["direction"] == "bullish"
    assert signal["action"] == "buy_call"
    assert signal["price_at_signal"] == 100.0


def test_needing_backfill_converges_as_columns_fill_in(temp_db):
    signal_id = create_trade_signal(
        symbol="TEST", direction="bullish", action="buy_call", confidence="medium",
        summary="s", reasoning=["r"], key_risks=["k"], price_at_signal=50.0,
    )

    assert any(s["id"] == signal_id for s in get_signals_needing_return_backfill())

    update_signal_returns(
        signal_id,
        return_1d=1.0, return_3d=1.0, return_5d=1.0, return_10d=1.0, return_20d=1.0,
    )

    assert all(s["id"] != signal_id for s in get_signals_needing_return_backfill())


def test_stay_out_signals_never_need_return_backfill(temp_db):
    create_trade_signal(
        symbol="TEST", direction="neutral", action="stay_out", confidence="low",
        summary="s", reasoning=["r"], key_risks=["k"], price_at_signal=50.0,
    )

    assert get_signals_needing_return_backfill() == []


def test_update_signal_returns_is_idempotent(temp_db):
    signal_id = create_trade_signal(
        symbol="TEST", direction="bullish", action="buy_call", confidence="high",
        summary="s", reasoning=["r"], key_risks=["k"], price_at_signal=100.0,
    )

    update_signal_returns(signal_id, return_1d=3.5)
    update_signal_returns(signal_id, return_1d=3.5)  # re-running with the same value is a no-op

    assert get_trade_signal(signal_id)["return_1d"] == 3.5
