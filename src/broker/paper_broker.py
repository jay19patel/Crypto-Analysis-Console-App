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
from collections import OrderedDict

from src.broker.models import Account, Position, PositionType, PositionStatus, Order, OrderType, OrderStatus
from src.config import get_settings, get_trading_config
from src.database.mongodb_client import AsyncMongoDBClient


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
    """Simplified async broker with dummy data and MongoDB persistence"""
    
    def __init__(self):
        """Initialize async broker"""
        self.settings = get_settings()
        self.trading_config = get_trading_config()
        self.logger = logging.getLogger("broker.async_broker")
        
        # Dummy data storage
        self._price_cache: OrderedDict[str, Dict] = OrderedDict()
        self._position_cache: OrderedDict[str, Position] = OrderedDict()
        self._cache_max_size = 500
        
        # Performance tracking
        self._trade_stats = {
            "total_requests": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            "avg_execution_time": 0.0
        }
        
        # MongoDB client
        self.mongodb_client = AsyncMongoDBClient()
        
        # Account and positions
        self.account: Optional[Account] = None
        self.positions: Dict[str, Position] = {}
        
        self.logger.info("Simplified async broker initialized")
    
    async def start(self) -> bool:
        """Start async broker system"""
        try:
            self.logger.info("Starting simplified async broker system")
            
            # Connect to MongoDB
            if not await self.mongodb_client.connect():
                self.logger.warning("Failed to connect to MongoDB, using in-memory storage")
            
            # Initialize account
            await self._initialize_account()
            
            # Load positions
            await self._load_positions()
            
            self.logger.info("Simplified async broker system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start async broker: {e}")
            return False
    
    async def stop(self):
        """Stop async broker system"""
        self.logger.info("Stopping simplified async broker system")
        
        # Disconnect from MongoDB
        await self.mongodb_client.disconnect()
        
        self.logger.info("Simplified async broker system stopped")
    
    async def _initialize_account(self):
        """Initialize or load trading account"""
        try:
            # Try to load existing account from MongoDB
            account_data = await self.mongodb_client.load_account("main")
            
            if account_data:
                self.account = Account.from_dict(account_data)
                self.logger.info(f"✅ Loaded existing account: {self.account.id}")
            else:
                # Create new account with config settings
                self.account = Account()
                self.account.id = "main"
                self.account.name = "Trading Account Main"
                self.account.initial_balance = self.trading_config["initial_balance"]
                self.account.current_balance = self.trading_config["initial_balance"]
                self.account.daily_trades_limit = self.trading_config["daily_trades_limit"]
                self.account.max_leverage = self.trading_config["max_leverage"]
                self.account.total_trades = 0
                self.account.profitable_trades = 0
                self.account.losing_trades = 0
                self.account.win_rate = 0.0
                self.account.realized_pnl = 0.0
                self.account.daily_trades_count = 0
                self.account.total_margin_used = 0.0
                self.account.brokerage_charges = 0.0
                self.account.last_trade_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                
                # Save new account to MongoDB
                await self.mongodb_client.save_account(self.account.to_dict())
                
                self.logger.info(f"✅ Created new account: {self.account.id}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize account: {e}")
            # Create fallback account
            self._create_fallback_account()
    
    def _create_fallback_account(self):
        """Create fallback account if MongoDB fails"""
        self.account = Account()
        self.account.id = "main"
        self.account.name = "Trading Account Main"
        self.account.initial_balance = self.trading_config["initial_balance"]
        self.account.current_balance = self.trading_config["initial_balance"]
        self.account.daily_trades_limit = self.trading_config["daily_trades_limit"]
        self.account.max_leverage = self.trading_config["max_leverage"]
        self.account.last_trade_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    async def _load_positions(self):
        """Load positions from MongoDB"""
        try:
            # Load all positions from MongoDB
            positions_data = await self.mongodb_client.load_positions()
            
            for position_data in positions_data:
                position = Position.from_dict(position_data)
                self.positions[position.id] = position
                self._position_cache[position.id] = position
            
            self.logger.info(f"✅ Loaded {len(self.positions)} positions from MongoDB")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load positions: {e}")
            # Continue with empty positions
    
    async def execute_trade_async(self, trade_request: TradeRequest) -> bool:
        """Execute trade asynchronously with dummy data and MongoDB persistence"""
        try:
            self.logger.info(f"🚀 Executing trade: {trade_request.signal} {trade_request.symbol} at ${trade_request.price:.2f}")
            
            # Update status
            trade_request.status = ExecutionStatus.EXECUTING
            
            # Validate trade request
            if not self._validate_trade_request(trade_request):
                trade_request.status = ExecutionStatus.FAILED
                self.logger.error(f"❌ Trade validation failed: {trade_request.error_message}")
                return False
            
            # Check risk limits
            if not self._check_risk_limits(trade_request):
                trade_request.status = ExecutionStatus.FAILED
                self.logger.error(f"❌ Risk limits check failed: {trade_request.error_message}")
                return False
            
            # Execute trade with dummy data
            success = await self._execute_trade_simple(trade_request)
            
            if success:
                trade_request.status = ExecutionStatus.COMPLETED
                
                # Save trade to MongoDB
                await self.mongodb_client.save_trade(trade_request.to_dict())
                
                # Save updated account to MongoDB
                await self.mongodb_client.save_account(self.account.to_dict())
                
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
            
            return False
    
    async def close_position_async(self, position_id: str, exit_price: float, reason: str) -> bool:
        """Close position asynchronously with MongoDB persistence"""
        try:
            position = self.positions.get(position_id)
            if not position or position.status != PositionStatus.OPEN:
                return False
            
            # Store position data before closing for notification
            position_data = {
                "symbol": position.symbol,
                "position_type": position.position_type.value,
                "entry_price": position.entry_price,
                "quantity": position.quantity,
                "leverage": position.leverage,
                "investment_amount": position.invested_amount,
                "leveraged_amount": position.invested_amount * position.leverage,
                "margin_used": position.margin_used,
                "account_balance_before": self.account.current_balance,
                "entry_time": position.entry_time
            }
            
            # Close position with dummy data
            success = await self._close_position_simple(position_id, exit_price, reason)
            
            if success:
                # Calculate exit fees and final PnL
                exit_fee = position.trading_fee * self.trading_config["exit_fee_multiplier"]
                total_fees = position.trading_fee + exit_fee
                
                # Calculate trade duration
                duration_seconds = (datetime.now(timezone.utc) - position_data["entry_time"].replace(tzinfo=timezone.utc)).total_seconds()
                hours = int(duration_seconds // 3600)
                minutes = int((duration_seconds % 3600) // 60)
                trade_duration = f"{hours}h {minutes}m"
                
                # Calculate account growth
                account_balance_after = self.account.current_balance
                account_growth = account_balance_after - position_data["account_balance_before"]
                account_growth_pct = (account_growth / position_data["account_balance_before"]) * 100 if position_data["account_balance_before"] > 0 else 0
                
                # Calculate PnL percentage
                pnl_percentage = (position.pnl / position_data["margin_used"]) * 100 if position_data["margin_used"] > 0 else 0
                
                # Save updated position to MongoDB
                await self.mongodb_client.save_position(position.to_dict())
                
                # Save updated account to MongoDB
                await self.mongodb_client.save_account(self.account.to_dict())
                
                # Send position close notification if notification manager is available
                if hasattr(self, 'notification_manager') and self.notification_manager:
                    try:
                        await self.notification_manager.notify_position_close(
                            symbol=position_data["symbol"],
                            position_id=position_id,
                            exit_price=exit_price,
                            pnl=position.pnl,
                            reason=reason,
                            position_type=position_data["position_type"],
                            entry_price=position_data["entry_price"],
                            quantity=position_data["quantity"],
                            leverage=position_data["leverage"],
                            pnl_percentage=pnl_percentage,
                            investment_amount=position_data["investment_amount"],
                            leveraged_amount=position_data["leveraged_amount"],
                            margin_used=position_data["margin_used"],
                            trading_fee=position.trading_fee,
                            exit_fee=exit_fee,
                            total_fees=total_fees,
                            trade_duration=trade_duration,
                            account_balance_before=position_data["account_balance_before"],
                            account_balance_after=account_balance_after,
                            account_growth=account_growth,
                            account_growth_percentage=account_growth_pct,
                            total_portfolio_pnl=self.account.realized_pnl,
                            win_rate=self.account.win_rate
                        )
                    except Exception as e:
                        self.logger.error(f"Failed to send position close notification: {e}")
                
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
            for symbol, price_dict in prices.items():
                # When updating price cache
                self._update_cache(self._price_cache, symbol, price_dict)
            
            # Update position PnLs
            self._update_position_pnls(prices)
            
        except Exception as e:
            self.logger.error(f"Error updating prices: {e}")
    
    async def get_account_summary_async(self) -> Dict[str, Any]:
        """Get account summary asynchronously with live PnL calculations"""
        if not self.account:
            return {}
        
        # Calculate live unrealized PnL from open positions
        open_positions = [p for p in self.positions.values() if p.status == PositionStatus.OPEN]
        total_unrealized_pnl = 0.0
        
        # Update PnL with latest prices for each open position
        for position in open_positions:
            if position.symbol in self._price_cache:
                current_price = self._price_cache[position.symbol].get("price", 0.0)
                if current_price > 0:
                    position.calculate_pnl(current_price)
            total_unrealized_pnl += position.pnl
        
        # Calculate total portfolio value (balance + unrealized PnL)
        total_portfolio_value = self.account.current_balance + total_unrealized_pnl
        
        # Calculate total PnL (realized + unrealized)
        total_pnl = self.account.realized_pnl + total_unrealized_pnl
        
        # Calculate total return percentage
        total_return_pct = 0.0
        if self.account.initial_balance > 0:
            total_return_pct = ((total_portfolio_value - self.account.initial_balance) / self.account.initial_balance) * 100
        
        # Calculate account growth (can be negative)
        account_growth = total_portfolio_value - self.account.initial_balance
        account_growth_pct = 0.0
        if self.account.initial_balance > 0:
            account_growth_pct = (account_growth / self.account.initial_balance) * 100
        
        # Calculate daily win rate from today's closed positions
        today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_closed_positions = []
        daily_profitable_trades = 0
        daily_total_trades = 0
        
        for position in self.positions.values():
            if (position.status == PositionStatus.CLOSED and 
                position.exit_time and 
                position.exit_time.strftime('%Y-%m-%d') == today_date):
                today_closed_positions.append(position)
                daily_total_trades += 1
                if position.pnl > 0:
                    daily_profitable_trades += 1
        
        daily_win_rate = 0.0
        if daily_total_trades > 0:
            daily_win_rate = (daily_profitable_trades / daily_total_trades) * 100
        
        # Calculate total positive and negative P&L from all positions
        total_positive_pnl = 0.0
        total_negative_pnl = 0.0
        
        for position in self.positions.values():
            pnl = position.pnl
            if pnl > 0:
                total_positive_pnl += pnl
            elif pnl < 0:
                total_negative_pnl += pnl
        
        summary = {
            "account_id": self.account.id,
            "name": self.account.name,
            "initial_balance": self.account.initial_balance,
            "current_balance": self.account.current_balance,
            "available_balance": self.account.current_balance,  # For frontend compatibility
            "total_balance": total_portfolio_value,  # Balance + unrealized PnL
            "total_trades": self.account.total_trades,
            "profitable_trades": self.account.profitable_trades,
            "losing_trades": self.account.losing_trades,
            "win_rate": self.account.win_rate,
            "daily_win_rate": daily_win_rate,
            "daily_profitable_trades": daily_profitable_trades,
            "daily_losing_trades": daily_total_trades - daily_profitable_trades,
            "realized_pnl": self.account.realized_pnl,
            "unrealized_pnl": total_unrealized_pnl,
            "total_pnl": total_pnl,  # Realized + Unrealized
            "total_return_percentage": total_return_pct,
            "account_growth": account_growth,  # Can be negative
            "account_growth_percentage": account_growth_pct,  # Can be negative
            "daily_trades_count": self.account.daily_trades_count,
            "daily_trades_limit": self.account.daily_trades_limit,
            "total_margin_used": self.account.total_margin_used,
            "total_positive_pnl": total_positive_pnl,
            "total_negative_pnl": total_negative_pnl,
            "brokerage_charges": self.account.brokerage_charges,
            "open_positions": len(open_positions),  # Frontend compatible
            "open_positions_count": len(open_positions),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
        return summary
    
    async def get_positions_summary_async(self) -> Dict[str, Any]:
        """Get positions summary asynchronously with enhanced position data"""
        open_positions = []
        closed_positions = []
        total_unrealized_pnl = 0.0
        
        for position in self.positions.values():
            pos_data = position.to_dict()
            
            # Add current price and recalculate PnL for live positions
            if position.symbol in self._price_cache:
                current_price = self._price_cache[position.symbol].get("price", 0.0)
                pos_data["current_price"] = current_price
                
                # Recalculate PnL with current price for open positions
                if position.status == PositionStatus.OPEN and current_price > 0:
                    position.calculate_pnl(current_price)
                    pos_data["pnl"] = position.pnl
                    pos_data["pnl_percentage"] = position.pnl_percentage
                    total_unrealized_pnl += position.pnl
            else:
                pos_data["current_price"] = position.exit_price if position.exit_price else position.entry_price
            
            # Enhanced position data for frontend
            pos_data.update({
                "open_price": position.entry_price,  # Frontend compatibility
                "close_price": position.exit_price,  # Will be None for open positions
                "side": position.position_type.value,  # LONG/SHORT for frontend
                "size": position.quantity,  # Frontend compatibility
                "open_time": position.entry_time.isoformat() if position.entry_time else None,
                "exit_time": position.exit_time.isoformat() if position.exit_time else None,
                "running_time": self._calculate_running_time(position) if position.status == PositionStatus.OPEN else None,
                "margin_usage_pct": position.calculate_margin_usage(pos_data["current_price"], self.account.current_balance) if position.status == PositionStatus.OPEN else 0.0,
                
                # Pyramiding and Trailing data
                "original_quantity": position.original_quantity,
                "total_quantity": position.total_quantity,
                "average_entry_price": position.average_entry_price,
                "pyramid_count": position.pyramid_count,
                "trailing_count": position.trailing_count,
                "remaining_quantity": position.remaining_quantity,
                "realized_pnl": position.realized_pnl,
                "unrealized_pnl": position.unrealized_pnl,
                "average_exit_price": position.average_exit_price,
                
                # Enhanced display info
                "is_pyramided": position.pyramid_count > 0,
                "is_trailed": position.trailing_count > 0,
                "has_partial_closes": position.trailing_count > 0 or position.realized_pnl != 0.0
            })
            
            if position.status == PositionStatus.OPEN:
                open_positions.append(pos_data)
            else:
                closed_positions.append(pos_data)
        
        # Sort positions
        open_positions.sort(key=lambda x: x.get("entry_time", ""), reverse=True)
        closed_positions.sort(key=lambda x: x.get("exit_time", ""), reverse=True)
        
        return {
            "open_positions": open_positions,
            "closed_positions": closed_positions[:10],  # Last 10
            "total_open": len(open_positions),
            "total_closed": len(closed_positions),
            "total_unrealized_pnl": total_unrealized_pnl
        }
    
    def _calculate_running_time(self, position: Position) -> str:
        """Calculate how long a position has been running"""
        if not position.entry_time:
            return "Unknown"
        
        now = datetime.now(timezone.utc)
        delta = now - position.entry_time
        
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    
    def has_open_position_for_symbol(self, symbol: str) -> bool:
        """Check if there's already an open position for the given symbol"""
        try:
            for position in self.positions.values():
                if position.symbol == symbol and position.status == PositionStatus.OPEN:
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error checking open position for {symbol}: {e}")
            return False
    
    def get_open_position_for_symbol(self, symbol: str) -> Optional[Position]:
        """Get the open position for a specific symbol if it exists"""
        try:
            for position in self.positions.values():
                if position.symbol == symbol and position.status == PositionStatus.OPEN:
                    return position
            return None
        except Exception as e:
            self.logger.error(f"Error getting open position for {symbol}: {e}")
            return None
    
    def get_open_positions_count_by_symbol(self) -> Dict[str, int]:
        """Get count of open positions grouped by symbol"""
        try:
            symbol_counts = {}
            for position in self.positions.values():
                if position.status == PositionStatus.OPEN:
                    symbol = position.symbol
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            return symbol_counts
        except Exception as e:
            self.logger.error(f"Error getting position counts by symbol: {e}")
            return {}

    async def get_position_orders(self, position_id: str) -> List[Dict[str, Any]]:
        """Get all orders for a specific position"""
        try:
            return await self.mongodb_client.load_orders(position_id=position_id)
        except Exception as e:
            self.logger.error(f"Error loading position orders: {e}")
            return []

    async def get_symbol_orders(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all orders for a specific symbol"""
        try:
            return await self.mongodb_client.load_orders_by_symbol(symbol=symbol, limit=limit)
        except Exception as e:
            self.logger.error(f"Error loading symbol orders: {e}")
            return []
    
    async def delete_all_data(self) -> bool:
        """Delete all trading data from MongoDB"""
        try:
            success = await self.mongodb_client.delete_all_data()
            if success:
                # Reset in-memory data
                self.positions.clear()
                self._position_cache.clear()
                self._price_cache.clear() # Clear price cache as well
                self._trade_stats = {
                    "total_requests": 0,
                    "successful_trades": 0,
                    "failed_trades": 0,
                    "avg_execution_time": 0.0
                }
                
                # Reinitialize account
                await self._initialize_account()
                
                self.logger.info("✅ All trading data deleted successfully")
                return True
            else:
                self.logger.error("❌ Failed to delete trading data")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error deleting data: {e}")
            return False
    
    # Private methods
    def _validate_trade_request(self, trade_request: TradeRequest) -> bool:
        """Validate trade request"""
        self.logger.info(f"📋 Validating trade: signal={trade_request.signal}, price={trade_request.price}, qty={trade_request.quantity}, conf={trade_request.confidence}%")
        
        if trade_request.signal not in ['BUY', 'SELL']:
            trade_request.error_message = f"Invalid signal: {trade_request.signal} (expected 'BUY' or 'SELL')"
            return False
        
        if trade_request.price <= 0:
            trade_request.error_message = f"Invalid price: {trade_request.price}"
            return False
        
        if trade_request.quantity <= 0:
            trade_request.error_message = f"Invalid quantity: {trade_request.quantity}"
            return False
        
        min_conf = self.trading_config["min_confidence"]
        if trade_request.confidence < min_conf:
            trade_request.error_message = f"Low confidence: {trade_request.confidence}% (minimum: {min_conf}%)"
            return False
        
        self.logger.info(f"✅ Trade validation passed")
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
        
        # Position value calculation (no size limits, handled by risk manager)
        position_value = trade_request.price * trade_request.quantity
        
        # Check if position already exists for symbol
        for position in self.positions.values():
            if position.symbol == trade_request.symbol and position.status == PositionStatus.OPEN:
                trade_request.error_message = f"Position already open for {trade_request.symbol}"
                return False
        
        return True
    
    async def _execute_trade_simple(self, trade_request: TradeRequest) -> bool:
        """Execute trade with dummy data and MongoDB persistence"""
        try:
            # Calculate position details
            position_value = trade_request.price * trade_request.quantity
            margin_required = position_value / trade_request.leverage
            trading_fee = margin_required * self.trading_config["trading_fee_pct"]
            
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
            position.leverage = trade_request.leverage if trade_request.leverage and trade_request.leverage > 0 else self.trading_config["default_leverage"]
            position.margin_used = margin_required
            position.trading_fee = trading_fee
            
            # Initialize pyramiding fields
            position.original_quantity = trade_request.quantity
            position.total_quantity = trade_request.quantity
            position.average_entry_price = trade_request.price
            position.pyramid_count = 0
            
            # Initialize trailing fields
            position.trailing_count = 0
            position.remaining_quantity = trade_request.quantity
            position.realized_pnl = 0.0
            position.unrealized_pnl = 0.0
            position.average_exit_price = 0.0
            
            # Calculate risk levels - 1% SL and 3% Target
            if position.position_type == PositionType.LONG:
                position.stop_loss = trade_request.price * (1 - 0.01)  # 1% below entry
                position.target = trade_request.price * (1 + 0.03)     # 3% above entry
            else:
                position.stop_loss = trade_request.price * (1 + 0.01)  # 1% above entry  
                position.target = trade_request.price * (1 - 0.03)     # 3% below entry
            
            # Calculate initial PnL
            position.calculate_pnl(trade_request.price)
            
            # Update account
            self.account.current_balance -= total_required
            self.account.total_margin_used += margin_required
            self.account.brokerage_charges += trading_fee
            self.account.total_trades += 1
            self.account.daily_trades_count += 1
            
            # Save position to MongoDB
            await self.mongodb_client.save_position(position.to_dict())
            
            # Save position to memory
            self.positions[position.id] = position
            trade_request.position_id = position.id
            
            # Create initial trade orders
            await self._create_initial_trade_orders(position)
            
            return True
            
        except Exception as e:
            trade_request.error_message = str(e)
            return False
    
    async def _close_position_simple(self, position_id: str, exit_price: float, reason: str) -> bool:
        """Close position with dummy data and MongoDB persistence"""
        try:
            position = self.positions.get(position_id)
            if not position or position.status != PositionStatus.OPEN:
                return False
            
            # Close position
            position.close_position(exit_price)
            position.notes = reason
            
            # Calculate exit fee
            exit_fee = position.trading_fee * self.trading_config["exit_fee_multiplier"]
            
            # Update account
            self.account.current_balance += position.margin_used + position.pnl - exit_fee
            self.account.total_margin_used -= position.margin_used
            
            if exit_fee > 0:
                self.account.brokerage_charges += exit_fee
            
            # Update realized P&L and statistics
            self.account.realized_pnl += position.pnl
            
            if position.pnl > 0:
                self.account.profitable_trades += 1
            else:
                self.account.losing_trades += 1
            
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
    
    def _update_cache(self, cache, key, value):
        cache[key] = value
        if len(cache) > self._cache_max_size:
            cache.popitem(last=False)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            **self._trade_stats,
            "total_positions": len(self.positions),
            "open_positions": len([p for p in self.positions.values() if p.status == PositionStatus.OPEN]),
            "account_balance": self.account.current_balance if self.account else 0.0,
            "mongodb_connected": self.mongodb_client.is_connected
        }
    
    # ==================== INITIAL TRADE ORDERS ====================
    
    async def _create_initial_trade_orders(self, position: Position):
        """Create initial BUY, STOP_LOSS, and TARGET orders for new position"""
        try:
            # Create BUY order (already executed)
            buy_order = Order(
                position_id=position.id,
                symbol=position.symbol,
                order_type=OrderType.BUY,
                status=OrderStatus.EXECUTED,
                price=position.entry_price,
                quantity=position.quantity,
                executed_price=position.entry_price,
                executed_quantity=position.quantity,
                leverage=position.leverage,
                margin_used=position.margin_used,
                trading_fee=position.trading_fee,
                strategy_name=position.strategy_name,
                confidence=100.0,
                execution_time=position.entry_time,
                notes=f"Initial {position.position_type.value} entry"
            )
            await self.mongodb_client.save_order(buy_order.to_dict())
            
            # Create STOP_LOSS order (pending)
            if position.stop_loss:
                sl_order = Order(
                    position_id=position.id,
                    symbol=position.symbol,
                    order_type=OrderType.STOP_LOSS,
                    status=OrderStatus.PENDING,
                    price=position.stop_loss,
                    quantity=position.quantity,
                    leverage=position.leverage,
                    strategy_name=position.strategy_name,
                    confidence=100.0,
                    notes=f"Initial SL @ ${position.stop_loss:.2f} (-1%)"
                )
                await self.mongodb_client.save_order(sl_order.to_dict())
            
            # Create TARGET order (pending)
            if position.target:
                target_order = Order(
                    position_id=position.id,
                    symbol=position.symbol,
                    order_type=OrderType.TARGET,
                    status=OrderStatus.PENDING,
                    price=position.target,
                    quantity=position.quantity,
                    leverage=position.leverage,
                    strategy_name=position.strategy_name,
                    confidence=100.0,
                    notes=f"Initial Target @ ${position.target:.2f} (+3%)"
                )
                await self.mongodb_client.save_order(target_order.to_dict())
            
            self.logger.info(f"📋 Created initial orders for {position.symbol}: BUY, SL, TARGET")
            
        except Exception as e:
            self.logger.error(f"Failed to create initial trade orders: {e}")
    
    
    async def _update_trailing_orders(self, position: Position, current_price: float):
        """Update stop loss and target for trailing - using config values"""
        try:
            stop_offset = self.trading_config.get("trailing_stop_offset", 0.5) / 100.0  # 0.5%
            target_offset = self.trading_config.get("trailing_target_offset", 1.0) / 100.0  # 1%
            
            if position.position_type == PositionType.LONG:
                new_stop_loss = current_price * (1 - stop_offset)  # current - 0.5%
                new_target = current_price * (1 + target_offset)   # current + 1%
            else:
                new_stop_loss = current_price * (1 + stop_offset)  # current + 0.5%
                new_target = current_price * (1 - target_offset)   # current - 1%
            
            # Update position stop loss and target
            position.stop_loss = new_stop_loss
            position.target = new_target
            
            # Create stop loss update order
            sl_order = Order(
                position_id=position.id,
                symbol=position.symbol,
                order_type=OrderType.STOP_LOSS,
                status=OrderStatus.PENDING,
                price=new_stop_loss,
                quantity=position.remaining_quantity,
                leverage=position.leverage,
                strategy_name=position.strategy_name,
                confidence=100.0,
                notes=f"Trailing SL #{position.trailing_count} @ ${new_stop_loss:.2f} (current-0.5%)"
            )
            await self.mongodb_client.save_order(sl_order.to_dict())
            
            # Create target update order  
            target_order = Order(
                position_id=position.id,
                symbol=position.symbol,
                order_type=OrderType.TARGET,
                status=OrderStatus.PENDING,
                price=new_target,
                quantity=position.remaining_quantity,
                leverage=position.leverage,
                strategy_name=position.strategy_name,
                confidence=100.0,
                notes=f"Trailing Target #{position.trailing_count} @ ${new_target:.2f} (current+1%)"
            )
            await self.mongodb_client.save_order(target_order.to_dict())
            
            self.logger.info(f"🎯 Trailing updated: SL=${new_stop_loss:.2f} (-0.5%), Target=${new_target:.2f} (+1%)")
            
        except Exception as e:
            self.logger.error(f"Failed to update trailing orders: {e}")
    
    # ==================== PYRAMIDING & TRAILING LOGIC ====================
    
    async def check_pyramiding_opportunity(self, position: Position, signal_confidence: float) -> bool:
        """Check if we should add to position (pyramiding)"""
        try:
            # Check if pyramiding is enabled
            if not self.trading_config.get("enable_pyramiding", True):
                return False
            
            # Check confidence threshold
            min_confidence = self.trading_config.get("pyramiding_min_confidence", 90.0)
            if signal_confidence < min_confidence:
                return False
            
            # Check pyramid limits
            max_adds = self.trading_config.get("pyramiding_max_adds", 3)
            if position.pyramid_count >= max_adds:
                return False
            
            # Check if position is profitable (optional safety check)
            current_price = self._price_cache.get(position.symbol, {}).get("price", 0.0)
            if current_price > 0:
                position.calculate_pnl(current_price)
                # Only pyramid if position is profitable
                if position.unrealized_pnl <= 0:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking pyramiding opportunity: {e}")
            return False
    
    async def execute_pyramiding(self, position: Position, current_price: float, signal_confidence: float):
        """Execute pyramiding - add to existing position"""
        try:
            # Check if we should pyramid
            if not await self.check_pyramiding_opportunity(position, signal_confidence):
                return False
            
            # Calculate quantity to add (percentage of original quantity)
            add_percentage = self.trading_config.get("pyramiding_add_percentage", 50.0) / 100.0
            add_quantity = position.original_quantity * add_percentage
            
            # Calculate margin required
            add_margin = (add_quantity * current_price) / position.leverage
            
            # Check if we have enough balance
            if self.account.current_balance < add_margin:
                self.logger.warning(f"Insufficient balance for pyramiding {position.symbol}")
                return False
            
            # Create and execute pyramid add order
            pyramid_order = Order(
                position_id=position.id,
                symbol=position.symbol,
                order_type=OrderType.PYRAMID_ADD,
                status=OrderStatus.EXECUTED,
                price=current_price,
                quantity=add_quantity,
                executed_price=current_price,
                executed_quantity=add_quantity,
                leverage=position.leverage,
                margin_used=add_margin,
                strategy_name=position.strategy_name,
                confidence=signal_confidence,
                execution_time=datetime.now(timezone.utc),
                notes=f"Pyramid add #{position.pyramid_count + 1} with {signal_confidence:.1f}% confidence"
            )
            await self.mongodb_client.save_order(pyramid_order.to_dict())
            
            # Update position with pyramiding
            position.add_to_position(add_quantity, current_price, add_margin)
            
            # Update account balance
            self.account.current_balance -= add_margin
            
            # Save updated position and account
            await self.mongodb_client.save_position(position.to_dict())
            await self.mongodb_client.save_account(self.account.to_dict())
            
            self.logger.info(f"🔺 Pyramiding executed: Added {add_quantity} to {position.symbol} at ${current_price:.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Pyramiding execution error: {e}")
            return False
    
    async def check_trailing_opportunity(self, position: Position, current_price: float) -> bool:
        """Check if we should partially close position (trailing)"""
        try:
            # Check if trailing is enabled
            if not self.trading_config.get("enable_trailing", True):
                return False
            
            # Check if we have remaining quantity to close
            remaining_qty = position.remaining_quantity if position.remaining_quantity > 0 else position.total_quantity
            if remaining_qty <= 0:
                return False
            
            # Check trailing limits
            max_trailing = self.trading_config.get("trailing_max_count", 5)
            if position.trailing_count >= max_trailing:
                return False
            
            # Check if target price is hit
            if position.target and current_price >= position.target:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking trailing opportunity: {e}")
            return False
    
    async def execute_trailing(self, position: Position, current_price: float):
        """Execute trailing - partially close position"""
        try:
            # Check if we should trail
            if not await self.check_trailing_opportunity(position, current_price):
                return False
            
            # Calculate quantity to close (percentage of remaining quantity)
            exit_percentage = self.trading_config.get("trailing_exit_percentage", 50.0) / 100.0
            remaining_qty = position.remaining_quantity if position.remaining_quantity > 0 else position.quantity
            close_quantity = remaining_qty * exit_percentage
            
            # Create and execute trailing close order
            trailing_order = Order(
                position_id=position.id,
                symbol=position.symbol,
                order_type=OrderType.TRAILING_CLOSE,
                status=OrderStatus.EXECUTED,
                price=current_price,
                quantity=close_quantity,
                executed_price=current_price,
                executed_quantity=close_quantity,
                leverage=position.leverage,
                strategy_name=position.strategy_name,
                confidence=100.0,
                execution_time=datetime.now(timezone.utc),
                notes=f"Trailing close #{position.trailing_count + 1} - target hit ({exit_percentage*100:.0f}% exit)"
            )
            await self.mongodb_client.save_order(trailing_order.to_dict())
            
            # Partially close position
            position.partial_close_position(close_quantity, current_price, f"Trailing close: target hit")
            
            # Calculate profit from partial close
            effective_entry = position.average_entry_price if position.average_entry_price > 0 else position.entry_price
            profit = (current_price - effective_entry) * close_quantity if position.position_type == PositionType.LONG else (effective_entry - current_price) * close_quantity
            
            # Update account balance with profit
            self.account.current_balance += profit
            self.account.realized_pnl += profit
            
            # Update new stop loss and target based on current price
            await self._update_trailing_orders(position, current_price)
            
            # Save updated position and account
            await self.mongodb_client.save_position(position.to_dict())
            await self.mongodb_client.save_account(self.account.to_dict())
            
            self.logger.info(f"📉 Trailing executed: Closed {close_quantity} of {position.symbol} at ${current_price:.2f}, profit: ${profit:.2f}")
            return True
            
        except Exception as e:
            self.logger.error(f"Trailing execution error: {e}")
            return False 