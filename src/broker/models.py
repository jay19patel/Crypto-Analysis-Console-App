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


class OrderType(Enum):
    """Order type enumeration"""
    BUY = "BUY"
    SELL = "SELL"
    STOP_LOSS = "STOP_LOSS" 
    TARGET = "TARGET"
    PYRAMID_ADD = "PYRAMID_ADD"
    TRAILING_CLOSE = "TRAILING_CLOSE"


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass  
class Order:
    """Trading order model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    position_id: str = ""
    symbol: str = ""
    order_type: OrderType = OrderType.BUY
    status: OrderStatus = OrderStatus.PENDING
    price: float = 0.0
    quantity: float = 0.0
    executed_price: Optional[float] = None
    executed_quantity: float = 0.0
    leverage: float = 1.0
    margin_used: float = 0.0
    trading_fee: float = 0.0
    strategy_name: str = ""
    confidence: float = 100.0
    order_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time: Optional[datetime] = None
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert order to dictionary"""
        return {
            "id": self.id,
            "position_id": self.position_id,
            "symbol": self.symbol,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "price": self.price,
            "quantity": self.quantity,
            "executed_price": self.executed_price,
            "executed_quantity": self.executed_quantity,
            "leverage": self.leverage,
            "margin_used": self.margin_used,
            "trading_fee": self.trading_fee,
            "strategy_name": self.strategy_name,
            "confidence": self.confidence,
            "order_time": self.order_time.isoformat() if self.order_time else None,
            "execution_time": self.execution_time.isoformat() if self.execution_time else None,
            "notes": self.notes,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """Create order from dictionary"""
        filtered_data = {k: v for k, v in data.items() if not k.startswith('_')}
        
        order = cls()
        
        # Handle enum fields
        if 'order_type' in filtered_data:
            order.order_type = OrderType(filtered_data['order_type'])
        
        if 'status' in filtered_data:
            order.status = OrderStatus(filtered_data['status'])
        
        # Handle datetime fields
        if 'order_time' in filtered_data and filtered_data['order_time']:
            if isinstance(filtered_data['order_time'], str):
                order.order_time = datetime.fromisoformat(filtered_data['order_time'].replace('Z', '+00:00'))
            else:
                order.order_time = filtered_data['order_time']
        
        if 'execution_time' in filtered_data and filtered_data['execution_time']:
            if isinstance(filtered_data['execution_time'], str):
                order.execution_time = datetime.fromisoformat(filtered_data['execution_time'].replace('Z', '+00:00'))
            else:
                order.execution_time = filtered_data['execution_time']
        
        # Set other fields
        for key, value in filtered_data.items():
            if hasattr(order, key) and key not in ['order_type', 'status', 'order_time', 'execution_time']:
                setattr(order, key, value)
        
        return order


@dataclass
class Account:
    """Trading account model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Trading Account"
    initial_balance: float = 10000.0
    current_balance: float = 10000.0
    daily_trades_limit: int = 50
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
    
    # Pyramiding support
    original_quantity: float = 0.0  # Original position size
    total_quantity: float = 0.0  # Total quantity including pyramids
    average_entry_price: float = 0.0  # Average entry price across all adds
    pyramid_count: int = 0  # Number of times position was added to
    
    # Trailing support
    trailing_count: int = 0  # Number of times position was partially closed in trailing
    remaining_quantity: float = 0.0  # Remaining quantity after partial closures
    realized_pnl: float = 0.0  # Realized PnL from partial closures
    unrealized_pnl: float = 0.0  # Unrealized PnL on remaining position
    average_exit_price: float = 0.0  # Average exit price for partial closures
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate P&L for the position including pyramiding and trailing"""
        # Calculate unrealized PnL on remaining quantity
        effective_quantity = self.remaining_quantity if self.remaining_quantity > 0 else self.total_quantity
        effective_entry_price = self.average_entry_price if self.average_entry_price > 0 else self.entry_price
        
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (current_price - effective_entry_price) * effective_quantity
        else:
            self.unrealized_pnl = (effective_entry_price - current_price) * effective_quantity
        
        # Total PnL = Realized PnL + Unrealized PnL
        self.pnl = self.realized_pnl + self.unrealized_pnl
        
        if self.invested_amount > 0:
            self.pnl_percentage = (self.pnl / self.invested_amount) * 100
        else:
            self.pnl_percentage = 0.0
        
        return self.pnl
    
    def calculate_margin_usage(self, current_price: float, account_balance: float = None) -> float:
        """Calculate pure margin usage percentage (without PnL impact)
        
        FIXED: Previously was incorrectly adding PnL losses to margin usage.
        Now returns pure margin usage only. PnL risk is handled separately at portfolio level.
        """
        if self.margin_used <= 0:
            return 0.0
        
        # Pure margin calculation: Margin used as percentage of account balance
        if account_balance and account_balance > 0:
            pure_margin_pct = (self.margin_used / account_balance) * 100
            return min(pure_margin_pct, 100.0)
        
        # Fallback: If no account balance, return conservative estimate
        return 50.0  # Conservative 50% usage estimate
    
    def calculate_effective_risk(self, current_price: float, account_balance: float = None) -> dict:
        """Calculate comprehensive position risk including margin + PnL impact
        
        This method provides both pure margin usage and PnL risk separately
        for better risk management decisions.
        """
        if account_balance is None or account_balance <= 0:
            return {
                "pure_margin_usage": 50.0,
                "pnl_risk": 0.0,
                "combined_risk": 50.0,
                "risk_components": {
                    "margin": 50.0,
                    "pnl_impact": 0.0
                }
            }
        
        # Pure margin usage (what we actually borrowed)
        pure_margin_usage = (self.margin_used / account_balance) * 100
        
        # PnL risk (how much we could lose as % of account)
        unrealized_pnl = self.calculate_pnl(current_price)
        pnl_risk = (abs(unrealized_pnl) / account_balance) * 100 if unrealized_pnl < 0 else 0.0
        
        # Combined risk (for comprehensive risk assessment)
        combined_risk = min(pure_margin_usage + (pnl_risk * 0.3), 100.0)  # PnL gets 30% weight
        
        return {
            "pure_margin_usage": min(pure_margin_usage, 100.0),
            "pnl_risk": pnl_risk,
            "combined_risk": combined_risk,
            "pnl_amount": unrealized_pnl,
            "risk_components": {
                "margin": pure_margin_usage,
                "pnl_impact": pnl_risk
            }
        }
    
    def add_to_position(self, add_quantity: float, add_price: float, add_margin: float):
        """Add to position (pyramiding)"""
        if self.original_quantity == 0.0:
            self.original_quantity = self.quantity
            self.total_quantity = self.quantity
            self.average_entry_price = self.entry_price
            self.remaining_quantity = self.quantity
        
        # Update quantities
        old_total = self.total_quantity
        self.total_quantity += add_quantity
        self.quantity = self.total_quantity
        self.remaining_quantity = self.total_quantity
        
        # Calculate new average entry price
        total_investment = (old_total * self.average_entry_price) + (add_quantity * add_price)
        self.average_entry_price = total_investment / self.total_quantity
        self.entry_price = self.average_entry_price  # Update main entry price
        
        # Update margin
        self.margin_used += add_margin
        self.invested_amount += add_quantity * add_price / self.leverage
        
        # Increment pyramid count
        self.pyramid_count += 1
        
        self.notes = f"Added {add_quantity} at ${add_price:.2f} (Pyramid #{self.pyramid_count})"

    def partial_close_position(self, close_quantity: float, exit_price: float, reason: str = "Trailing"):
        """Partially close position (trailing)"""
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = self.total_quantity if self.total_quantity > 0 else self.quantity
        
        # Calculate realized PnL for this partial close
        effective_entry_price = self.average_entry_price if self.average_entry_price > 0 else self.entry_price
        
        if self.position_type == PositionType.LONG:
            partial_pnl = (exit_price - effective_entry_price) * close_quantity
        else:
            partial_pnl = (effective_entry_price - exit_price) * close_quantity
        
        # Update realized PnL
        self.realized_pnl += partial_pnl
        
        # Update average exit price
        if self.trailing_count == 0:
            self.average_exit_price = exit_price
        else:
            total_closed = (self.total_quantity - self.remaining_quantity) + close_quantity
            previous_closed = self.total_quantity - self.remaining_quantity
            self.average_exit_price = ((previous_closed * self.average_exit_price) + (close_quantity * exit_price)) / total_closed
        
        # Update remaining quantity
        self.remaining_quantity -= close_quantity
        self.quantity = self.remaining_quantity
        
        # Increment trailing count
        self.trailing_count += 1
        
        # Update notes
        if self.notes:
            self.notes += f" | Trailing #{self.trailing_count}: Sold {close_quantity} at ${exit_price:.2f}"
        else:
            self.notes = f"Trailing #{self.trailing_count}: Sold {close_quantity} at ${exit_price:.2f}"
        
        # If position is fully closed
        if self.remaining_quantity <= 0:
            self.close_position(exit_price, f"Fully closed via trailing ({reason})")

    def close_position(self, exit_price: float, reason: str = "Manual Close"):
        """Close the position"""
        self.exit_price = exit_price
        self.exit_time = datetime.now(timezone.utc)
        self.status = PositionStatus.CLOSED
        self.notes = reason
        
        # If position was never partially closed, do full calculation
        if self.remaining_quantity == 0.0:
            self.remaining_quantity = self.total_quantity if self.total_quantity > 0 else self.quantity
        
        # Calculate final P&L on any remaining quantity
        if self.remaining_quantity > 0:
            effective_entry_price = self.average_entry_price if self.average_entry_price > 0 else self.entry_price
            
            if self.position_type == PositionType.LONG:
                final_pnl = (exit_price - effective_entry_price) * self.remaining_quantity
            else:
                final_pnl = (effective_entry_price - exit_price) * self.remaining_quantity
            
            self.realized_pnl += final_pnl
            
        self.pnl = self.realized_pnl
        self.unrealized_pnl = 0.0
        self.remaining_quantity = 0.0
    
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
            # Pyramiding fields
            "original_quantity": self.original_quantity,
            "total_quantity": self.total_quantity,
            "average_entry_price": self.average_entry_price,
            "pyramid_count": self.pyramid_count,
            # Trailing fields
            "trailing_count": self.trailing_count,
            "remaining_quantity": self.remaining_quantity,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "average_exit_price": self.average_exit_price,
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