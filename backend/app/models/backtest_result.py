import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BacktestResult(Base):
    """Summary metrics for a single backtest run (SRD §2, §9)."""

    __tablename__ = "backtest_results"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    strategy_name: Mapped[str] = mapped_column(String(128))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    total_trades: Mapped[int] = mapped_column(default=0)
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    profit_factor: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    max_drawdown: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    sharpe_ratio: Mapped[float] = mapped_column(Numeric(8, 4), default=0)
    net_pnl: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
