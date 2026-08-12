"""Instrument token resolution against Kite's instrument dump (SRD §2, §3).

Kite's `/instruments` endpoint only lists currently-tradeable contracts - it
does not expose tokens for options/futures that have already expired. That
means a full multi-year *options/futures* history is not retrievable in one
backfill; you can only pull what's live now and accumulate history forward
from there via the live feed (`app/services/kite/live_feed.py`). The spot
index and India VIX have no such limitation - Kite serves their full
historical range regardless of how old the request is.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.services.kite.client import KiteClient


@dataclass
class Instrument:
    instrument_token: int
    tradingsymbol: str
    exchange: str
    segment: str
    instrument_type: str
    strike: float
    expiry: date | None
    name: str
    lot_size: int


def _to_instrument(row: dict) -> Instrument:
    expiry = row.get("expiry") or None
    return Instrument(
        instrument_token=row["instrument_token"],
        tradingsymbol=row["tradingsymbol"],
        exchange=row["exchange"],
        segment=row.get("segment", ""),
        instrument_type=row.get("instrument_type", ""),
        strike=float(row.get("strike") or 0),
        expiry=expiry,
        name=row.get("name", ""),
        lot_size=int(row.get("lot_size") or 1),
    )


class InstrumentResolver:
    """Caches the (large) NSE and NFO instrument dumps in memory for the
    life of the process/script - re-fetch by constructing a new instance."""

    def __init__(self, client: KiteClient):
        self.client = client
        self._nse_cache: list[dict] | None = None
        self._nfo_cache: list[dict] | None = None

    def _nse(self) -> list[dict]:
        if self._nse_cache is None:
            self._nse_cache = self.client.kite.instruments("NSE")
        return self._nse_cache

    def _nfo(self) -> list[dict]:
        if self._nfo_cache is None:
            self._nfo_cache = self.client.kite.instruments("NFO")
        return self._nfo_cache

    def spot_index(self, name: str = "NIFTY BANK") -> Instrument:
        for row in self._nse():
            if row.get("segment") == "INDICES" and row.get("name") == name:
                return _to_instrument(row)
        raise LookupError(f"Spot index {name!r} not found in NSE instrument dump")

    def india_vix(self) -> Instrument:
        return self.spot_index("INDIA VIX")

    def futures(self, underlying: str = "BANKNIFTY") -> list[Instrument]:
        rows = [r for r in self._nfo() if r.get("name") == underlying and r.get("instrument_type") == "FUT"]
        return sorted((_to_instrument(r) for r in rows), key=lambda i: i.expiry or date.max)

    def options(self, underlying: str = "BANKNIFTY", expiry: date | None = None) -> list[Instrument]:
        rows = [
            r
            for r in self._nfo()
            if r.get("name") == underlying and r.get("instrument_type") in ("CE", "PE")
        ]
        instruments = [_to_instrument(r) for r in rows]
        if expiry is not None:
            instruments = [i for i in instruments if i.expiry == expiry]
        return sorted(instruments, key=lambda i: (i.expiry or date.max, i.strike))

    def expiries(self, underlying: str = "BANKNIFTY") -> list[date]:
        found = {
            r["expiry"]
            for r in self._nfo()
            if r.get("name") == underlying and r.get("instrument_type") in ("FUT", "CE", "PE") and r.get("expiry")
        }
        return sorted(found)
