"""Historical Data Service backfill CLI (SRD §2, §3).

Usage (run from `backend/`, after `KITE_ACCESS_TOKEN` is set for today):

    uv run backfill spot --years 2
    uv run backfill vix --years 2
    uv run backfill futures --years 1
    uv run backfill options --expiries 2 --strikes-around-atm 10
    uv run backfill all --years 2

Important limitation: Kite's `/instruments` endpoint only lists currently
tradeable contracts, so `futures`/`options` can only backfill what's live
right now, back to whenever that specific contract was listed - not a true
multi-year options history. `spot`/`vix` have no such limitation. See
`app/services/kite/instruments.py` for details. Going forward, history
accumulates naturally via the live feed (`app/services/kite/live_feed.py`).
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, date, datetime, timedelta

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.core.logging import configure_logging, get_logger
from app.services.kite.client import get_kite_client
from app.services.kite.historical import HistoricalDataService, iter_date_chunks
from app.services.kite.ingest import (
    upsert_futures,
    upsert_india_vix,
    upsert_option_ohlc,
    upsert_spot_ohlc,
)
from app.services.kite.instruments import InstrumentResolver

logger = get_logger(__name__)

DEFAULT_INTERVALS = ["1d", "15m", "5m", "1m"]


async def _fetch(historical: HistoricalDataService, token: int, start: date, end: date, interval: str, delay: float) -> list[dict]:
    candles = await asyncio.to_thread(historical.fetch_ohlc, token, start, end, interval)
    if delay:
        await asyncio.sleep(delay)
    return candles


async def backfill_spot(historical, db, symbol: str, token: int, start: date, end: date, intervals: list[str], delay: float) -> None:
    for interval in intervals:
        total = 0
        for chunk_start, chunk_end in iter_date_chunks(start, end, interval):
            candles = await _fetch(historical, token, chunk_start, chunk_end, interval, delay)
            total += await upsert_spot_ohlc(db, symbol, interval, candles)
        logger.info("spot_backfilled", symbol=symbol, interval=interval, rows=total)


async def backfill_vix(historical, db, token: int, start: date, end: date, intervals: list[str], delay: float) -> None:
    for interval in intervals:
        total = 0
        for chunk_start, chunk_end in iter_date_chunks(start, end, interval):
            candles = await _fetch(historical, token, chunk_start, chunk_end, interval, delay)
            total += await upsert_india_vix(db, interval, candles)
        logger.info("vix_backfilled", interval=interval, rows=total)


async def backfill_futures(historical, db, resolver: InstrumentResolver, underlying: str, start: date, end: date, interval: str, delay: float) -> None:
    contracts = resolver.futures(underlying)
    if not contracts:
        logger.warning("no_futures_contracts_found", underlying=underlying)
        return
    for fut in contracts:
        total = 0
        for chunk_start, chunk_end in iter_date_chunks(start, end, interval):
            candles = await _fetch(historical, fut.instrument_token, chunk_start, chunk_end, interval, delay)
            total += await upsert_futures(db, underlying, fut.expiry, candles)
        logger.info("futures_backfilled", tradingsymbol=fut.tradingsymbol, expiry=str(fut.expiry), rows=total)


async def backfill_options(
    historical,
    db,
    resolver: InstrumentResolver,
    kite_client,
    underlying: str,
    spot_symbol: str,
    start: date,
    end: date,
    interval: str,
    strikes_around_atm: int,
    max_expiries: int,
    delay: float,
) -> None:
    quote = await asyncio.to_thread(kite_client.kite.ltp, [f"NSE:{spot_symbol}"])
    spot_price = quote[f"NSE:{spot_symbol}"]["last_price"]
    logger.info("options_backfill_spot_anchor", spot_symbol=spot_symbol, spot_price=spot_price)

    expiries = resolver.expiries(underlying)[:max_expiries]
    if not expiries:
        logger.warning("no_option_expiries_found", underlying=underlying)
        return

    for expiry in expiries:
        chain = resolver.options(underlying, expiry)
        nearest = sorted(chain, key=lambda inst: abs(inst.strike - spot_price))[: strikes_around_atm * 2]
        for inst in nearest:
            total = 0
            for chunk_start, chunk_end in iter_date_chunks(start, end, interval):
                candles = await _fetch(historical, inst.instrument_token, chunk_start, chunk_end, interval, delay)
                total += await upsert_option_ohlc(
                    db, underlying, inst.strike, expiry, inst.instrument_type, interval, candles
                )
            logger.info("option_backfilled", tradingsymbol=inst.tradingsymbol, rows=total)


def _date_range(args: argparse.Namespace) -> tuple[date, date]:
    end = args.to or datetime.now(UTC).date()
    start = args.frm or (end - timedelta(days=365 * args.years))
    return start, end


async def run_async(args: argparse.Namespace) -> None:
    settings = get_settings()
    configure_logging(settings.debug)
    kite_client = get_kite_client()
    historical = HistoricalDataService(kite_client)
    resolver = InstrumentResolver(kite_client)
    start, end = _date_range(args)

    async with async_session_factory() as db:
        if args.command in ("spot", "all"):
            spot = resolver.spot_index(settings.trading_symbol)
            await backfill_spot(historical, db, settings.trading_symbol, spot.instrument_token, start, end, args.intervals, args.delay)

        if args.command in ("vix", "all"):
            vix = resolver.india_vix()
            await backfill_vix(historical, db, vix.instrument_token, start, end, ["1d"] if args.command == "all" else args.intervals, args.delay)

        if args.command in ("futures", "all"):
            await backfill_futures(historical, db, resolver, settings.nfo_underlying, start, end, "1d", args.delay)

        if args.command in ("options", "all"):
            await backfill_options(
                historical,
                db,
                resolver,
                kite_client,
                settings.nfo_underlying,
                settings.trading_symbol,
                start,
                end,
                "1d" if args.command == "all" else args.interval,
                args.strikes_around_atm,
                args.expiries,
                args.delay,
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Backfill historical market data from Kite Connect.")
    parser.add_argument("command", choices=["spot", "vix", "futures", "options", "all"])
    parser.add_argument("--years", type=int, default=2, help="How many years back to fetch (default 2, ignored if --from is set)")
    parser.add_argument("--from", dest="frm", type=date.fromisoformat, default=None, help="YYYY-MM-DD")
    parser.add_argument("--to", type=date.fromisoformat, default=None, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--intervals", nargs="+", default=DEFAULT_INTERVALS, help="Only for spot/vix, e.g. --intervals 1d 5m")
    parser.add_argument("--interval", default="1d", help="Only for options backfill (default 1d - minute data for every strike is a LOT of requests)")
    parser.add_argument("--expiries", type=int, default=2, help="Number of nearest option expiries to backfill (default 2)")
    parser.add_argument("--strikes-around-atm", type=int, default=10, help="Strikes each side of spot to backfill (default 10)")
    parser.add_argument("--delay", type=float, default=0.4, help="Seconds to sleep between Kite API calls (default 0.4, ~2.5 req/s)")
    return parser


def run() -> None:
    args = build_parser().parse_args()
    asyncio.run(run_async(args))


if __name__ == "__main__":
    run()
