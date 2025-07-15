"""
Simplified Async Broker System
Basic trading execution with dummy data and essential functionality
"""

import logging
import uuid
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from src.broker.models import Account, Position, PositionType, PositionStatus
from src.config import get_settings
from src.notifications import NotificationManager


class ExecutionStatus(Enum):
    """Trade execution status"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TradeRequest:
    """Trade execution request"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    signal: str = ""  # BUY/SELL
    price: float = 0.0
    quantity: float = 0.0
    leverage: float = 1.0
    strategy_name: str = ""
    confidence: float = 100.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: ExecutionStatus = ExecutionStatus.PENDING
    error_message: Optional[str] = None
    position_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal": self.signal,
            "price": self.price,
            "quantity": self.quantity,
            "leverage": self.leverage,
            "strategy_name": self.strategy_name,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "error_message": self.error_message,
            "position_id": self.position_id
        }


class AsyncBroker:
    """Simplified async broker with dummy data"""
    
    def __init__(self):
        """Initialize async broker"""
        self.settings = get_settings()
        self.logger = logging.getLogger("broker.async_broker")
        
        # Dummy data storage
        self._price_cache: Dict[str, Dict] = {}
        self._position_cache: Dict[str, Position] = {}
        
        # Performance tracking
        self._trade_stats = {
            "total_requests": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "avg_execution_time": 0.0
        }
        
        # Notification system
        self.notification_manager = NotificationManager()
        
        # Account and positions
        self.account: Optional[Account] = None
        self.positions: Dict[str, Position] = {}
        
        # Initialize dummy account
        self._initialize_dummy_account()
        
        self.logger.info("Simplified async broker initialized")
    
    def _initialize_dummy_account(self):
        """Initialize dummy account with fixed data"""
        self.account = Account()
        self.account.id = "main"
        self.account.name = "Trading Account Main"
        self.account.initial_balance = 10000.0
        self.account.current_balance = 10000.0
        self.account.daily_trades_limit = 50
        self.account.max_position_size = 1000.0
        self.account.risk_per_trade = 0.02
        self.account.max_leverage = 5.0
        self.account.total_trades = 0
        self.account.profitable_trades = 0
        self.account.losing_trades = 0
        self.account.win_rate = 0.0
        self.account.total_profit = 0.0
        self.account.total_loss = 0.0
        self.account.daily_trades_count = 0
        self.account.total_margin_used = 0.0
        self.account.brokerage_charges = 0.0
        self.account.last_trade_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    async def start(self) -> bool:
        """Start async broker system"""
        try:
            self.logger.info("Starting simplified async broker system")
            
            # Start notification manager
            await self.notification_manager.start()
            
            self.logger.info("Simplified async broker system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start async broker: {e}")
            return False
    
    async def stop(self):
        """Stop async broker system"""
        self.logger.info("Stopping simplified async broker system")
        
        # Stop notification manager
        await self.notification_manager.stop()
        
        self.logger.info("Simplified async broker system stopped")
    
    async def execute_trade_async(self, trade_request: TradeRequest) -> bool:
        """Execute trade asynchronously with dummy data"""
        try:
            self.logger.info(f"🚀 Executing trade: {trade_request.signal} {trade_request.symbol} at ${trade_request.price:.2f}")
            
            # Update status
            trade_request.status = ExecutionStatus.EXECUTING
            
            # Validate trade request
            if not self._validate_trade_request(trade_request):
                trade_request.status = ExecutionStatus.FAILED
                return False
            
            # Check risk limits
            if not self._check_risk_limits(trade_request):
                trade_request.status = ExecutionStatus.FAILED
                return False
            
            # Execute trade with dummy data
            success = self._execute_trade_simple(trade_request)
            
            if success:
                trade_request.status = ExecutionStatus.COMPLETED
                
                # Send notification
                await self.notification_manager.notify_trade_execution(
                    symbol=trade_request.symbol,
                    signal=trade_request.signal,
                    price=trade_request.price,
                    trade_id=trade_request.id,
                    position_id=trade_request.position_id
                )
                
                self._trade_stats["successful_trades"] += 1
                self.logger.info(f"✅ Trade executed successfully")
                return True
            else:
                trade_request.status = ExecutionStatus.FAILED
                self._trade_stats["failed_trades"] += 1
                return False
                
        except Exception as e:
            trade_request.status = ExecutionStatus.FAILED
            trade_request.error_message = str(e)
            self._trade_stats["failed_trades"] += 1
            
            self.logger.error(f"❌ Trade execution failed: {e}")
            
            # Send error notification
            await self.notification_manager.notify_system_error(
                error_message=str(e),
                component="AsyncBroker"
            )
            
            return False
    
    async def close_position_async(self, position_id: str, exit_price: float, reason: str) -> bool:
        """Close position asynchronously"""
        try:
            position = self.positions.get(position_id)
            if not position or position.status != PositionStatus.OPEN:
                return False
            
            # Close position with dummy data
            success = self._close_position_simple(position_id, exit_price, reason)
            
            if success:
                # Send notification
                await self.notification_manager.notify_position_close(
                    symbol=position.symbol,
                    position_id=position_id,
                    exit_price=exit_price,
                    pnl=position.pnl,
                    reason=reason
                )
                
                self.logger.info(f"✅ Position closed: {position.symbol} at ${exit_price:.2f}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Failed to close position {position_id}: {e}")
            return False
    
    async def update_prices_async(self, prices: Dict[str, Dict]) -> None:
        """Update prices asynchronously with dummy data"""
        try:
            # Update local cache
            self._price_cache.update(prices)
            
            # Update position PnLs
            self._update_position_pnls(prices)
            
        except Exception as e:
            self.logger.error(f"Error updating prices: {e}")
    
    async def get_account_summary_async(self) -> Dict[str, Any]:
        """Get account summary asynchronously"""
        if not self.account:
            return {}
        
        summary = {
            "account_id": self.account.id,
            "name": self.account.name,
            "initial_balance": self.account.initial_balance,
            "current_balance": self.account.current_balance,
            "total_trades": self.account.total_trades,
            "profitable_trades": self.account.profitable_trades,
            "losing_trades": self.account.losing_trades,
            "win_rate": self.account.win_rate,
            "total_profit": self.account.total_profit,
            "total_loss": self.account.total_loss,
            "daily_trades_count": self.account.daily_trades_count,
            "daily_trades_limit": self.account.daily_trades_limit,
            "total_margin_used": self.account.total_margin_used,
            "brokerage_charges": self.account.brokerage_charges,
            "open_positions_count": len([p for p in self.positions.values() if p.status == PositionStatus.OPEN]),
            "total_unrealized_pnl": sum(p.pnl for p in self.positions.values() if p.status == PositionStatus.OPEN),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return summary
    
    async def get_positions_summary_async(self) -> Dict[str, Any]:
        """Get positions summary asynchronously"""
        open_positions = []
        closed_positions = []
        
        for position in self.positions.values():
            pos_data = position.to_dict()
            if position.symbol in self._price_cache:
                pos_data["current_price"] = self._price_cache[position.symbol].get("price", 0.0)
            
            if position.status == PositionStatus.OPEN:
                open_positions.append(pos_data)
            else:
                closed_positions.append(pos_data)
        
        # Sort closed positions by exit time
        closed_positions.sort(
            key=lambda x: x.get("exit_time", ""), reverse=True
        )
        
        return {
            "open_positions": open_positions,
            "closed_positions": closed_positions[:10],  # Last 10
            "total_open": len(open_positions),
            "total_closed": len(closed_positions),
            "total_unrealized_pnl": sum(p.pnl for p in self.positions.values() if p.status == PositionStatus.OPEN)
        }
    
    # Private methods
    def _validate_trade_request(self, trade_request: TradeRequest) -> bool:
        """Validate trade request"""
        if trade_request.signal not in ['BUY', 'SELL']:
            trade_request.error_message = f"Invalid signal: {trade_request.signal}"
            return False
        
        if trade_request.price <= 0:
            trade_request.error_message = f"Invalid price: {trade_request.price}"
            return False
        
        if trade_request.quantity <= 0:
            trade_request.error_message = f"Invalid quantity: {trade_request.quantity}"
            return False
        
        if trade_request.confidence < 50:  # Lower threshold for demo
            trade_request.error_message = f"Low confidence: {trade_request.confidence}%"
            return False
        
        return True
    
    def _check_risk_limits(self, trade_request: TradeRequest) -> bool:
        """Check risk management limits"""
        if not self.account:
            trade_request.error_message = "No account available"
            return False
        
        # Check daily trade limits
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        if self.account.last_trade_date != today:
            self.account.daily_trades_count = 0
            self.account.last_trade_date = today
        
        if self.account.daily_trades_count >= self.account.daily_trades_limit:
            trade_request.error_message = f"Daily trade limit reached: {self.account.daily_trades_count}/{self.account.daily_trades_limit}"
            return False
        
        # Check position size limits
        position_value = trade_request.price * trade_request.quantity
        if position_value > self.account.max_position_size:
            trade_request.error_message = f"Position size ${position_value:.2f} exceeds limit ${self.account.max_position_size:.2f}"
            return False
        
        # Check if position already exists for symbol
        for position in self.positions.values():
            if position.symbol == trade_request.symbol and position.status == PositionStatus.OPEN:
                trade_request.error_message = f"Position already open for {trade_request.symbol}"
                return False
        
        return True
    
    def _execute_trade_simple(self, trade_request: TradeRequest) -> bool:
        """Execute trade with dummy data"""
        try:
            # Calculate position details
            position_value = trade_request.price * trade_request.quantity
            margin_required = position_value / trade_request.leverage
            trading_fee = margin_required * 0.001  # 0.1% fee
            
            # Check if we have enough balance
            total_required = margin_required + trading_fee
            if total_required > self.account.current_balance:
                trade_request.error_message = f"Insufficient balance: need ${total_required:.2f}, have ${self.account.current_balance:.2f}"
                return False
            
            # Create position
            position = Position()
            position.symbol = trade_request.symbol
            position.position_type = PositionType.LONG if trade_request.signal == 'BUY' else PositionType.SHORT
            position.entry_price = trade_request.price
            position.quantity = trade_request.quantity
            position.invested_amount = position_value
            position.strategy_name = trade_request.strategy_name
            position.leverage = trade_request.leverage
            position.margin_used = margin_required
            position.trading_fee = trading_fee
            
            # Calculate risk levels
            if position.position_type == PositionType.LONG:
                position.stop_loss = trade_request.price * 0.95  # 5% below
                position.target = trade_request.price * 1.10  # 10% above
            else:
                position.stop_loss = trade_request.price * 1.05  # 5% above
                position.target = trade_request.price * 0.90  # 10% below
            
            # Calculate initial PnL
            position.calculate_pnl(trade_request.price)
            
            # Update account
            self.account.current_balance -= total_required
            self.account.total_margin_used += margin_required
            self.account.brokerage_charges += trading_fee
            self.account.total_trades += 1
            self.account.daily_trades_count += 1
            
            # Save position
            self.positions[position.id] = position
            trade_request.position_id = position.id
            
            return True
            
        except Exception as e:
            trade_request.error_message = str(e)
            return False
    
    def _close_position_simple(self, position_id: str, exit_price: float, reason: str) -> bool:
        """Close position with dummy data"""
        try:
            position = self.positions.get(position_id)
            if not position or position.status != PositionStatus.OPEN:
                return False
            
            # Close position
            position.close_position(exit_price)
            position.notes = reason
            
            # Calculate exit fee
            exit_fee = position.trading_fee * 0.5
            
            # Update account
            self.account.current_balance += position.margin_used + position.pnl - exit_fee
            self.account.total_margin_used -= position.margin_used
            
            if exit_fee > 0:
                self.account.brokerage_charges += exit_fee
            
            # Update statistics
            if position.pnl > 0:
                self.account.profitable_trades += 1
                self.account.total_profit += position.pnl
            else:
                self.account.losing_trades += 1
                self.account.total_loss += abs(position.pnl)
            
            # Calculate win rate
            if self.account.total_trades > 0:
                self.account.win_rate = (self.account.profitable_trades / self.account.total_trades) * 100
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return False
    
    def _update_position_pnls(self, prices: Dict[str, Dict]):
        """Update position PnLs with new prices"""
        for position in self.positions.values():
            if position.symbol in prices and position.status == PositionStatus.OPEN:
                current_price = prices[position.symbol].get("price", 0.0)
                if current_price > 0:
                    position.calculate_pnl(current_price)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self._trade_stats,
            "total_positions": len(self.positions),
            "open_positions": len([p for p in self.positions.values() if p.status == PositionStatus.OPEN]),
            "account_balance": self.account.current_balance if self.account else 0.0
        } 