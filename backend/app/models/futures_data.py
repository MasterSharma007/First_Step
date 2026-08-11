from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FuturesTick(Base):
    """Futures LTP / OI / OI change (SRD §4)."""

    __tablename__ = "futures_data"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    underlying: Mapped[str] = mapped_column(String(64), default="NIFTY BANK", index=True)
    expiry: Mapped[date] = mapped_column(Date, index=True)
    datetime_: Mapped[datetime] = mapped_column("datetime", DateTime(timezone=True), index=True)
    ltp: Mapped[float] = mapped_column(Numeric(12, 2))
    oi: Mapped[int] = mapped_column(BigInteger, default=0)
    oi_change: Mapped[int] = mapped_column(BigInteger, default=0)
    volume: Mapped[int] = mapped_column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("underlying", "expiry", "datetime", name="uq_futures_identity"),
        Index("ix_futures_lookup", "underlying", "expiry", "datetime"),
    )
