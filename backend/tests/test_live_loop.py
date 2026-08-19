"""Tests for the EOD square-off check, fill-price lookup, and position
closing in the live/paper trading loop."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import Settings
from app.models.trade_execution import TradeExecution, TradeMode, TradeStatus
from app.workers.live_loop import _close_position, _fetch_fill_price, _is_past_square_off


@dataclass
class _FakeKite:
    history: list[dict] | None = None
    raises: bool = False

    def order_history(self, order_id):
        if self.raises:
            raise RuntimeError("kite api down")
        return self.history or []


@dataclass
class _FakeClient:
    kite: _FakeKite


def test_before_square_off_time_is_false():
    # 15:30 IST == 10:00 UTC
    as_of = datetime(2026, 8, 12, 9, 59, tzinfo=UTC)
    assert _is_past_square_off(as_of, "15:38") is False


def test_at_square_off_time_is_true():
    # 15:38 IST == 10:08 UTC
    as_of = datetime(2026, 8, 12, 10, 8, tzinfo=UTC)
    assert _is_past_square_off(as_of, "15:38") is True


def test_after_square_off_time_is_true():
    as_of = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    assert _is_past_square_off(as_of, "15:38") is True


def test_next_morning_before_square_off_is_false():
    # 09:15 IST == 03:45 UTC - well before the same day's square-off time.
    as_of = datetime(2026, 8, 13, 3, 45, tzinfo=UTC)
    assert _is_past_square_off(as_of, "15:38") is False


def test_fetch_fill_price_uses_completed_average_price():
    client = _FakeClient(kite=_FakeKite(history=[{"status": "OPEN"}, {"status": "COMPLETE", "average_price": 655.2}]))
    assert _fetch_fill_price(client, "broker-order-1", fallback=650.45) == 655.2


def test_fetch_fill_price_falls_back_when_not_yet_completed():
    client = _FakeClient(kite=_FakeKite(history=[{"status": "OPEN"}]))
    assert _fetch_fill_price(client, "broker-order-1", fallback=650.45) == 650.45


def test_fetch_fill_price_falls_back_on_lookup_failure():
    client = _FakeClient(kite=_FakeKite(raises=True))
    assert _fetch_fill_price(client, "broker-order-1", fallback=650.45) == 650.45


def test_close_position_sets_status_and_pnl():
    position = TradeExecution(
        mode=TradeMode.LIVE,
        status=TradeStatus.OPEN,
        symbol="BANKNIFTY26AUG57500CE",
        option_type="CE",
        quantity=30,
        entry_time=datetime.now(UTC),
        entry_price=650.45,
    )
    _close_position(position, exit_price=700.0, reason="TARGET", settings=Settings())
    assert position.status == TradeStatus.CLOSED
    assert position.exit_price == 700.0
    assert position.exit_reason == "TARGET"
    assert position.pnl == round((700.0 - 650.45) * 30, 2)
    assert position.charges > 0
