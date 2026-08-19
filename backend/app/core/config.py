from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Bank Nifty Intraday Trading Platform"
    environment: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://bn_user:bn_password@localhost:5432/banknifty"
    db_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # RabbitMQ
    rabbitmq_url: str = "amqp://bn_user:bn_password@localhost:5672/"

    # Kite Connect
    kite_api_key: str = Field(default="")
    kite_api_secret: str = Field(default="")
    kite_access_token: str = Field(default="")
    kite_redirect_url: str = "http://localhost:8000/api/v1/kite/callback"

    # Trading
    trading_symbol: str = "NIFTY BANK"  # NSE spot index name
    trading_exchange: str = "NFO"
    nfo_underlying: str = "BANKNIFTY"  # NFO futures/options `name` field differs from the spot symbol
    paper_trading: bool = True
    paper_trading_capital: float = 100000.0
    risk_per_trade_pct: float = 3.0
    max_daily_loss: float = 10000.0
    max_trade_loss: float = 4000.0
    max_open_positions: int = 2
    risk_reward_ratio: float = 2.0
    # Floor on (target - entry) / (entry - stop_loss). The S/R cap in
    # sr_capped_target() can crush the target down to almost nothing when
    # spot is already sitting at the level - this rejects those trades
    # instead of opening a full-risk, near-zero-reward position.
    min_reward_risk_ratio: float = 1.5

    # Estimated round-trip transaction costs (SEE app/services/risk_management/costs.py).
    # `charges` was never being populated before this, so every historical
    # P&L figure was gross - a 3-day paper sample with 77 trades and a 17%
    # win rate looked net positive (+3,544.50) on gross P&L but flips
    # negative (~-2,230) once these are applied, because ~59 of those
    # trades were small trailing-stop exits whose gross P&L (avg -26) is
    # dwarfed by a ~75 flat round-trip cost. Defaults are commonly-quoted
    # Zerodha/Kite F&O options rates - check against a real contract note
    # before relying on this for live capital decisions.
    brokerage_per_order: float = 20.0
    stt_pct_on_sell: float = 0.001  # STT on options: 0.1% of sell-side premium turnover
    exchange_txn_pct: float = 0.00035  # NSE F&O transaction charge, both legs
    stamp_duty_pct: float = 0.00003  # stamp duty, buy-side turnover only
    gst_pct: float = 0.18  # GST on brokerage + exchange transaction charges
    # Reject an entry unless its target reward (at 1 lot) is at least this
    # many multiples of the estimated round-trip cost for that lot - a
    # trade with a "good enough" reward:risk ratio can still be a bad bet
    # if the edge it's chasing is smaller than the toll every trade pays
    # regardless of outcome.
    min_reward_to_cost_ratio: float = 3.0

    # Live loop
    live_loop_enabled: bool = False
    live_loop_interval_seconds: int = 10
    eod_square_off_time: str = "15:38"  # HH:MM, IST - force-close every open paper position at/after this time
    # Blocks re-entering the same strike/side for this long after it last
    # exited (any reason) - a choppy spot near a support/resistance level
    # can re-trigger the same signal seconds after a stop-out, re-entering
    # into the same whipsaw repeatedly (49 trades / 10% win rate on one
    # session - see live trading notes 2026-08-13).
    reentry_cooldown_seconds: int = 300

    # Signal thresholds (see SRD §6, §8)
    ce_signal_score_threshold: float = 70.0
    pe_signal_score_threshold: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
