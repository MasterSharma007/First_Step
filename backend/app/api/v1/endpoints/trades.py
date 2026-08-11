from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trade_execution import TradeExecution
from app.schemas.trade import TradeExecutionOut

router = APIRouter(prefix="/trades", tags=["trades"])


@router.get("", response_model=list[TradeExecutionOut])
async def list_trades(limit: int = 50, db: AsyncSession = Depends(get_db)) -> list[TradeExecution]:
    stmt = select(TradeExecution).order_by(TradeExecution.entry_time.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())
