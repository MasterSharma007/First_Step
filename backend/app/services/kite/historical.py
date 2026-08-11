"""Historical Data Service (SRD §2, §3) backed by Kite Connect's historical
data API. Fetches spot/option/futures OHLC for backfilling the database.
"""

from __future__ import annotations

from datetime import date, datetime

from app.services.kite.client import KiteClient

INTERVAL_MAP = {
    "1m": "minute",
    "5m": "5minute",
    "15m": "15minute",
    "1d": "day",
}


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
