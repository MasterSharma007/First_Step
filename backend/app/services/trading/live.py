"""Live Trading Engine (SRD §2): places real orders through Kite Connect.

Mirrors `PaperTradingEngine`'s interface exactly so callers (API layer,
Signal Engine loop) can switch between them via `settings.paper_trading`
without branching logic. Every entry/exit still goes through
`RiskManager` checks upstream - this class does not re-validate risk, it
only executes.
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.services.kite.orders import KiteOrderService
from app.services.trading.base import ClosedPosition, OpenPosition, TradingEngine

logger = get_logger(__name__)


class LiveTradingEngine(TradingEngine):
    def __init__(self, order_service: KiteOrderService):
        super().__init__()
        self.order_service = order_service

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
        result = self.order_service.buy_option(symbol, quantity)
        position = OpenPosition(
            order_id=result.order_id,
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
        logger.info("live_position_opened", order_id=position.order_id, symbol=symbol)
        return position

    def exit(self, order_id: str, price: float, reason: str) -> ClosedPosition:
        position = self.open_positions.pop(order_id)
        self.order_service.exit_position(position.symbol, position.quantity)
        pnl = round((price - position.entry_price) * position.quantity, 2)
        closed = ClosedPosition(
            **position.__dict__,
            exit_price=price,
            exit_reason=reason,
            pnl=pnl,
        )
        self.closed_positions.append(closed)
        logger.info("live_position_closed", order_id=order_id, reason=reason, pnl=pnl)
        return closed
