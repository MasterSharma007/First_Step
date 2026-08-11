"""Shared position bookkeeping for paper and live trading engines (SRD §2)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class OpenPosition:
    order_id: str
    signal_id: str | None
    symbol: str
    option_type: str
    quantity: int
    entry_time: datetime
    entry_price: float
    stop_loss: float
    target: float


@dataclass
class ClosedPosition(OpenPosition):
    exit_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    exit_price: float = 0.0
    exit_reason: str = ""
    pnl: float = 0.0


class TradingEngine(ABC):
    """Common interface for `PaperTradingEngine` and `LiveTradingEngine` -
    the Signal Engine and API layer talk to this, not the broker."""

    def __init__(self):
        self.open_positions: dict[str, OpenPosition] = {}
        self.closed_positions: list[ClosedPosition] = []

    @abstractmethod
    def enter(
        self,
        symbol: str,
        option_type: str,
        quantity: int,
        price: float,
        stop_loss: float,
        target: float,
        signal_id: str | None = None,
    ) -> OpenPosition: ...

    @abstractmethod
    def exit(self, order_id: str, price: float, reason: str) -> ClosedPosition: ...

    def _new_order_id(self) -> str:
        return str(uuid.uuid4())

    def unrealized_pnl(self, order_id: str, current_price: float, lot_size: int) -> float:
        position = self.open_positions[order_id]
        return round((current_price - position.entry_price) * lot_size, 2)

    def daily_realized_pnl(self, as_of: datetime | None = None) -> float:
        as_of = as_of or datetime.now(UTC)
        return round(
            sum(p.pnl for p in self.closed_positions if p.exit_time.date() == as_of.date()), 2
        )
