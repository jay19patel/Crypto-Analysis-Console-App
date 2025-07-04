"""
Account Manager for broker system
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pymongo import MongoClient
from src.broker.models import Account, Position, PositionStatus
from src.config import get_settings
import logging
from src.system.message_formatter import MessageFormatter, MessageType

logger = logging.getLogger(__name__)

class AccountManager:
    """Manages trading account operations"""
    
    def __init__(self, websocket_server=None):
        """Initialize account manager
        
        Args:
            websocket_server: WebSocket server instance for sending messages
        """
        self.logger = logging.getLogger(__name__)
        self.websocket_server = websocket_server
        self.settings = get_settings()
        self.client = None
        self.db = None
        self.accounts_collection = None
        self.positions_collection = None
        self.account: Optional[Account] = None
        self.is_connected = False
        self.account_info = {}
        self.is_initialized = False
    
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
            self.logger.error(f"MongoDB connection error: {e}")
            return False
    
    def initialize_account(self) -> bool:
        """Initialize trading account"""
        try:
            # Account initialization logic here
            self.is_initialized = True
            self.logger.info("Account initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error initializing account: {e}")
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
            self.logger.error(f"Error saving account: {e}")
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
                self.logger.info(f"Balance updated: {old_balance:.2f} → {self.account.current_balance:.2f} ({reason})")
            return True
        
        return False
    
    def can_open_position(self, amount: float) -> bool:
        """Check if can open position with given amount"""
        if not self.account:
            return False
        
        # First refresh daily trades count from database
        if not self.refresh_daily_trades_count():
            self.logger.warning("Could not verify daily trades count")
            return False
        
        # Check daily trade limit BEFORE checking other conditions
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        actual_daily_count = self.get_daily_positions_count(today)
        
        if actual_daily_count >= self.account.daily_trades_limit:
            self.logger.warning(f"Daily trade limit reached: {actual_daily_count}/{self.account.daily_trades_limit} positions taken today")
            return False
        
        # Check if have enough balance
        if self.account.current_balance < amount:
            self.logger.warning(f"Insufficient balance: {self.account.current_balance:.2f} < {amount:.2f}")
            return False
        
        # Check max position size
        if amount > self.account.max_position_size:
            self.logger.warning(f"Position size too large: {amount:.2f} > {self.account.max_position_size:.2f}")
            return False
        
        return True
    
    def get_daily_positions_count(self, date_str: Optional[str] = None) -> int:
        """Get count of positions created on specific date from database"""
        if not self.is_connected:
            if not self.connect():
                return 0
        
        try:
            if date_str is None:
                date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Get positions collection reference
            positions_collection = self.db['positions']
            
            # Create date range for the entire day
            start_date = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            end_date = start_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Count positions created within this date range
            count = positions_collection.count_documents({
                "entry_time": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            })
            
            return count
            
        except Exception as e:
            self.logger.error(f"Error getting daily positions count: {e}")
            return 0

    def refresh_daily_trades_count(self) -> bool:
        """Refresh daily trades count from database based on today's date"""
        if not self.account or not self.is_connected:
            return False
        
        try:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Get actual count of positions created today from database
            actual_daily_count = self.get_daily_positions_count(today)
            
            # If it's a new day, reset the counter
            if self.account.last_trade_date != today:
                self.account.daily_trades_count = 0
                self.account.last_trade_date = today
                self.logger.info(f"New trading day: {today} - Daily trades reset to 0")
            
            # Update account with actual count from database
            if self.account.daily_trades_count != actual_daily_count:
                self.logger.info(f"Syncing daily trades count: {self.account.daily_trades_count} → {actual_daily_count}")
                self.account.daily_trades_count = actual_daily_count
            
            # Save updated account
            self.save_account()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error refreshing daily trades count: {e}")
            return False
    
    def reserve_margin(self, margin_amount: float, trading_fee: float) -> bool:
        """Reserve margin for a position and deduct from current balance"""
        if not self.account:
            return False
        
        total_required = margin_amount + trading_fee
        
        # Check if we have enough current balance (margin comes from balance)
        if total_required > self.account.current_balance:
            self.logger.warning(f"Insufficient balance for margin: {self.account.current_balance:.2f} < {total_required:.2f}")
            return False
        
        # Deduct margin and trading fee from current balance
        self.account.current_balance -= total_required
        self.account.total_margin_used += margin_amount
        
        # Track brokerage charges
        self.account.brokerage_charges += trading_fee
        
        # Update timestamp only
        self.account.updated_at = datetime.now(timezone.utc)
        
        return self.save_account()
    
    def release_margin(self, margin_amount: float, pnl: float, trading_fee: float = 0.0) -> bool:
        """Release margin from closed position and add back to current balance with PnL"""
        if not self.account:
            return False
        
        # Add margin back to current balance along with PnL
        self.account.current_balance += margin_amount + pnl
        self.account.total_margin_used -= margin_amount
        
        # If there was an exit fee, deduct it and track it
        if trading_fee > 0:
            self.account.current_balance -= trading_fee
            self.account.brokerage_charges += trading_fee
        
        # Ensure margin used doesn't go negative
        if self.account.total_margin_used < 0:
            self.account.total_margin_used = 0
        
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
        
        # Ensure we have enough balance available for margin + fee
        total_required = required_margin + trading_fee
        if total_required > self.account.current_balance:
            # Reduce position size to fit available balance
            available_for_position = self.account.current_balance * 0.95  # Leave 5% buffer
            if available_for_position > 0:
                total_available = available_for_position
                trading_fee = total_available * self.settings.BROKER_TRADING_FEE_PCT / (1 + self.settings.BROKER_TRADING_FEE_PCT)
                required_margin = total_available - trading_fee
                max_position_value = required_margin * leverage
            else:
                return 0.0, 0.0, 0.0
        
        return max_position_value, required_margin, trading_fee
    
    def update_statistics(self, positions: List[Position]) -> None:
        """Update account statistics from positions"""
        if not self.account:
            return
        
        try:
            self.account.calculate_statistics(positions)
            self.save_account()
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary"""
        if not self.account:
            return {}
        
        return {
            'id': self.account.id,
            'name': self.account.name,
            'initial_balance': self.account.initial_balance,
            'current_balance': self.account.current_balance,
            'total_trades': self.account.total_trades,
            'profitable_trades': self.account.profitable_trades,
            'losing_trades': self.account.losing_trades,
            'total_profit': self.account.total_profit,
            'total_loss': self.account.total_loss,
            'win_rate': self.account.win_rate,
            'daily_trades_count': self.account.daily_trades_count,
            'daily_trades_limit': self.account.daily_trades_limit,
            'last_trade_date': self.account.last_trade_date,
            'algo_status': self.account.algo_status,
            'max_position_size': self.account.max_position_size,
            'risk_per_trade': self.account.risk_per_trade,
            'max_leverage': self.account.max_leverage,
            'total_margin_used': self.account.total_margin_used,
            'brokerage_charges': self.account.brokerage_charges,
            'total_profit_loss': self.account.total_profit - self.account.total_loss,
            'created_at': self.account.created_at,
            'updated_at': self.account.updated_at
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
    
    def set_algo_status(self, status: bool) -> bool:
        """Set algorithm running status"""
        if not self.account:
            return False
        
        self.account.algo_status = status
        self.account.updated_at = datetime.now(timezone.utc)
        return self.save_account()
    
    def get_algo_status(self) -> bool:
        """Get algorithm running status"""
        if not self.account:
            return False
        
        return self.account.algo_status
    
    def start_algo(self) -> bool:
        """Set algorithm status to running (True)"""
        return self.set_algo_status(True)
    
    def stop_algo(self) -> bool:
        """Set algorithm status to stopped (False)"""
        return self.set_algo_status(False)
    
    def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.is_connected = False
    
    def check_and_reset_daily_trades(self) -> bool:
        """Check and reset daily trades if it's a new day with no positions"""
        if not self.account or not self.is_connected:
            return False
        
        try:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # If it's same day, no need to reset
            if self.account.last_trade_date == today:
                return True
            
            # It's a new day - get actual positions count for today
            actual_daily_count = self.get_daily_positions_count(today)
            
            # Reset account values for new day
            self.account.daily_trades_count = actual_daily_count
            self.account.last_trade_date = today
            self.account.updated_at = datetime.now(timezone.utc)
            
            # Save updated account
            if self.save_account():
                if actual_daily_count == 0:
                    self.logger.info(f"New trading day: {today} - Daily trades reset to 0")
                else:
                    self.logger.info(f"New trading day: {today} - Daily trades synced to {actual_daily_count}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking and resetting daily trades: {e}")
            return False
    
    def sync_daily_trades_after_position_creation(self) -> bool:
        """Sync daily trades count with database after position creation"""
        if not self.account or not self.is_connected:
            return False
        
        try:
            today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
            
            # Get actual count of positions created today from database
            actual_daily_count = self.get_daily_positions_count(today)
            
            # Update account with actual count from database
            self.account.daily_trades_count = actual_daily_count
            self.account.last_trade_date = today
            self.account.updated_at = datetime.now(timezone.utc)
            
            # Save updated account
            if self.save_account():
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error syncing daily trades after position creation: {e}")
            return False

    def send_message(self, message: Dict):
        """Send message through WebSocket if available"""
        if self.websocket_server:
            self.websocket_server.queue_message(message)

    def log_message(self, message: str, level: str = "info"):
        """Send log message"""
        self.logger.log(getattr(logging, level.upper()), message)
        if self.websocket_server:
            self.send_message(
                MessageFormatter.format_log(message, level, "account_manager")
            )

    def get_account_info(self) -> Dict:
        """Get current account information"""
        try:
            # Get account info logic here
            if self.websocket_server:
                self.send_message(
                    MessageFormatter.format_message(
                        MessageType.SYSTEM,
                        self.account_info,
                        "account_manager"
                    )
                )
            return self.account_info
        except Exception as e:
            self.log_message(f"Error getting account info: {e}", "error")
            return {}

    def check_margin_requirements(self, required_margin: float) -> bool:
        """Check if account has sufficient margin"""
        try:
            # Margin check logic here
            has_margin = True  # Replace with actual check
            if not has_margin:
                self.log_message(
                    f"Insufficient margin. Required: ${required_margin:.2f}",
                    "warning"
                )
            return has_margin
        except Exception as e:
            self.log_message(f"Error checking margin: {e}", "error")
            return False

    def update_account_status(self):
        """Update and broadcast account status"""
        try:
            # Update account status logic here
            status = {
                "balance": self.account_info.get("balance", 0),
                "used_margin": self.account_info.get("used_margin", 0),
                "available_margin": self.account_info.get("available_margin", 0),
                "margin_level": self.account_info.get("margin_level", 0),
                "open_positions": self.account_info.get("open_positions", 0)
            }
            
            if self.websocket_server:
                self.send_message(
                    MessageFormatter.format_message(
                        MessageType.SYSTEM,
                        {
                            "type": "account_status",
                            "data": status
                        },
                        "account_manager"
                    )
                )
        except Exception as e:
            self.log_message(f"Error updating account status: {e}", "error") 