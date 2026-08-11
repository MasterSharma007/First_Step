import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TradeMode(str, enum.Enum):
    BACKTEST = "BACKTEST"
    PAPER = "PAPER"
    LIVE = "LIVE"


class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class TradeExecution(Base):
    """Executed trades - backtest, paper, or live (SRD §2, §5)."""

    __tablename__ = "trade_execution"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trade_signals.signal_id"), nullable=True
    )
    mode: Mapped[TradeMode] = mapped_column(Enum(TradeMode, name="trade_mode"), index=True)
    status: Mapped[TradeStatus] = mapped_column(
        Enum(TradeStatus, name="trade_status"), default=TradeStatus.OPEN, index=True
    )
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(64))
    option_type: Mapped[str] = mapped_column(String(2))  # CE / PE
    quantity: Mapped[int] = mapped_column(default=0)
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[float] = mapped_column(Numeric(12, 2))
    exit_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    target: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    pnl: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    charges: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
