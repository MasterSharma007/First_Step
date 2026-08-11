import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SignalType(str, enum.Enum):
    CE_ENTRY = "CE_ENTRY"
    PE_ENTRY = "PE_ENTRY"
    EXIT = "EXIT"
    PARTIAL_EXIT = "PARTIAL_EXIT"
    SL_UPDATE = "SL_UPDATE"


class TradeSignal(Base):
    """Signals produced by the Signal Generation Engine (SRD §2, §6, §8)."""

    __tablename__ = "trade_signals"

    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    underlying: Mapped[str] = mapped_column(String(64), default="NIFTY BANK")
    strike: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType, name="signal_type"), index=True)
    entry_price: Mapped[float] = mapped_column(Numeric(12, 2))
    stop_loss: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    target: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2))
    reasons: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
