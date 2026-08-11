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
    max_daily_loss: float = 10000.0
    max_trade_loss: float = 2000.0
    max_open_positions: int = 2
    risk_reward_ratio: float = 2.0

    # Signal thresholds (see SRD §6, §8)
    ce_signal_score_threshold: float = 70.0
    pe_signal_score_threshold: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
