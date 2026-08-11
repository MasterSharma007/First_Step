from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SpotOHLC(Base):
    """Bank Nifty spot candles at 1m / 5m / 15m / daily intervals (SRD §3)."""

    __tablename__ = "spot_ohlc"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), default="NIFTY BANK", index=True)
    interval: Mapped[str] = mapped_column(String(8), index=True)  # 1m, 5m, 15m, 1d
    datetime_: Mapped[datetime] = mapped_column("datetime", DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Numeric(12, 2))
    high: Mapped[float] = mapped_column(Numeric(12, 2))
    low: Mapped[float] = mapped_column(Numeric(12, 2))
    close: Mapped[float] = mapped_column(Numeric(12, 2))
    volume: Mapped[int] = mapped_column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("symbol", "interval", "datetime", name="uq_spot_ohlc_symbol_interval_dt"),
        Index("ix_spot_ohlc_symbol_interval_dt", "symbol", "interval", "datetime"),
    )
