from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OptionOHLC(Base):
    """Historical option candles per strike/expiry/type (SRD §3)."""

    __tablename__ = "option_ohlc"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    underlying: Mapped[str] = mapped_column(String(64), default="NIFTY BANK", index=True)
    strike: Mapped[float] = mapped_column(Numeric(12, 2), index=True)
    expiry: Mapped[date] = mapped_column(Date, index=True)
    option_type: Mapped[str] = mapped_column(String(2), index=True)  # CE / PE
    interval: Mapped[str] = mapped_column(String(8), index=True)
    datetime_: Mapped[datetime] = mapped_column("datetime", DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Numeric(12, 2))
    high: Mapped[float] = mapped_column(Numeric(12, 2))
    low: Mapped[float] = mapped_column(Numeric(12, 2))
    close: Mapped[float] = mapped_column(Numeric(12, 2))
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    oi: Mapped[int] = mapped_column(BigInteger, default=0)
    oi_change: Mapped[int] = mapped_column(BigInteger, default=0)
    iv: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "underlying", "strike", "expiry", "option_type", "interval", "datetime",
            name="uq_option_ohlc_identity",
        ),
        Index("ix_option_ohlc_lookup", "underlying", "expiry", "strike", "option_type", "datetime"),
    )
