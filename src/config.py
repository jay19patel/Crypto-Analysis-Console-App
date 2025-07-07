from pydantic_settings import BaseSettings
from typing import Dict, List, ClassVar
from functools import lru_cache


class Settings(BaseSettings):
    """Clean Application Settings for Optimized Trading System"""
    
    # Core Trading Configuration
    DEFAULT_SYMBOLS: List[str] = ["BTC-USD", "ETH-USD"]
    DEFAULT_SYMBOL: str = "BTCUSD"
    
    # Real-time Update Intervals (in seconds)
    LIVE_PRICE_UPDATE_INTERVAL: int = 1    # Live price every 1 second
    POSITION_UPDATE_INTERVAL: int = 1      # Position updates every 1 second
    ACCOUNT_UPDATE_INTERVAL: int = 1       # Account updates every 1 second
    STRATEGY_CHECK_INTERVAL: int = 1       # Strategy checks every 1 second
    RISK_CHECK_INTERVAL: int = 1           # Risk management every 1 second
    
    # WebSocket Configuration
    DELTA_WEBSOCKET_URL: str = "wss://socket.delta.exchange"
    WEBSOCKET_TIMEOUT: int = 10
    
    # MongoDB Configuration
    MONGODB_URI: str = "mongodb://localhost:27017/"
    DATABASE_NAME: str = "trading_bot"
    MONGODB_TIMEOUT: int = 5
    
    # Broker Configuration
    BROKER_INITIAL_BALANCE: float = 10000.0
    BROKER_MAX_POSITION_SIZE: float = 1000.0
    BROKER_RISK_PER_TRADE: float = 0.02     # 2% risk per trade
    BROKER_DAILY_TRADE_LIMIT: int = 50      # Max trades per day
    BROKER_STOP_LOSS_PCT: float = 0.01      # 1% stop loss
    BROKER_TARGET_PCT: float = 0.02         # 2% target
    BROKER_MIN_CONFIDENCE: float = 60.0     # Minimum signal confidence
    
    # Margin Trading Configuration
    BROKER_DEFAULT_LEVERAGE: float = 50.0
    BROKER_MAX_LEVERAGE: float = 100.0
    BROKER_TRADING_FEE_PCT: float = 0.02    # 2% trading fee
    BROKER_MARGIN_CALL_THRESHOLD: float = 0.8
    BROKER_LIQUIDATION_THRESHOLD: float = 0.95
    BROKER_MAX_HOLDING_HOURS: float = 48.0
    
    # Strategy Configuration
    STRATEGY_BUY_PROBABILITY: float = 0.10   # 10% chance to BUY
    STRATEGY_SELL_PROBABILITY: float = 0.10  # 10% chance to SELL
    
    # Risk Management Configuration
    RISK_MAX_PORTFOLIO_RISK: float = 0.15   # 15% max portfolio risk
    RISK_MAX_POSITION_RISK: float = 0.05    # 5% max position risk
    RISK_CORRELATION_THRESHOLD: float = 0.7  # Max correlation between positions
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/trading_bot.log"
    
    class Config:
        env_prefix = "CRYPTO_"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 