"""Historical Data Service (SRD §2, §3) backed by Kite Connect's historical
data API. Fetches spot/option/futures OHLC for backfilling the database.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.services.kite.client import KiteClient

INTERVAL_MAP = {
    "1m": "minute",
    "5m": "5minute",
    "15m": "15minute",
    "1d": "day",
}

# Kite's historical API caps how much date range you can request in a
# single call, keyed by their (not our) interval name.
MAX_DAYS_PER_REQUEST = {
    "minute": 60,
    "3minute": 100,
    "5minute": 100,
    "10minute": 100,
    "15minute": 100,
    "30minute": 100,
    "60minute": 400,
    "day": 2000,
}


def iter_date_chunks(from_date: date, to_date: date, interval: str) -> list[tuple[date, date]]:
    """Split [from_date, to_date] into windows that respect Kite's per-request
    range limit for `interval` (our short form, e.g. "1m", "1d")."""
    kite_interval = INTERVAL_MAP.get(interval, interval)
    max_days = MAX_DAYS_PER_REQUEST.get(kite_interval, 60)

    chunks: list[tuple[date, date]] = []
    chunk_start = from_date
    while chunk_start <= to_date:
        chunk_end = min(chunk_start + timedelta(days=max_days - 1), to_date)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end + timedelta(days=1)
    return chunks


class HistoricalDataService:
    def __init__(self, client: KiteClient):
        self.client = client

    def fetch_ohlc(
        self,
        instrument_token: int,
        from_date: date | datetime,
        to_date: date | datetime,
        interval: str,
        continuous: bool = False,
    ) -> list[dict]:
        """Returns raw Kite candle dicts: date/open/high/low/close/volume
        (+ oi for F&O instruments). Kite limits historical requests to
        ~60 days per call for minute intervals - callers should chunk
        `from_date`/`to_date` ranges accordingly for multi-year backfills.
        """
        kite_interval = INTERVAL_MAP.get(interval, interval)
        return self.client.kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval=kite_interval,
            continuous=continuous,
            oi=True,
        )

    def fetch_instruments(self, exchange: str = "NFO") -> list[dict]:
        """Full instrument dump, used to resolve strike/expiry -> instrument_token."""
        return self.client.kite.instruments(exchange=exchange)
