"""Tests for the EOD square-off time check in the live paper trading loop."""

from datetime import UTC, datetime

from app.workers.live_loop import _is_past_square_off


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
