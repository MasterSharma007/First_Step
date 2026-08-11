from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trade_signal import TradeSignal
from app.schemas.signal import TradeSignalOut

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("", response_model=list[TradeSignalOut])
async def list_signals(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[TradeSignal]:
    stmt = select(TradeSignal).order_by(TradeSignal.entry_time.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
