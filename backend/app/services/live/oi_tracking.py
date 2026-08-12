"""Diffs live option-chain OI against the most recently persisted snapshot,
since a single quote poll has no notion of "change" on its own - that's
only meaningful against a prior point in time. Persists each poll as the
new baseline (throttled - see `MIN_PERSIST_INTERVAL_SECONDS`) so live polls
also accumulate into `option_chain` history between backfills, and so the
*next* poll (whether from the read-only status endpoint or the scheduled
live loop) has something real to diff against, regardless of which one
happens to run first.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.option_chain import OptionChainSnapshot
from app.services.option_chain.analyzer import StrikeRow

# Don't write a new baseline more often than this - GET /live/status can be
# polled every few seconds by the frontend, and writing a full chain on
# every single one of those would both flood the table and make "change"
# meaningless (near-zero elapsed time between baseline and read).
MIN_PERSIST_INTERVAL_SECONDS = 20


async def _latest_snapshot_time(db: AsyncSession, underlying: str, expiry: date) -> datetime | None:
    stmt = select(func.max(OptionChainSnapshot.datetime_)).where(
        OptionChainSnapshot.underlying == underlying, OptionChainSnapshot.expiry == expiry
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _latest_prior_chain(db: AsyncSession, underlying: str, expiry: date) -> list[StrikeRow]:
    """Reconstructs a `StrikeRow` chain from the latest stored snapshot per
    (strike, option_type) - both OI (for change) and LTP (for the OI
    buildup classifier's price-change input, see `analyzer.atm_oi_buildup_bias`)."""
    stmt = (
        select(OptionChainSnapshot)
        .where(OptionChainSnapshot.underlying == underlying, OptionChainSnapshot.expiry == expiry)
        .order_by(OptionChainSnapshot.datetime_.desc())
    )
    rows = list((await db.execute(stmt)).scalars().all())

    latest: dict[tuple[float, str], OptionChainSnapshot] = {}
    for row in rows:
        key = (float(row.strike), row.option_type)
        latest.setdefault(key, row)  # newest-first, so first hit per key wins

    by_strike: dict[float, dict[str, OptionChainSnapshot]] = {}
    for (strike, option_type), row in latest.items():
        by_strike.setdefault(strike, {})[option_type] = row

    chain = []
    for strike, sides in by_strike.items():
        ce, pe = sides.get("CE"), sides.get("PE")
        chain.append(
            StrikeRow(
                strike=strike,
                ce_oi=ce.oi if ce else 0,
                ce_ltp=float(ce.ltp) if ce else 0.0,
                pe_oi=pe.oi if pe else 0,
                pe_ltp=float(pe.ltp) if pe else 0.0,
            )
        )
    return chain


async def enrich_and_maybe_persist_oi_change(
    db: AsyncSession, underlying: str, expiry: date, as_of: datetime, chain: list[StrikeRow]
) -> tuple[list[StrikeRow], list[StrikeRow] | None]:
    """Mutates and returns (`chain` with real ce_oi_change/pe_oi_change,
    the previous chain it diffed against - or None on the very first poll)."""
    if not chain:
        return chain, None

    previous_chain = await _latest_prior_chain(db, underlying, expiry)
    prior = {(r.strike, "CE"): r.ce_oi for r in previous_chain} | {(r.strike, "PE"): r.pe_oi for r in previous_chain}
    for row in chain:
        prev_ce_oi = prior.get((row.strike, "CE"))
        prev_pe_oi = prior.get((row.strike, "PE"))
        row.ce_oi_change = row.ce_oi - prev_ce_oi if prev_ce_oi is not None else 0
        row.pe_oi_change = row.pe_oi - prev_pe_oi if prev_pe_oi is not None else 0

    last_persisted = await _latest_snapshot_time(db, underlying, expiry)
    if last_persisted is not None and as_of - last_persisted < timedelta(seconds=MIN_PERSIST_INTERVAL_SECONDS):
        return chain, (previous_chain or None)

    rows_to_insert = []
    for row in chain:
        rows_to_insert.append(
            {
                "underlying": underlying, "expiry": expiry, "datetime": as_of,
                "strike": row.strike, "option_type": "CE",
                "ltp": row.ce_ltp, "oi": row.ce_oi, "oi_change": row.ce_oi_change, "volume": row.ce_volume,
            }
        )
        rows_to_insert.append(
            {
                "underlying": underlying, "expiry": expiry, "datetime": as_of,
                "strike": row.strike, "option_type": "PE",
                "ltp": row.pe_ltp, "oi": row.pe_oi, "oi_change": row.pe_oi_change, "volume": row.pe_volume,
            }
        )

    stmt = insert(OptionChainSnapshot).values(rows_to_insert)
    stmt = stmt.on_conflict_do_update(
        index_elements=["underlying", "expiry", "datetime", "strike", "option_type"],
        set_={col: stmt.excluded[col] for col in ("ltp", "oi", "oi_change", "volume")},
    )
    await db.execute(stmt)
    await db.commit()

    return chain, (previous_chain or None)
