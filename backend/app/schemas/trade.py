from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.trade_execution import TradeMode, TradeStatus


class TradeExecutionOut(BaseModel):
    order_id: UUID
    mode: TradeMode
    status: TradeStatus
    symbol: str
    option_type: str
    quantity: int
    entry_time: datetime
    entry_price: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    pnl: float | None = None
    charges: float = 0.0
    exit_reason: str | None = None

    class Config:
        from_attributes = True


class DailyReport(BaseModel):
    report_date: str
    total_trades: int
    win_rate: float
    net_profit: float
    charges: float
    max_drawdown: float


class MonthlyReport(BaseModel):
    month: str
    total_pnl: float
    win_rate: float
    max_drawdown: float
    roi: float
