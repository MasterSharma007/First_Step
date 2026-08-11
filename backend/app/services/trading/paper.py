"""Paper Trading Engine (SRD §2): simulates entries/exits/P&L with no
broker calls - same interface as `LiveTradingEngine` so the rest of the
platform is agnostic to which one it's talking to."""

from __future__ import annotations

from datetime import UTC, datetime

from app.services.trading.base import ClosedPosition, OpenPosition, TradingEngine


class PaperTradingEngine(TradingEngine):
    def __init__(self, lot_size: int = 35):
        super().__init__()
        self.lot_size = lot_size

    def enter(
        self,
        symbol: str,
        option_type: str,
        quantity: int,
        price: float,
        stop_loss: float,
        target: float,
        signal_id: str | None = None,
    ) -> OpenPosition:
        position = OpenPosition(
            order_id=self._new_order_id(),
            signal_id=signal_id,
            symbol=symbol,
            option_type=option_type,
            quantity=quantity,
            entry_time=datetime.now(UTC),
            entry_price=price,
            stop_loss=stop_loss,
            target=target,
        )
        self.open_positions[position.order_id] = position
        return position

    def exit(self, order_id: str, price: float, reason: str) -> ClosedPosition:
        position = self.open_positions.pop(order_id)
        pnl = round((price - position.entry_price) * position.quantity, 2)
        closed = ClosedPosition(
            **position.__dict__,
            exit_price=price,
            exit_reason=reason,
            pnl=pnl,
        )
        self.closed_positions.append(closed)
        return closed
