from pydantic_settings import BaseSettings
from typing import Dict, List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings using Pydantic-settings"""
    
    # WebSocket Configuration
    WEBSOCKET_URL: str = "wss://socket.india.delta.exchange"
    HISTORICAL_URL: str = "https://api.india.delta.exchange/v2/history/candles"
    WEBSOCKET_TIMEOUT: int = 10
    PRICE_UPDATE_INTERVAL: int = 5  # seconds
    DEFAULT_SYMBOLS: List[str] = ["BTCUSD", "ETHUSD"]
    
    # Technical Analysis Configuration
    DEFAULT_RESOLUTION: str = "5m"
    DEFAULT_HISTORY_DAYS: int = 10
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
    MONGODB_DATABASE: str = "crypto_analysis"
    MONGODB_COLLECTION: str = "analysis_results"
    MONGODB_TIMEOUT: int = 5
    
    # AI Strategy Configuration
    GOOGLE_API_KEY: str = "AIzaSyCK2n2AoIwXNTvdpEQMiGiwnYZ00-MRLqE"  # Add your Google AI API key here
    AI_MODEL_NAME: str = "gemini-2.0-flash"
    AI_TEMPERATURE: float = 0.0
    AI_MAX_RETRIES: int = 2
    
    class Config:
        env_prefix = "CRYPTO_"  # Environment variables should be prefixed with CRYPTO_
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings() 