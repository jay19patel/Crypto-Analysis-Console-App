"""
Data models for broker system
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
import uuid

class PositionType(Enum):
    """Position types"""
    LONG = "LONG"
    SHORT = "SHORT"

class PositionStatus(Enum):
    """Position status"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class TradeType(Enum):
    """Trade types"""
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TARGET = "TARGET"

@dataclass
class Position:
    """Position data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    position_type: PositionType = PositionType.LONG
    status: PositionStatus = PositionStatus.OPEN
    
    # Entry details
    entry_price: float = 0.0
    entry_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    quantity: float = 0.0
    invested_amount: float = 0.0
    
    # Exit details
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    
    # Risk management
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_stop: Optional[float] = None
    
    # Performance metrics
    pnl: float = 0.0
    profit_after_amount: float = 0.0
    holding_time: Optional[str] = None
    
    # Metadata
    strategy_name: str = ""
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_pnl(self, current_price: float) -> float:
        """Calculate current PnL"""
        if self.status == PositionStatus.CLOSED and self.exit_price:
            # Position is closed, use exit price
            if self.position_type == PositionType.LONG:
                self.pnl = (self.exit_price - self.entry_price) * self.quantity
            else:
                self.pnl = (self.entry_price - self.exit_price) * self.quantity
        else:
            # Position is open, use current price
            if self.position_type == PositionType.LONG:
                self.pnl = (current_price - self.entry_price) * self.quantity
            else:
                self.pnl = (self.entry_price - current_price) * self.quantity
        
        self.profit_after_amount = self.invested_amount + self.pnl
        return self.pnl
    
    def calculate_holding_time(self) -> str:
        """Calculate holding time"""
        try:
            # Ensure both times are timezone-aware
            entry_time = self.entry_time
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            
            if self.exit_time:
                exit_time = self.exit_time
                if exit_time.tzinfo is None:
                    exit_time = exit_time.replace(tzinfo=timezone.utc)
                delta = exit_time - entry_time
            else:
                delta = datetime.now(timezone.utc) - entry_time
            
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                self.holding_time = f"{int(hours)}h {int(minutes)}m"
            else:
                self.holding_time = f"{int(minutes)}m {int(seconds)}s"
            
            return self.holding_time
        except Exception:
            self.holding_time = "N/A"
            return "N/A"
    
    def close_position(self, exit_price: float, exit_time: Optional[datetime] = None):
        """Close the position"""
        self.exit_price = exit_price
        self.exit_time = exit_time or datetime.now(timezone.utc)
        self.status = PositionStatus.CLOSED
        self.calculate_pnl(exit_price)
        self.calculate_holding_time()
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            'id': self.id,
            'symbol': self.symbol,
            'position_type': self.position_type.value,
            'status': self.status.value,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time,
            'quantity': self.quantity,
            'invested_amount': self.invested_amount,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time,
            'stop_loss': self.stop_loss,
            'target': self.target,
            'trailing_stop': self.trailing_stop,
            'pnl': self.pnl,
            'profit_after_amount': self.profit_after_amount,
            'holding_time': self.holding_time,
            'strategy_name': self.strategy_name,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """Create Position from dictionary"""
        position = cls()
        position.id = data.get('id', str(uuid.uuid4()))
        position.symbol = data.get('symbol', '')
        position.position_type = PositionType(data.get('position_type', 'LONG'))
        position.status = PositionStatus(data.get('status', 'OPEN'))
        position.entry_price = data.get('entry_price', 0.0)
        position.entry_time = data.get('entry_time', datetime.now(timezone.utc))
        position.quantity = data.get('quantity', 0.0)
        position.invested_amount = data.get('invested_amount', 0.0)
        position.exit_price = data.get('exit_price')
        position.exit_time = data.get('exit_time')
        position.stop_loss = data.get('stop_loss')
        position.target = data.get('target')
        position.trailing_stop = data.get('trailing_stop')
        position.pnl = data.get('pnl', 0.0)
        position.profit_after_amount = data.get('profit_after_amount', 0.0)
        position.holding_time = data.get('holding_time')
        position.strategy_name = data.get('strategy_name', '')
        position.notes = data.get('notes', '')
        position.created_at = data.get('created_at', datetime.now(timezone.utc))
        position.updated_at = data.get('updated_at', datetime.now(timezone.utc))
        return position

@dataclass
class Account:
    """Account data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Default Account"
    initial_balance: float = 10000.0  # Starting with 10k
    current_balance: float = 10000.0
    equity: float = 10000.0  # Balance + unrealized PnL
    
    # Trading statistics
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    
    # Daily limits
    daily_trades_count: int = 0
    daily_trades_limit: int = 5
    last_trade_date: Optional[str] = None
    
    # Risk management
    max_position_size: float = 1000.0  # Max amount per position
    risk_per_trade: float = 0.02  # 2% risk per trade
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_statistics(self, positions: list) -> None:
        """Calculate account statistics from positions"""
        closed_positions = [p for p in positions if p.status == PositionStatus.CLOSED]
        
        self.total_trades = len(closed_positions)
        self.profitable_trades = len([p for p in closed_positions if p.pnl > 0])
        self.losing_trades = len([p for p in closed_positions if p.pnl < 0])
        
        if self.total_trades > 0:
            self.win_rate = (self.profitable_trades / self.total_trades) * 100
        
        self.total_profit = sum(p.pnl for p in closed_positions if p.pnl > 0)
        self.total_loss = abs(sum(p.pnl for p in closed_positions if p.pnl < 0))
        
        # Calculate equity including open positions
        open_positions = [p for p in positions if p.status == PositionStatus.OPEN]
        unrealized_pnl = sum(p.pnl for p in open_positions)
        self.equity = self.current_balance + unrealized_pnl
        
        self.updated_at = datetime.now(timezone.utc)
    
    def can_trade_today(self) -> bool:
        """Check if can trade today (within daily limits)"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        if self.last_trade_date != today:
            self.daily_trades_count = 0
            self.last_trade_date = today
        
        return self.daily_trades_count < self.daily_trades_limit
    
    def increment_daily_trades(self) -> None:
        """Increment daily trades counter"""
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if self.last_trade_date != today:
            self.daily_trades_count = 0
        
        self.daily_trades_count += 1
        self.last_trade_date = today
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for MongoDB storage"""
        return {
            'id': self.id,
            'name': self.name,
            'initial_balance': self.initial_balance,
            'current_balance': self.current_balance,
            'equity': self.equity,
            'total_trades': self.total_trades,
            'profitable_trades': self.profitable_trades,
            'losing_trades': self.losing_trades,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'daily_trades_count': self.daily_trades_count,
            'daily_trades_limit': self.daily_trades_limit,
            'last_trade_date': self.last_trade_date,
            'max_position_size': self.max_position_size,
            'risk_per_trade': self.risk_per_trade,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """Create Account from dictionary"""
        account = cls()
        account.id = data.get('id', str(uuid.uuid4()))
        account.name = data.get('name', 'Default Account')
        account.initial_balance = data.get('initial_balance', 10000.0)
        account.current_balance = data.get('current_balance', 10000.0)
        account.equity = data.get('equity', 10000.0)
        account.total_trades = data.get('total_trades', 0)
        account.profitable_trades = data.get('profitable_trades', 0)
        account.losing_trades = data.get('losing_trades', 0)
        account.total_profit = data.get('total_profit', 0.0)
        account.total_loss = data.get('total_loss', 0.0)
        account.max_drawdown = data.get('max_drawdown', 0.0)
        account.win_rate = data.get('win_rate', 0.0)
        account.daily_trades_count = data.get('daily_trades_count', 0)
        account.daily_trades_limit = data.get('daily_trades_limit', 5)
        account.last_trade_date = data.get('last_trade_date')
        account.max_position_size = data.get('max_position_size', 1000.0)
        account.risk_per_trade = data.get('risk_per_trade', 0.02)
        account.created_at = data.get('created_at', datetime.now(timezone.utc))
        account.updated_at = data.get('updated_at', datetime.now(timezone.utc))
        return account 