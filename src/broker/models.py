"""
Broker Models
Simple data models for trading account and positions
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class PositionType(Enum):
    """Position type"""
    LONG = "long"
    SHORT = "short"


class PositionStatus(Enum):
    """Position status"""
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"


@dataclass
class Account:
    """Trading account model"""
    id: str = ""
    name: str = ""
    initial_balance: float = 0.0
    current_balance: float = 0.0
    daily_trades_limit: int = 50
    max_position_size: float = 1000.0
    risk_per_trade: float = 0.02
    max_leverage: float = 5.0
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    total_loss: float = 0.0
    daily_trades_count: int = 0
    total_margin_used: float = 0.0
    brokerage_charges: float = 0.0
    last_trade_date: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "daily_trades_limit": self.daily_trades_limit,
            "max_position_size": self.max_position_size,
            "risk_per_trade": self.risk_per_trade,
            "max_leverage": self.max_leverage,
            "total_trades": self.total_trades,
            "profitable_trades": self.profitable_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "total_profit": self.total_profit,
            "total_loss": self.total_loss,
            "daily_trades_count": self.daily_trades_count,
            "total_margin_used": self.total_margin_used,
            "brokerage_charges": self.brokerage_charges,
            "last_trade_date": self.last_trade_date
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class Position:
    """Trading position model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    position_type: PositionType = PositionType.LONG
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    invested_amount: float = 0.0
    strategy_name: str = ""
    leverage: float = 1.0
    margin_used: float = 0.0
    trading_fee: float = 0.0
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exit_time: Optional[datetime] = None
    notes: str = ""
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate PnL based on current price"""
        if self.position_type == PositionType.LONG:
            self.pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.pnl = (self.entry_price - current_price) * self.quantity
        
        # Calculate percentage
        if self.invested_amount > 0:
            self.pnl_percentage = (self.pnl / self.invested_amount) * 100
        else:
            self.pnl_percentage = 0.0
        
        return self.pnl
    
    def calculate_margin_usage(self, current_price: float) -> float:
        """Calculate margin usage percentage"""
        if self.leverage <= 1 or self.margin_used <= 0:
            return 0.0
        
        current_value = current_price * self.quantity
        required_margin = current_value / self.leverage
        return (required_margin / self.margin_used) * 100
    
    def close_position(self, exit_price: float):
        """Close position"""
        self.exit_price = exit_price
        self.exit_time = datetime.now(timezone.utc)
        self.status = PositionStatus.CLOSED
        
        # Calculate final PnL
        self.calculate_pnl(exit_price)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "position_type": self.position_type.value,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "invested_amount": self.invested_amount,
            "strategy_name": self.strategy_name,
            "leverage": self.leverage,
            "margin_used": self.margin_used,
            "trading_fee": self.trading_fee,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "pnl": self.pnl,
            "pnl_percentage": self.pnl_percentage,
            "status": self.status.value,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create from dictionary"""
        # Handle enum conversions
        if "position_type" in data:
            data["position_type"] = PositionType(data["position_type"])
        if "status" in data:
            data["status"] = PositionStatus(data["status"])
        
        # Handle datetime conversions
        if "entry_time" in data and data["entry_time"]:
            data["entry_time"] = datetime.fromisoformat(data["entry_time"])
        if "exit_time" in data and data["exit_time"]:
            data["exit_time"] = datetime.fromisoformat(data["exit_time"])
        
        return cls(**data) 