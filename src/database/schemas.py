from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


class TradingSignal(BaseModel):
    """Trading signal with additional metadata"""
    signal: SignalType
    symbol: str
    confidence: float = Field(ge=0.0, le=100.0)
    strategy_name: str
    price: float
    quantity: float = 0.01
    leverage: float = 1.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MarketData(BaseModel):
    """Market data structure (expanded)"""
    price: float
    mark_price: float = None
    spot_price: float = None
    volume: float = None
    turnover: float = None
    turnover_usd: float = None
    high: float = None
    low: float = None
    open: float = None
    close: float = None
    open_interest: float = None
    oi_value: float = None
    oi_contracts: float = None
    oi_value_usd: float = None
    oi_change_usd_6h: float = None
    funding_rate: float = None
    mark_basis: float = None
    mark_change_24h: float = None
    underlying_asset_symbol: str = None
    description: str = None
    initial_margin: float = None
    tick_size: float = None
    price_band_lower: float = None
    price_band_upper: float = None
    best_bid: float = None
    best_ask: float = None
    bid_size: float = None
    ask_size: float = None
    mark_iv: float = None
    size: float = None
    symbol: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StrategyStats(BaseModel):
    """Strategy statistics"""
    name: str
    symbol: str
    total_signals: int
    signal_distribution: Dict[str, int]
    last_signal: str
    price_history_length: int
    win_rate: float = 0.0
    total_pnl: float = 0.0


class StrategyResult(BaseModel):
    """Result from strategy execution"""
    strategy_name: str
    symbol: str
    signal: TradingSignal
    execution_time: float
    success: bool
    error_message: Optional[str] = None


class StrategyManagerResult(BaseModel):
    """Final result from strategy manager"""
    selected_signal: TradingSignal
    all_signals: List[TradingSignal]
    strategy_results: List[StrategyResult]
    execution_timestamp: datetime = Field(default_factory=lambda: datetime.now())
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TradeRequest(BaseModel):
    """Trade request model"""
    symbol: str
    signal: SignalType
    price: float
    quantity: float
    leverage: float = 1.0
    strategy_name: str
    confidence: float = Field(ge=0.0, le=100.0)
    id: Optional[str] = None
    position_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SystemStats(BaseModel):
    """System statistics"""
    trades_executed: int = 0
    trades_successful: int = 0
    trades_failed: int = 0
    total_pnl: float = 0.0
    signals_generated: int = 0
    price_updates: int = 0
    strategies_executed: int = 0
    system_running: bool = False
    price_thread_alive: bool = False
    strategy_thread_alive: bool = False
    active_symbols: int = 0 


class NotificationStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"

class NotificationLog(BaseModel):
    """Schema for logging notifications sent via email, with status"""
    type: str
    priority: str
    title: str
    message: str
    data: Dict[str, Any] = {}
    timestamp: datetime
    user_id: Optional[str] = None
    trade_id: Optional[str] = None
    position_id: Optional[str] = None
    symbol: Optional[str] = None
    price: Optional[float] = None
    pnl: Optional[float] = None
    status: NotificationStatus
    error: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        } 