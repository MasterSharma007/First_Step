from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.option_chain import OptionChainSnapshot
from app.schemas.option_chain import OptionChainAnalysis, OptionChainRow
from app.services.option_chain.analyzer import (
    StrikeRow,
    atm_strike,
    max_pain,
    put_call_ratio,
    writing_activity,
)

router = APIRouter(prefix="/option-chain", tags=["option-chain"])


@router.get("/{underlying}/expiries", response_model=list[date])
async def list_expiries(underlying: str, db: AsyncSession = Depends(get_db)) -> list[date]:
    """Expiries with at least one stored snapshot - lets a UI offer a real
    picker instead of guessing a date that may 404."""
    stmt = (
        select(OptionChainSnapshot.expiry)
        .where(OptionChainSnapshot.underlying == underlying)
        .distinct()
        .order_by(OptionChainSnapshot.expiry.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{underlying}/{expiry}", response_model=OptionChainAnalysis)
async def get_option_chain_analysis(
    underlying: str,
    expiry: date,
    spot_price: float,
    as_of: date | None = None,
    db: AsyncSession = Depends(get_db),
) -> OptionChainAnalysis:
    """Without `as_of`, returns the latest stored snapshot. With `as_of`,
    returns the latest snapshot at or before that date - lets historical
    (backfilled) chains be browsed by day, not just the live one."""
    stmt = select(OptionChainSnapshot).where(
        OptionChainSnapshot.underlying == underlying, OptionChainSnapshot.expiry == expiry
    )
    if as_of is not None:
        stmt = stmt.where(OptionChainSnapshot.datetime_ < as_of + timedelta(days=1))
    stmt = stmt.order_by(OptionChainSnapshot.datetime_.desc())

    result = await db.execute(stmt)
    all_rows = list(result.scalars().all())
    if not all_rows:
        raise HTTPException(status_code=404, detail="No option chain data for this underlying/expiry/date")

    latest_ts = all_rows[0].datetime_
    latest = [r for r in all_rows if r.datetime_ == latest_ts]

    by_strike: dict[float, dict] = {}
    for row in latest:
        entry = by_strike.setdefault(float(row.strike), {})
        entry[row.option_type] = row

    strike_rows: list[StrikeRow] = []
    output_rows: list[OptionChainRow] = []
    for strike, sides in sorted(by_strike.items()):
        ce = sides.get("CE")
        pe = sides.get("PE")
        strike_rows.append(
            StrikeRow(
                strike=strike,
                ce_oi=ce.oi if ce else 0,
                ce_oi_change=ce.oi_change if ce else 0,
                ce_volume=ce.volume if ce else 0,
                ce_ltp=float(ce.ltp) if ce else 0.0,
                pe_oi=pe.oi if pe else 0,
                pe_oi_change=pe.oi_change if pe else 0,
                pe_volume=pe.volume if pe else 0,
                pe_ltp=float(pe.ltp) if pe else 0.0,
            )
        )
        output_rows.append(
            OptionChainRow(
                strike=strike,
                ce_ltp=float(ce.ltp) if ce else None,
                ce_oi=ce.oi if ce else 0,
                ce_oi_change=ce.oi_change if ce else 0,
                ce_volume=ce.volume if ce else 0,
                ce_iv=float(ce.iv) if ce and ce.iv is not None else None,
                pe_ltp=float(pe.ltp) if pe else None,
                pe_oi=pe.oi if pe else 0,
                pe_oi_change=pe.oi_change if pe else 0,
                pe_volume=pe.volume if pe else 0,
                pe_iv=float(pe.iv) if pe and pe.iv is not None else None,
            )
        )

    pcr = put_call_ratio(strike_rows)
    writing = writing_activity(strike_rows, spot_price=spot_price)

    return OptionChainAnalysis(
        underlying=underlying,
        expiry=expiry,
        as_of=latest_ts,
        spot_price=spot_price,
        atm_strike=atm_strike(strike_rows, spot_price),
        pcr=pcr,
        max_pain=max_pain(strike_rows),
        total_ce_oi=sum(r.ce_oi for r in strike_rows),
        total_pe_oi=sum(r.pe_oi for r in strike_rows),
        rows=output_rows,
        oi_signal=writing["verdict"],
    )
