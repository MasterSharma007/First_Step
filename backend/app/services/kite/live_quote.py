"""Live quote polling via Kite's REST quote API (SRD §2 Live Market Data
Service).

Deliberately uses `kite.quote()` polling rather than the tick-by-tick
websocket (`live_feed.py`, which needs its own long-running connection
process wired up separately) - a ~15-30s poll from a background scheduler
job is a far simpler fit for the live cockpit / paper trading loop, at the
cost of tick-level granularity we don't need for a signal that only
re-evaluates every cycle anyway.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.kite.client import KiteClient
from app.services.kite.instruments import Instrument
from app.services.option_chain.analyzer import StrikeRow


@dataclass
class LiveQuote:
    instrument_token: int
    tradingsymbol: str
    last_price: float
    volume: int
    oi: int
    bid: float | None
    ask: float | None


def fetch_quotes(client: KiteClient, instruments: list[Instrument]) -> dict[str, LiveQuote]:
    """Returns quotes keyed by tradingsymbol. Kite caps quote() at 500
    instruments per call - callers batch near-ATM strikes only, which is
    always well under that."""
    if not instruments:
        return {}

    keys = [f"{inst.exchange}:{inst.tradingsymbol}" for inst in instruments]
    raw = client.kite.quote(keys)

    result: dict[str, LiveQuote] = {}
    for inst, key in zip(instruments, keys, strict=True):
        q = raw.get(key)
        if not q:
            continue
        depth = q.get("depth", {})
        bid = (depth.get("buy") or [{}])[0].get("price")
        ask = (depth.get("sell") or [{}])[0].get("price")
        result[inst.tradingsymbol] = LiveQuote(
            instrument_token=inst.instrument_token,
            tradingsymbol=inst.tradingsymbol,
            last_price=q.get("last_price", 0.0),
            volume=q.get("volume", 0),
            oi=q.get("oi", 0),
            bid=bid,
            ask=ask,
        )
    return result


def fetch_ltp(client: KiteClient, exchange: str, tradingsymbol: str) -> float:
    key = f"{exchange}:{tradingsymbol}"
    raw = client.kite.ltp([key])
    return float(raw[key]["last_price"])


def option_chain_from_quotes(option_instruments: list[Instrument], quotes: dict[str, LiveQuote]) -> list[StrikeRow]:
    """Combines CE/PE live quotes for a set of option instruments (same
    expiry) into per-strike `StrikeRow`s for the Option Chain / Signal
    engines. OI *change* isn't available from a single quote snapshot -
    that's only meaningful against the previous poll, which the live loop
    (not this pure function) is responsible for diffing."""
    by_strike: dict[float, dict[str, LiveQuote]] = {}
    for inst in option_instruments:
        quote = quotes.get(inst.tradingsymbol)
        if quote is None:
            continue
        by_strike.setdefault(inst.strike, {})[inst.instrument_type] = quote

    rows = []
    for strike, sides in by_strike.items():
        ce, pe = sides.get("CE"), sides.get("PE")
        rows.append(
            StrikeRow(
                strike=strike,
                ce_oi=ce.oi if ce else 0,
                ce_volume=ce.volume if ce else 0,
                ce_ltp=ce.last_price if ce else 0.0,
                pe_oi=pe.oi if pe else 0,
                pe_volume=pe.volume if pe else 0,
                pe_ltp=pe.last_price if pe else 0.0,
            )
        )
    return rows
