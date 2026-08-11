from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketTick(Base):
    """Raw tick-by-tick market data (spot, futures, or option LTP)."""

    __tablename__ = "market_ticks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    symbol: Mapped[str] = mapped_column(String(64), index=True)
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    bid: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    ask: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    oi: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (Index("ix_market_ticks_symbol_timestamp", "symbol", "timestamp"),)
