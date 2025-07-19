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
    """Market data structure"""
    symbol: str
    price: float
    volume: float
    change: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    high_24h: float
    low_24h: float
    bid: float
    ask: float
    
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