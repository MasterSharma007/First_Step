from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndiaVix(Base):
    """India VIX, daily and intraday (SRD §3)."""

    __tablename__ = "india_vix"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    interval: Mapped[str] = mapped_column(String(8), index=True)  # 1m, 1d
    datetime_: Mapped[datetime] = mapped_column("datetime", DateTime(timezone=True), index=True)
    value: Mapped[float] = mapped_column(Numeric(8, 2))

    __table_args__ = (UniqueConstraint("interval", "datetime", name="uq_india_vix_interval_dt"),)
