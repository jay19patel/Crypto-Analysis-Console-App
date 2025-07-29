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
    
    # Core Trading Settings - Recommended Optimized Settings
    INITIAL_BALANCE: float = Field(default=17500.0)  # $15,000-20,000 recommended range (₹14.6L-16.7L)
    BALANCE_PER_TRADE_PCT: float = Field(default=0.15)  # 15% of balance per trade (optimized from 20%)
    DEFAULT_LEVERAGE: float = Field(default=30.0)  # 30x leverage (optimized from 50x for better risk management)
    MAX_LEVERAGE: float = Field(default=50.0)  # Keep max at 50x for flexibility
    DAILY_TRADES_LIMIT: int = Field(default=50)
    MIN_CONFIDENCE: float = Field(default=50.0)
    
    # Risk Management - Basic Settings
    STOP_LOSS_PCT: float = Field(default=0.05)  # 5% stop loss
    TARGET_PCT: float = Field(default=0.10)     # 10% target
    LIQUIDATION_BUFFER_PCT: float = Field(default=0.30)  # 30% buffer from liquidation for safety
    
    # Emergency Close Risk Thresholds (Configurable)
    EMERGENCY_CLOSE_MARGIN_PCT: float = Field(default=95.0)  # Emergency close at 95% margin usage
    EMERGENCY_CLOSE_LOSS_PCT: float = Field(default=15.0)    # Emergency close at 15% loss 
    EMERGENCY_CLOSE_TIME_HOURS: float = Field(default=48.0)  # Emergency close after 48 hours
    
    # Risk Level Thresholds
    CRITICAL_RISK_MARGIN_PCT: float = Field(default=90.0)    # Critical risk at 90% margin
    CRITICAL_RISK_LOSS_PCT: float = Field(default=12.0)      # Critical risk at 12% loss
    CRITICAL_RISK_TIME_HOURS: float = Field(default=36.0)    # Critical risk after 36 hours
    
    HIGH_RISK_MARGIN_PCT: float = Field(default=80.0)        # High risk at 80% margin
    HIGH_RISK_LOSS_PCT: float = Field(default=8.0)           # High risk at 8% loss
    HIGH_RISK_TIME_HOURS: float = Field(default=24.0)        # High risk after 24 hours
    
    MEDIUM_RISK_MARGIN_PCT: float = Field(default=70.0)      # Medium risk at 70% margin
    MEDIUM_RISK_LOSS_PCT: float = Field(default=5.0)         # Medium risk at 5% loss
    MEDIUM_RISK_TIME_HOURS: float = Field(default=12.0)      # Medium risk after 12 hours
    
    # Safe Position Sizing for Small Balance
    SAFE_BALANCE_PER_TRADE_PCT: float = Field(default=0.05)  # 5% of balance per trade for safety
    MAX_POSITIONS_OPEN: int = Field(default=2)               # Max 2 positions open simultaneously (optimized)
    HIGH_RISK_MARGIN_PCT: float = Field(default=85.0)        # Portfolio high risk threshold at 85% margin
    MAX_PORTFOLIO_RISK_PCT: float = Field(default=80.0)      # Maximum portfolio risk percentage (anti-overtrade)
    
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
    """Get clean trading configuration for algo trading system"""
    settings = get_settings()
    return {
        "initial_balance": settings.INITIAL_BALANCE,
        "balance_per_trade_pct": settings.BALANCE_PER_TRADE_PCT,  # 20% per trade (normal)
        "safe_balance_per_trade_pct": settings.SAFE_BALANCE_PER_TRADE_PCT,  # 5% per trade (safe mode)
        "default_leverage": settings.DEFAULT_LEVERAGE,  # 50x leverage
        "max_leverage": settings.MAX_LEVERAGE,
        "daily_trades_limit": settings.DAILY_TRADES_LIMIT,
        "min_confidence": settings.MIN_CONFIDENCE,
        "stop_loss_pct": settings.STOP_LOSS_PCT,
        "target_pct": settings.TARGET_PCT,
        "liquidation_buffer_pct": settings.LIQUIDATION_BUFFER_PCT,  # Liquidation safety buffer
        "trading_fee_pct": settings.TRADING_FEE_PCT,
        "exit_fee_multiplier": settings.EXIT_FEE_MULTIPLIER,
        "max_positions_open": settings.MAX_POSITIONS_OPEN,
        
        # Emergency Close Thresholds
        "emergency_close_margin_pct": settings.EMERGENCY_CLOSE_MARGIN_PCT,
        "emergency_close_loss_pct": settings.EMERGENCY_CLOSE_LOSS_PCT,
        "emergency_close_time_hours": settings.EMERGENCY_CLOSE_TIME_HOURS,
        
        # Risk Level Thresholds
        "critical_risk_margin_pct": settings.CRITICAL_RISK_MARGIN_PCT,
        "critical_risk_loss_pct": settings.CRITICAL_RISK_LOSS_PCT,
        "critical_risk_time_hours": settings.CRITICAL_RISK_TIME_HOURS,
        
        "high_risk_margin_pct": settings.HIGH_RISK_MARGIN_PCT,
        "high_risk_loss_pct": settings.HIGH_RISK_LOSS_PCT,
        "high_risk_time_hours": settings.HIGH_RISK_TIME_HOURS,
        
        "medium_risk_margin_pct": settings.MEDIUM_RISK_MARGIN_PCT,
        "medium_risk_loss_pct": settings.MEDIUM_RISK_LOSS_PCT,
        "medium_risk_time_hours": settings.MEDIUM_RISK_TIME_HOURS,
        
        "max_portfolio_risk_pct": settings.MAX_PORTFOLIO_RISK_PCT,
        "high_risk_margin_pct": settings.HIGH_RISK_MARGIN_PCT
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