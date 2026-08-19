from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.trade_execution import TradeExecution, TradeMode, TradeStatus
from app.schemas.trade import DailyReport
from app.services.backtesting.metrics import TradeResult, compute_metrics

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily", response_model=DailyReport)
async def daily_report(report_date: date | None = None, db: AsyncSession = Depends(get_db)) -> DailyReport:
    """Scoped to whichever mode (`PAPER`/`LIVE`) is currently active via
    `settings.paper_trading`, so a day that has both paper and real trades
    (e.g. right after switching modes) never blends simulated P&L with
    real P&L into one number."""
    settings = get_settings()
    mode = TradeMode.PAPER if settings.paper_trading else TradeMode.LIVE
    report_date = report_date or datetime.now(UTC).date()
    stmt = select(TradeExecution).where(
        TradeExecution.mode == mode,
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


@router.get("/range", response_model=list[DailyReport])
async def range_report(
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[DailyReport]:
    """One `DailyReport` per calendar day in the range that had closed trades,
    scoped to whichever mode is currently active - same scoping rationale as
    `daily_report` above."""
    settings = get_settings()
    mode = TradeMode.PAPER if settings.paper_trading else TradeMode.LIVE
    end_date = end_date or datetime.now(UTC).date()
    start_date = start_date or end_date - timedelta(days=30)

    stmt = select(TradeExecution).where(
        TradeExecution.mode == mode,
        TradeExecution.status == TradeStatus.CLOSED,
        TradeExecution.exit_time >= start_date,
        TradeExecution.exit_time < end_date + timedelta(days=1),
    )
    result = await db.execute(stmt)
    trades = list(result.scalars().all())

    by_date: dict[date, list[TradeExecution]] = defaultdict(list)
    for t in trades:
        by_date[t.exit_time.date()].append(t)

    reports = []
    for day, day_trades in sorted(by_date.items(), reverse=True):
        metrics = compute_metrics([TradeResult(pnl=float(t.pnl or 0)) for t in day_trades])
        charges = sum(float(t.charges or 0) for t in day_trades)
        reports.append(
            DailyReport(
                report_date=day.isoformat(),
                total_trades=metrics.total_trades,
                win_rate=metrics.win_rate,
                net_profit=metrics.net_pnl - charges,
                charges=round(charges, 2),
                max_drawdown=metrics.max_drawdown,
            )
        )
    return reports
