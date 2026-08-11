from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.spot_ohlc import SpotOHLC
from app.schemas.market_data import SpotOHLCOut

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/spot-ohlc", response_model=list[SpotOHLCOut])
async def get_spot_ohlc(
    interval: str = Query("5m", pattern="^(1m|5m|15m|1d)$"),
    symbol: str = "NIFTY BANK",
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(500, le=5000),
    db: AsyncSession = Depends(get_db),
) -> list[SpotOHLC]:
    stmt = select(SpotOHLC).where(SpotOHLC.symbol == symbol, SpotOHLC.interval == interval)
    if start:
        stmt = stmt.where(SpotOHLC.datetime_ >= start)
    if end:
        stmt = stmt.where(SpotOHLC.datetime_ <= end)
    stmt = stmt.order_by(SpotOHLC.datetime_.desc()).limit(limit)

    result = await db.execute(stmt)
    rows = list(result.scalars().all())
    rows.reverse()
    return rows
