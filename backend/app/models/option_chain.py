from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OptionChainSnapshot(Base):
    """Per-strike option chain snapshot, stored every minute (SRD §3, §5)."""

    __tablename__ = "option_chain"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    underlying: Mapped[str] = mapped_column(String(64), default="NIFTY BANK", index=True)
    expiry: Mapped[date] = mapped_column(Date, index=True)
    datetime_: Mapped[datetime] = mapped_column("datetime", DateTime(timezone=True), index=True)
    strike: Mapped[float] = mapped_column(Numeric(12, 2), index=True)
    option_type: Mapped[str] = mapped_column(String(2), index=True)  # CE / PE
    ltp: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    oi: Mapped[int] = mapped_column(BigInteger, default=0)
    oi_change: Mapped[int] = mapped_column(BigInteger, default=0)
    volume: Mapped[int] = mapped_column(BigInteger, default=0)
    iv: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    bid: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    ask: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "underlying", "expiry", "datetime", "strike", "option_type",
            name="uq_option_chain_snapshot_identity",
        ),
        Index("ix_option_chain_lookup", "underlying", "expiry", "datetime", "strike"),
    )
