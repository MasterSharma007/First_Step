"""Order execution against Kite Connect (SRD §2 Live Trading Engine).

Thin, explicit wrapper around the handful of order calls the platform
needs (buy CE/PE, exit, SL) rather than exposing the full Kite order API
surface, so the Trading Engine has one obvious call per intent.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.services.kite.client import KiteClient

logger = get_logger(__name__)


@dataclass
class OrderResult:
    order_id: str
    status: str


class KiteOrderService:
    def __init__(self, client: KiteClient, exchange: str = "NFO", product: str = "MIS"):
        self.client = client
        self.exchange = exchange
        self.product = product

    def _place(self, tradingsymbol: str, transaction_type: str, quantity: int, order_type: str, **kwargs) -> OrderResult:
        kite = self.client.kite
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=self.exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=quantity,
            product=self.product,
            order_type=order_type,
            **kwargs,
        )
        logger.info("kite_order_placed", tradingsymbol=tradingsymbol, transaction_type=transaction_type, order_id=order_id)
        return OrderResult(order_id=order_id, status="PLACED")

    def buy_option(self, tradingsymbol: str, quantity: int, order_type: str = "MARKET", price: float | None = None) -> OrderResult:
        kwargs = {"price": price} if order_type == "LIMIT" else {}
        return self._place(tradingsymbol, "BUY", quantity, order_type, **kwargs)

    def exit_position(self, tradingsymbol: str, quantity: int, order_type: str = "MARKET", price: float | None = None) -> OrderResult:
        kwargs = {"price": price} if order_type == "LIMIT" else {}
        return self._place(tradingsymbol, "SELL", quantity, order_type, **kwargs)

    def place_stop_loss(self, tradingsymbol: str, quantity: int, trigger_price: float, price: float) -> OrderResult:
        kite = self.client.kite
        order_id = kite.place_order(
            variety=kite.VARIETY_REGULAR,
            exchange=self.exchange,
            tradingsymbol=tradingsymbol,
            transaction_type="SELL",
            quantity=quantity,
            product=self.product,
            order_type=kite.ORDER_TYPE_SL,
            trigger_price=trigger_price,
            price=price,
        )
        logger.info("kite_sl_order_placed", tradingsymbol=tradingsymbol, trigger_price=trigger_price, order_id=order_id)
        return OrderResult(order_id=order_id, status="PLACED")

    def modify_stop_loss(self, order_id: str, trigger_price: float, price: float) -> None:
        self.client.kite.modify_order(
            variety=self.client.kite.VARIETY_REGULAR,
            order_id=order_id,
            trigger_price=trigger_price,
            price=price,
        )

    def cancel_order(self, order_id: str) -> None:
        self.client.kite.cancel_order(variety=self.client.kite.VARIETY_REGULAR, order_id=order_id)
