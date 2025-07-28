"""
Trading system models for account and position management
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class PositionType(Enum):
    """Position type enumeration"""
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(Enum):
    """Position status enumeration"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    PENDING = "PENDING"


@dataclass
class Account:
    """Trading account model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Trading Account"
    initial_balance: float = 10000.0
    current_balance: float = 10000.0
    daily_trades_limit: int = 50
    max_position_size: float = 1000.0  # Will be updated from config
    risk_per_trade: float = 0.02
    max_leverage: float = 5.0  # Will be updated from config
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    realized_pnl: float = 0.0
    daily_trades_count: int = 0
    total_margin_used: float = 0.0
    brokerage_charges: float = 0.0
    last_trade_date: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert account to dictionary"""
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
            "realized_pnl": self.realized_pnl,
            "daily_trades_count": self.daily_trades_count,
            "total_margin_used": self.total_margin_used,
            "brokerage_charges": self.brokerage_charges,
            "last_trade_date": self.last_trade_date,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """Create account from dictionary"""
        # Filter out MongoDB-specific fields
        filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
        
        account = cls()
        for key, value in filtered_data.items():
            if hasattr(account, key):
                setattr(account, key, value)
        
        return account


@dataclass
class Position:
    """Trading position model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    position_type: PositionType = PositionType.LONG
    status: PositionStatus = PositionStatus.OPEN
    entry_price: float = 0.0
    exit_price: Optional[float] = None
    quantity: float = 0.0
    invested_amount: float = 0.0
    strategy_name: str = ""
    leverage: float = 1.0  # Will be updated from config
    margin_used: float = 0.0
    trading_fee: float = 0.0
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    exit_time: Optional[datetime] = None
    notes: Optional[str] = None
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate P&L for the position"""
        if self.position_type == PositionType.LONG:
            self.pnl = (current_price - self.entry_price) * self.quantity
        else:
            self.pnl = (self.entry_price - current_price) * self.quantity
        
        if self.invested_amount > 0:
            self.pnl_percentage = (self.pnl / self.invested_amount) * 100
        else:
            self.pnl_percentage = 0.0
        
        return self.pnl
    
    def calculate_margin_usage(self, current_price: float) -> float:
        """Calculate current margin usage percentage"""
        if self.margin_used <= 0:
            return 0.0
        
        current_value = current_price * self.quantity
        return (current_value / self.margin_used) * 100
    
    def close_position(self, exit_price: float, reason: str = "Manual Close"):
        """Close the position"""
        self.exit_price = exit_price
        self.exit_time = datetime.now(timezone.utc)
        self.status = PositionStatus.CLOSED
        self.notes = reason
        
        # Calculate final P&L
        self.calculate_pnl(exit_price)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert position to dictionary"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "position_type": self.position_type.value,
            "status": self.status.value,
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
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "notes": self.notes,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create position from dictionary"""
        # Filter out MongoDB-specific fields
        filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
        
        position = cls()
        
        # Handle enum fields
        if 'position_type' in filtered_data:
            position.position_type = PositionType(filtered_data['position_type'])
        
        if 'status' in filtered_data:
            position.status = PositionStatus(filtered_data['status'])
        
        # Handle datetime fields
        if 'entry_time' in filtered_data and filtered_data['entry_time']:
            if isinstance(filtered_data['entry_time'], str):
                position.entry_time = datetime.fromisoformat(filtered_data['entry_time'].replace('Z', '+00:00'))
            else:
                position.entry_time = filtered_data['entry_time']
        
        if 'exit_time' in filtered_data and filtered_data['exit_time']:
            if isinstance(filtered_data['exit_time'], str):
                position.exit_time = datetime.fromisoformat(filtered_data['exit_time'].replace('Z', '+00:00'))
            else:
                position.exit_time = filtered_data['exit_time']
        
        # Set other fields
        for key, value in filtered_data.items():
            if hasattr(position, key) and key not in ['position_type', 'status', 'entry_time', 'exit_time']:
                setattr(position, key, value)
        
        return position 