"""Unit tests for the backfill CLI's DB-free pieces: Kite date-range
chunking and instrument-dump filtering. The upsert/ingest path (writes to
Postgres) is covered by manual verification against a scratch DB rather
than here, to keep the suite DB-free."""

from datetime import date, timedelta
from itertools import pairwise

from app.services.kite.historical import iter_date_chunks
from app.services.kite.instruments import InstrumentResolver


def test_iter_date_chunks_respects_minute_limit():
    chunks = iter_date_chunks(date(2024, 1, 1), date(2024, 4, 1), "1m")
    assert chunks[0] == (date(2024, 1, 1), date(2024, 2, 29))  # 60-day window (2024 is a leap year)
    assert chunks[-1][1] == date(2024, 4, 1)
    for start, end in chunks:
        assert (end - start).days <= 59


def test_iter_date_chunks_single_window_for_daily():
    chunks = iter_date_chunks(date(2023, 1, 1), date(2024, 1, 1), "1d")
    assert len(chunks) == 1
    assert chunks[0] == (date(2023, 1, 1), date(2024, 1, 1))


def test_iter_date_chunks_no_gaps_or_overlaps():
    chunks = iter_date_chunks(date(2024, 1, 1), date(2024, 6, 1), "5m")
    for (_, prev_end), (next_start, _) in pairwise(chunks):
        assert next_start == prev_end + timedelta(days=1)


class _FakeKite:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def instruments(self, exchange: str) -> list[dict]:
        return [r for r in self._rows if r["exchange"] == exchange]


class _FakeClient:
    def __init__(self, rows: list[dict]):
        self.kite = _FakeKite(rows)


FAKE_ROWS = [
    {"instrument_token": 1, "tradingsymbol": "NIFTY BANK", "exchange": "NSE", "segment": "INDICES", "instrument_type": "", "strike": 0, "expiry": None, "name": "NIFTY BANK"},
    {"instrument_token": 2, "tradingsymbol": "INDIA VIX", "exchange": "NSE", "segment": "INDICES", "instrument_type": "", "strike": 0, "expiry": None, "name": "INDIA VIX"},
    {"instrument_token": 3, "tradingsymbol": "BANKNIFTY24AUGFUT", "exchange": "NFO", "segment": "NFO-FUT", "instrument_type": "FUT", "strike": 0, "expiry": date(2024, 8, 29), "name": "BANKNIFTY"},
    {"instrument_token": 4, "tradingsymbol": "BANKNIFTY24AUG48000CE", "exchange": "NFO", "segment": "NFO-OPT", "instrument_type": "CE", "strike": 48000, "expiry": date(2024, 8, 29), "name": "BANKNIFTY"},
    {"instrument_token": 5, "tradingsymbol": "BANKNIFTY24AUG48000PE", "exchange": "NFO", "segment": "NFO-OPT", "instrument_type": "PE", "strike": 48000, "expiry": date(2024, 8, 29), "name": "BANKNIFTY"},
    {"instrument_token": 6, "tradingsymbol": "BANKNIFTY24AUG48100CE", "exchange": "NFO", "segment": "NFO-OPT", "instrument_type": "CE", "strike": 48100, "expiry": date(2024, 8, 29), "name": "BANKNIFTY"},
]


def test_instrument_resolver_spot_and_vix():
    resolver = InstrumentResolver(_FakeClient(FAKE_ROWS))
    assert resolver.spot_index("NIFTY BANK").instrument_token == 1
    assert resolver.india_vix().instrument_token == 2


def test_instrument_resolver_futures_and_options():
    resolver = InstrumentResolver(_FakeClient(FAKE_ROWS))
    futures = resolver.futures("BANKNIFTY")
    assert len(futures) == 1
    assert futures[0].tradingsymbol == "BANKNIFTY24AUGFUT"

    options = resolver.options("BANKNIFTY", date(2024, 8, 29))
    assert {o.tradingsymbol for o in options} == {
        "BANKNIFTY24AUG48000CE",
        "BANKNIFTY24AUG48000PE",
        "BANKNIFTY24AUG48100CE",
    }


def test_instrument_resolver_expiries():
    resolver = InstrumentResolver(_FakeClient(FAKE_ROWS))
    assert resolver.expiries("BANKNIFTY") == [date(2024, 8, 29)]
