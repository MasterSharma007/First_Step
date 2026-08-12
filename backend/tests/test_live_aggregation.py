"""Tests for the live tick-to-bar bucketing math (pure, no DB needed)."""

from datetime import UTC, datetime

from app.workers.live_aggregation import _bucket_start


def test_bucket_start_floors_to_5_minute_boundary():
    as_of = datetime(2026, 8, 12, 7, 53, 42, tzinfo=UTC)
    assert _bucket_start(as_of, "5m") == datetime(2026, 8, 12, 7, 50, 0, tzinfo=UTC)


def test_bucket_start_floors_to_1_minute_boundary():
    as_of = datetime(2026, 8, 12, 7, 53, 42, tzinfo=UTC)
    assert _bucket_start(as_of, "1m") == datetime(2026, 8, 12, 7, 53, 0, tzinfo=UTC)


def test_bucket_start_exactly_on_boundary_stays_put():
    as_of = datetime(2026, 8, 12, 7, 55, 0, tzinfo=UTC)
    assert _bucket_start(as_of, "5m") == as_of


def test_bucket_start_one_second_past_boundary_advances():
    as_of = datetime(2026, 8, 12, 7, 55, 1, tzinfo=UTC)
    assert _bucket_start(as_of, "5m") == datetime(2026, 8, 12, 7, 55, 0, tzinfo=UTC)
