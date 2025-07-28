"""
Simplified Configuration settings using Pydantic
"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Simplified application settings"""
    
    # Database Settings
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")
    DATABASE_NAME: str = Field(default="trading_system")
    MONGODB_TIMEOUT: int = Field(default=5)
    
    # Trading Settings
    INITIAL_BALANCE: float = Field(default=10000.0)
    RISK_PER_TRADE: float = Field(default=0.02)
    STOP_LOSS_PCT: float = Field(default=0.05)
    TARGET_PCT: float = Field(default=0.10)
    DAILY_TRADES_LIMIT: int = Field(default=50)
    MIN_CONFIDENCE: float = Field(default=50.0)
    
    # Margin and Leverage Settings
    MAX_LEVERAGE: float = Field(default=5.0)
    DEFAULT_LEVERAGE: float = Field(default=1.0)
    MAX_POSITION_SIZE: float = Field(default=1000.0)
    
    # Risk Management Settings
    MAX_PORTFOLIO_RISK: float = Field(default=0.15)  # 15% max portfolio risk
    
    # Trading Fee Settings
    TRADING_FEE_PCT: float = Field(default=0.001)  # 0.1% of margin
    EXIT_FEE_MULTIPLIER: float = Field(default=0.5)  # Exit fee is 50% of entry fee
    
    # System Intervals (in seconds)
    STRATEGY_EXECUTION_INTERVAL: int = Field(default=600)  # 10 minutes
    HISTORICAL_DATA_UPDATE_INTERVAL: int = Field(default=900)  # 15 minutes
    RISK_CHECK_INTERVAL: int = Field(default=60)  # 1 minute
    LIVE_PRICE_UPDATE: str = Field(default="realtime")
    
    # WebSocket Settings
    WEBSOCKET_PORT: int = Field(default=8765)
    WEBSOCKET_TIMEOUT: int = Field(default=30)
    
    # Email Notifications (FastAPI-Mail only)
    EMAIL_NOTIFICATIONS_ENABLED: bool = Field(default=True)
    FASTAPI_MAIL_USERNAME: str = Field(default="")
    FASTAPI_MAIL_PASSWORD: str = Field(default="")
    FASTAPI_MAIL_FROM: str = Field(default="")
    FASTAPI_MAIL_FROM_NAME: str = Field(default="Trading Bot")
    FASTAPI_MAIL_PORT: int = Field(default=587)
    FASTAPI_MAIL_SERVER: str = Field(default="smtp.gmail.com")
    FASTAPI_MAIL_STARTTLS: bool = Field(default=True)
    FASTAPI_MAIL_SSL_TLS: bool = Field(default=False)
    
    # Active Strategies
    STRATEGY_CLASSES: List[str] = Field(default=["EMAStrategy"])
    TRADING_SYMBOLS: List[str] = Field(default=["BTCUSD", "ETHUSD"])
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_trading_config() -> dict:
    """Get simplified trading configuration"""
    settings = get_settings()
    return {
        "initial_balance": settings.INITIAL_BALANCE,
        "risk_per_trade": settings.RISK_PER_TRADE,
        "stop_loss_pct": settings.STOP_LOSS_PCT,
        "target_pct": settings.TARGET_PCT,
        "daily_trades_limit": settings.DAILY_TRADES_LIMIT,
        "min_confidence": settings.MIN_CONFIDENCE,
        "max_leverage": settings.MAX_LEVERAGE,
        "default_leverage": settings.DEFAULT_LEVERAGE,
        "max_position_size": settings.MAX_POSITION_SIZE,
        "max_portfolio_risk": settings.MAX_PORTFOLIO_RISK,
        "trading_fee_pct": settings.TRADING_FEE_PCT,
        "exit_fee_multiplier": settings.EXIT_FEE_MULTIPLIER
    }


def get_system_intervals() -> dict:
    """Get system timing intervals"""
    settings = get_settings()
    return {
        "strategy_execution": settings.STRATEGY_EXECUTION_INTERVAL,
        "historical_data_update": settings.HISTORICAL_DATA_UPDATE_INTERVAL,
        "risk_check": settings.RISK_CHECK_INTERVAL,
        "live_price_update": settings.LIVE_PRICE_UPDATE
    }


def get_fastapi_mail_config() -> dict:
    """Get FastAPI-Mail config as dict"""
    settings = get_settings()
    return {
        "MAIL_USERNAME": settings.FASTAPI_MAIL_USERNAME,
        "MAIL_PASSWORD": settings.FASTAPI_MAIL_PASSWORD,
        "MAIL_FROM": settings.FASTAPI_MAIL_FROM,
        "MAIL_FROM_NAME": settings.FASTAPI_MAIL_FROM_NAME,
        "MAIL_PORT": settings.FASTAPI_MAIL_PORT,
        "MAIL_SERVER": settings.FASTAPI_MAIL_SERVER,
        "MAIL_STARTTLS": settings.FASTAPI_MAIL_STARTTLS,
        "MAIL_SSL_TLS": settings.FASTAPI_MAIL_SSL_TLS,
    } 