"""
Configuration settings using Pydantic
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings using Pydantic"""
    
    # Database Settings
    MONGODB_URI: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URI")
    DATABASE_NAME: str = Field(default="trading_system", description="Database name")
    MONGODB_TIMEOUT: int = Field(default=5, description="MongoDB connection timeout in seconds")
    
    # Broker Settings
    BROKER_INITIAL_BALANCE: float = Field(default=10000.0, description="Initial account balance")
    BROKER_MAX_LEVERAGE: float = Field(default=5.0, description="Maximum leverage allowed")
    BROKER_TRADING_FEE_PCT: float = Field(default=0.001, description="Trading fee percentage (0.1%)")
    BROKER_MIN_CONFIDENCE: float = Field(default=50.0, description="Minimum confidence for trade execution")
    BROKER_STOP_LOSS_PCT: float = Field(default=0.05, description="Default stop loss percentage (5%)")
    BROKER_TARGET_PCT: float = Field(default=0.10, description="Default target percentage (10%)")
    BROKER_MAX_HOLDING_HOURS: int = Field(default=48, description="Maximum position holding time in hours")
    
    # Risk Management Settings
    RISK_MAX_PORTFOLIO_RISK: float = Field(default=0.15, description="Maximum portfolio risk (15%)")
    RISK_MAX_POSITION_RISK: float = Field(default=0.05, description="Maximum position risk (5%)")
    RISK_CORRELATION_THRESHOLD: float = Field(default=0.7, description="Correlation threshold for risk")
    RISK_CHECK_INTERVAL: int = Field(default=5, description="Risk check interval in seconds")
    
    # Trading Settings
    DAILY_TRADES_LIMIT: int = Field(default=50, description="Daily trade limit")
    MAX_POSITION_SIZE: float = Field(default=1000.0, description="Maximum position size")
    RISK_PER_TRADE: float = Field(default=0.02, description="Risk per trade (2%)")
    
    # Notification Settings
    EMAIL_ENABLED: bool = Field(default=True, description="Enable email notifications")
    EMAIL_HOST: str = Field(default="smtp.gmail.com", description="SMTP host")
    EMAIL_PORT: int = Field(default=587, description="SMTP port")
    EMAIL_USERNAME: str = Field(default="", description="Email username")
    EMAIL_PASSWORD: str = Field(default="", description="Email password")
    EMAIL_FROM: str = Field(default="", description="From email address")
    EMAIL_TO: str = Field(default="", description="To email address")
    
    # System Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: str = Field(default="logs/trading_system.log", description="Log file path")
    
    # Dummy Data Settings
    DUMMY_SYMBOLS: List[str] = Field(
        default=["BTC-USD", "ETH-USD", "AAPL", "GOOGL", "TSLA"],
        description="Dummy trading symbols"
    )
    DUMMY_PRICE_CHANGE_RANGE: float = Field(default=0.02, description="Dummy price change range (±2%)")
    TRADING_LOOP_INTERVAL: int = Field(default=5, description="Trading loop interval in seconds")
    
    # Performance Settings
    MAX_BACKGROUND_WORKERS: int = Field(default=4, description="Maximum background workers")
    TASK_QUEUE_SIZE: int = Field(default=1000, description="Task queue size")
    PRICE_UPDATE_INTERVAL: int = Field(default=1, description="Price update interval in seconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get application settings singleton"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenience functions for common settings
def get_mongodb_uri() -> str:
    """Get MongoDB URI"""
    return get_settings().MONGODB_URI


def get_database_name() -> str:
    """Get database name"""
    return get_settings().DATABASE_NAME


def get_broker_settings() -> dict:
    """Get broker settings"""
    settings = get_settings()
    return {
        "initial_balance": settings.BROKER_INITIAL_BALANCE,
        "max_leverage": settings.BROKER_MAX_LEVERAGE,
        "trading_fee_pct": settings.BROKER_TRADING_FEE_PCT,
        "min_confidence": settings.BROKER_MIN_CONFIDENCE,
        "stop_loss_pct": settings.BROKER_STOP_LOSS_PCT,
        "target_pct": settings.BROKER_TARGET_PCT,
        "max_holding_hours": settings.BROKER_MAX_HOLDING_HOURS,
        "daily_trades_limit": settings.DAILY_TRADES_LIMIT,
        "max_position_size": settings.MAX_POSITION_SIZE,
        "risk_per_trade": settings.RISK_PER_TRADE
    }


def get_risk_settings() -> dict:
    """Get risk management settings"""
    settings = get_settings()
    return {
        "max_portfolio_risk": settings.RISK_MAX_PORTFOLIO_RISK,
        "max_position_risk": settings.RISK_MAX_POSITION_RISK,
        "correlation_threshold": settings.RISK_CORRELATION_THRESHOLD,
        "check_interval": settings.RISK_CHECK_INTERVAL
    }


def get_dummy_settings() -> dict:
    """Get dummy data settings"""
    settings = get_settings()
    return {
        "symbols": settings.DUMMY_SYMBOLS,
        "price_change_range": settings.DUMMY_PRICE_CHANGE_RANGE,
        "trading_loop_interval": settings.TRADING_LOOP_INTERVAL
    } 