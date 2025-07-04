from pydantic_settings import BaseSettings
from typing import Dict, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings using Pydantic-settings"""
    
    # WebSocket Configuration
    WEBSOCKET_URL: str = "wss://socket.india.delta.exchange"
    HISTORICAL_URL: str = "https://api.india.delta.exchange/v2/history/candles"
    WEBSOCKET_TIMEOUT: int = 10
    PRICE_UPDATE_INTERVAL: int = 10  # seconds
    DEFAULT_SYMBOLS: List[str] = ["BTCUSD", "ETHUSD"]
    
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
    MONGODB_URL: str = "mongodb+srv://justj:justjay19@cluster0.fsgzjrl.mongodb.net/"
    # MONGODB_URL: str = "mongodb://localhost:27017/"
    MONGODB_DATABASE: str = "crypto_analysis"
    MONGODB_COLLECTION: str = "analysis_results"
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
    
    class Config:
        env_prefix = "CRYPTO_"  # Environment variables should be prefixed with CRYPTO_
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 