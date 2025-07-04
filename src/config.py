from pydantic_settings import BaseSettings
from typing import Dict, List, ClassVar
from functools import lru_cache
import os
from dataclasses import dataclass


class Settings(BaseSettings):
    """Application settings using Pydantic-settings"""
    
    # WebSocket Configuration
    WEBSOCKET_URL: str = "ws://localhost:8765"  # Local WebSocket server URL
    DELTA_WEBSOCKET_URL: str = "wss://socket.delta.exchange"  # Delta Exchange WebSocket URL
    HISTORICAL_URL: str = "https://api.india.delta.exchange/v2/history/candles"
    WEBSOCKET_TIMEOUT: int = 10  # Seconds to wait for WebSocket connection
    PRICE_UPDATE_INTERVAL: int = 10  # Seconds between price updates
    ANALYSIS_INTERVAL: int = 600  # Seconds between analysis updates (10 minutes)
    DEFAULT_SYMBOLS: List[str] = ["BTC-USD", "ETH-USD"]  # Default trading pairs
    POSITION_CHECK_INTERVAL: int = 10  # Seconds between position checks
    
    # Technical Analysis Configuration
    DEFAULT_RESOLUTION: str = "5m"
    DEFAULT_HISTORY_DAYS: int = 10
    DEFAULT_SYMBOL: str = "BTCUSD"
    DEFAULT_REFRESH_INTERVAL: int = 600  # 600 seconds = 10 minutes
    DEFAULT_ENABLE_BROKER: bool = True
    DEFAULT_ENABLE_LIVE_PRICE: bool = True
    SUPPORTED_RESOLUTIONS: List[str] = ["1m", "5m", "15m", "1h", "1d"]
    
    # Indicator Settings
    EMA_PERIODS: List[int] = [5, 15, 50]
    RSI_PERIOD: int = 14
    MACD_SETTINGS: Dict[str, int] = {
        "fast": 12,
        "slow": 26,
        "signal": 9
    }
    ATR_PERIOD: int = 14
    STOCH_PERIOD: int = 14
    
    # Additional Indicator Settings
    SUPERTREND_PERIOD: int = 10
    SUPERTREND_MULTIPLIER: float = 3.0
    ADX_PERIOD: int = 14
    ZSCORE_PERIOD: int = 20
    
    # UI Configuration
    BANNER_TITLE: str = "Crypto Price Tracker"
    BANNER_SUBTITLE: str = "WebSocket Monitor + Technical Analysis"
    PROGRESS_BAR_STYLE: str = "{l_bar}{bar}| {n_fmt}/{total_fmt}"
    
    # System Check Configuration
    SYSTEM_CHECK_TIMEOUT: int = 10
    
    # MongoDB Configuration
    MONGODB_URI: str = "mongodb://localhost:27017/"
    DATABASE_NAME: str = "trading_bot"
    MONGODB_TIMEOUT: int = 5
    
    # AI Strategy Configuration
    GOOGLE_API_KEY: str = "AIzaSyCK2n2AoIwXNTvdpEQMiGiwnYZ00-MRLqE"  # Add your Google AI API key here
    AI_MODEL_NAME: str = "gemini-2.0-flash"
    AI_TEMPERATURE: float = 0.0
    AI_MAX_RETRIES: int = 2
    
    # WebSocket Server Configuration (for web viewing)
    WEBSOCKET_SERVER_HOST: str = "localhost"
    WEBSOCKET_SERVER_PORT: int = 8765
    WEB_UPDATE_INTERVAL: int = 5  # seconds
    
    # Broker Configuration
    BROKER_INITIAL_BALANCE: float = 10000.0
    BROKER_MAX_POSITION_SIZE: float = 1000.0  # Max amount per position
    BROKER_RISK_PER_TRADE: float = 0.02  # 2% risk per trade
    BROKER_DAILY_TRADE_LIMIT: int = 5  # Max trades per day
    BROKER_STOP_LOSS_PCT: float = 0.01  # 1% stop loss
    BROKER_TARGET_PCT: float = 0.02  # 2% target (2:1 risk:reward)
    BROKER_MIN_CONFIDENCE: float = 60.0  # Minimum signal confidence for trade execution
    BROKER_UI_REFRESH_INTERVAL: int = 60  # Broker UI refresh interval in seconds (1 minute)
    BROKER_DEBUG_POSITION_MONITORING: bool = True  # Enable detailed position monitoring logs
    
    # Margin Trading Configuration
    BROKER_DEFAULT_LEVERAGE: float = 50.0  # Default leverage (50x)
    BROKER_MAX_LEVERAGE: float = 100.0  # Maximum leverage (100x)
    BROKER_TRADING_FEE_PCT: float = 0.02  # 2% trading fee on invested amount
    BROKER_MARGIN_CALL_THRESHOLD: float = 0.8  # Margin call at 80% of margin used
    BROKER_LIQUIDATION_THRESHOLD: float = 0.95  # Liquidation at 95% of margin used
    BROKER_MAX_HOLDING_HOURS: float = 48.0  # Maximum holding time in hours (48 hours)
    
    # WebSocket Configuration
    WEBSOCKET_HOST: ClassVar[str] = "0.0.0.0"
    WEBSOCKET_PORT: ClassVar[int] = 8765
    WEBSOCKET_UPDATE_INTERVAL: ClassVar[int] = 10  # seconds
    
    # Data Types for WebSocket Messages
    class WSMessageTypes:
        TRADE_LOGS: ClassVar[str] = "tradelogs"
        LIVE_PRICE: ClassVar[str] = "liveprice"
        ANALYSIS: ClassVar[str] = "analysis"
        POSITIONS: ClassVar[str] = "positions"
    
    # Position Update Thresholds
    POSITION_WARNING_THRESHOLD: ClassVar[float] = 0.8  # 80% of stop loss/target
    LIQUIDATION_WARNING_THRESHOLD: ClassVar[float] = 0.9  # 90% of liquidation price
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/trading_bot.log"
    
    class Config:
        env_prefix = "CRYPTO_"  # Environment variables should be prefixed with CRYPTO_
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 