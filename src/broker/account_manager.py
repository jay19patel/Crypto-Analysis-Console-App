"""
Account Manager for broker system
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pymongo import MongoClient
from src.broker.models import Account, Position, PositionStatus
from src.config import get_settings
from src.ui.console import ConsoleUI


class AccountManager:
    """Manages trading account operations"""
    
    def __init__(self, ui: ConsoleUI):
        """Initialize account manager"""
        self.ui = ui
        self.settings = get_settings()
        self.client = None
        self.db = None
        self.accounts_collection = None
        self.account: Optional[Account] = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(
                self.settings.MONGODB_URL,
                serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT * 1000
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database and collection
            self.db = self.client[self.settings.MONGODB_DATABASE]
            self.accounts_collection = self.db['accounts']
            
            self.is_connected = True
            return True
            
        except Exception as e:
            self.ui.print_error(f"MongoDB connection error: {e}")
            return False
    
    def initialize_account(self) -> bool:
        """Initialize or load existing account"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            # Try to load existing account
            existing_account = self.accounts_collection.find_one({})
            
            if existing_account:
                self.account = Account.from_dict(existing_account)
                self.ui.print_success(f"Loaded existing account: {self.account.name}")
            else:
                # Create new account with config settings
                self.account = Account(
                    initial_balance=self.settings.BROKER_INITIAL_BALANCE,
                    current_balance=self.settings.BROKER_INITIAL_BALANCE,
                    equity=self.settings.BROKER_INITIAL_BALANCE,
                    max_position_size=self.settings.BROKER_MAX_POSITION_SIZE,
                    risk_per_trade=self.settings.BROKER_RISK_PER_TRADE,
                    daily_trades_limit=self.settings.BROKER_DAILY_TRADE_LIMIT,
                    max_leverage=self.settings.BROKER_MAX_LEVERAGE,
                    available_margin=self.settings.BROKER_INITIAL_BALANCE
                )
                self.save_account()
                self.ui.print_success(f"Created new account: {self.account.name}")
            
            return True
            
        except Exception as e:
            self.ui.print_error(f"Error initializing account: {e}")
            return False
    
    def save_account(self) -> bool:
        """Save account to MongoDB"""
        if not self.account or not self.is_connected:
            return False
        
        try:
            account_data = self.account.to_dict()
            
            # Update or insert account
            result = self.accounts_collection.replace_one(
                {'id': self.account.id},
                account_data,
                upsert=True
            )
            
            return result.acknowledged
            
        except Exception as e:
            self.ui.print_error(f"Error saving account: {e}")
            return False
    
    def get_account(self) -> Optional[Account]:
        """Get current account"""
        return self.account
    
    def update_balance(self, amount: float, reason: str = "") -> bool:
        """Update account balance"""
        if not self.account:
            return False
        
        old_balance = self.account.current_balance
        self.account.current_balance += amount
        self.account.updated_at = datetime.now(timezone.utc)
        
        # Save to database
        if self.save_account():
            if reason:
                self.ui.print_info(f"Balance updated: {old_balance:.2f} → {self.account.current_balance:.2f} ({reason})")
            return True
        
        return False
    
    def can_open_position(self, amount: float) -> bool:
        """Check if can open position with given amount"""
        if not self.account:
            return False
        
        # Check if have enough balance
        if self.account.current_balance < amount:
            self.ui.print_warning(f"Insufficient balance: {self.account.current_balance:.2f} < {amount:.2f}")
            return False
        
        # Check daily trade limit
        if not self.account.can_trade_today():
            self.ui.print_warning(f"Daily trade limit reached: {self.account.daily_trades_count}/{self.account.daily_trades_limit}")
            return False
        
        # Check max position size
        if amount > self.account.max_position_size:
            self.ui.print_warning(f"Position size too large: {amount:.2f} > {self.account.max_position_size:.2f}")
            return False
        
        return True
    
    def reserve_margin(self, margin_amount: float, trading_fee: float) -> bool:
        """Reserve margin for a position"""
        if not self.account:
            return False
        
        total_required = margin_amount + trading_fee
        
        # Check if we have enough available margin
        if total_required > self.account.available_margin:
            self.ui.print_warning(f"Insufficient margin: {self.account.available_margin:.2f} < {total_required:.2f}")
            return False
        
        # Reserve margin and deduct trading fee from balance
        self.account.available_margin -= total_required
        self.account.total_margin_used += margin_amount
        self.account.current_balance -= trading_fee  # Trading fee is paid immediately
        self.account.increment_daily_trades()
        
        return self.save_account()
    
    def reserve_funds(self, amount: float) -> bool:
        """Reserve funds for a position (legacy method for compatibility)"""
        if not self.can_open_position(amount):
            return False
        
        # Deduct from balance
        self.account.current_balance -= amount
        self.account.increment_daily_trades()
        
        return self.save_account()
    
    def release_margin(self, margin_amount: float, pnl: float) -> bool:
        """Release margin from closed position"""
        if not self.account:
            return False
        
        # Release margin back to available margin
        self.account.available_margin += margin_amount
        self.account.total_margin_used -= margin_amount
        
        # Add PnL to balance (can be positive or negative)
        self.account.current_balance += pnl
        
        # Ensure margin used doesn't go negative
        if self.account.total_margin_used < 0:
            self.account.total_margin_used = 0
        
        return self.save_account()
    
    def release_funds(self, amount: float, pnl: float) -> bool:
        """Release funds from closed position (legacy method for compatibility)"""
        if not self.account:
            return False
        
        # Return invested amount plus PnL
        self.account.current_balance += amount + pnl
        
        return self.save_account()
    
    def calculate_position_size(self, price: float, risk_percentage: Optional[float] = None, leverage: float = 1.0) -> tuple[float, float, float]:
        """Calculate position size and margin requirements"""
        if not self.account:
            return 0.0, 0.0, 0.0
        
        risk_pct = risk_percentage or self.account.risk_per_trade
        risk_amount = self.account.current_balance * risk_pct
        
        # Calculate position size with leverage
        max_position_value = min(risk_amount * leverage, self.account.max_position_size * leverage)
        
        # Calculate required margin (position value / leverage)
        required_margin = max_position_value / leverage
        
        # Calculate trading fee (2% of invested amount)
        trading_fee = required_margin * self.settings.BROKER_TRADING_FEE_PCT
        
        # Ensure we have enough margin available
        if required_margin + trading_fee > self.account.available_margin:
            # Reduce position size to fit available margin
            available_for_position = self.account.available_margin - trading_fee
            if available_for_position > 0:
                required_margin = available_for_position
                max_position_value = required_margin * leverage
                trading_fee = required_margin * self.settings.BROKER_TRADING_FEE_PCT
            else:
                return 0.0, 0.0, 0.0
        
        return max_position_value, required_margin, trading_fee
    
    def update_statistics(self, positions: List[Position]) -> None:
        """Update account statistics"""
        if not self.account:
            return
        
        self.account.calculate_statistics(positions)
        self.save_account()
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary for display"""
        if not self.account:
            return {}
        
        return {
            'name': self.account.name,
            'current_balance': self.account.current_balance,
            'equity': self.account.equity,
            'initial_balance': self.account.initial_balance,
            'total_profit_loss': self.account.current_balance - self.account.initial_balance,
            'total_trades': self.account.total_trades,
            'profitable_trades': self.account.profitable_trades,
            'losing_trades': self.account.losing_trades,
            'win_rate': self.account.win_rate,
            'daily_trades_count': self.account.daily_trades_count,
            'daily_trades_limit': self.account.daily_trades_limit,
            'max_position_size': self.account.max_position_size,
            'growth_percentage': ((self.account.current_balance - self.account.initial_balance) / self.account.initial_balance) * 100,
            # Margin trading info
            'max_leverage': self.account.max_leverage,
            'total_margin_used': self.account.total_margin_used,
            'available_margin': self.account.available_margin,
            'margin_usage_percentage': (self.account.total_margin_used / (self.account.total_margin_used + self.account.available_margin)) * 100 if (self.account.total_margin_used + self.account.available_margin) > 0 else 0
        }
    
    def reset_daily_trades(self) -> bool:
        """Reset daily trades counter (for new day)"""
        if not self.account:
            return False
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if self.account.last_trade_date != today:
            self.account.daily_trades_count = 0
            self.account.last_trade_date = today
            return self.save_account()
        
        return True
    
    def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.is_connected = False 