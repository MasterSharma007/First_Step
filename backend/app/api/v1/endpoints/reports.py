from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.trade_execution import TradeExecution, TradeStatus
from app.schemas.trade import DailyReport
from app.services.backtesting.metrics import TradeResult, compute_metrics

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily", response_model=DailyReport)
async def daily_report(report_date: date | None = None, db: AsyncSession = Depends(get_db)) -> DailyReport:
    report_date = report_date or datetime.now(UTC).date()
    stmt = select(TradeExecution).where(
        TradeExecution.status == TradeStatus.CLOSED,
        TradeExecution.exit_time >= report_date,
        TradeExecution.exit_time < report_date.fromordinal(report_date.toordinal() + 1),
    )
    result = await db.execute(stmt)
    trades = list(result.scalars().all())

    metrics = compute_metrics([TradeResult(pnl=float(t.pnl or 0)) for t in trades])
    charges = sum(float(t.charges or 0) for t in trades)

    return DailyReport(
        report_date=report_date.isoformat(),
        total_trades=metrics.total_trades,
        win_rate=metrics.win_rate,
        net_profit=metrics.net_pnl - charges,
        charges=round(charges, 2),
        max_drawdown=metrics.max_drawdown,
    )
