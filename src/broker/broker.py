"""
Unified Broker System - Professional Trading Platform
Handles all broker operations including account, positions, trades, and risk management
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from src.broker.models import Account, Position, PositionType, PositionStatus
from src.config import get_settings
# Removed message formatter dependency for simplified system
import uuid
import json

class BrokerLogger:
    """Enhanced logging system for broker operations"""
    
    def __init__(self, module_name: str = "Broker", websocket_server=None):
        self.module_name = module_name
        self.websocket_server = websocket_server
        self.logger = logging.getLogger(f"broker.{module_name.lower()}")
    
    def log(self, level: str, message: str, data: Any = None, execution_time: float = None):
        """Enhanced logging with execution time and data"""
        timestamp = datetime.now(timezone.utc)
        
        # Format log entry
        log_entry = {
            "module": self.module_name,
            "timestamp": timestamp.isoformat(),
            "execution_time_ms": round(execution_time * 1000, 2) if execution_time else None,
            "level": level.upper(),
            "message": message,
            "data": data
        }
        
        # Log to file
        log_msg = f"[{self.module_name}] {message}"
        if execution_time:
            log_msg += f" (executed in {execution_time*1000:.2f}ms)"
        
        getattr(self.logger, level.lower())(log_msg)
        
        # Send to WebSocket
        if self.websocket_server:
            self.websocket_server.queue_message({
                "type": "broker_log",
                "data": log_entry
            })

class UnifiedBroker:
    """
    Unified Broker System - All-in-one trading platform
    Handles account management, positions, trades, and real-time monitoring
    """
    
    def __init__(self, websocket_server=None):
        """Initialize unified broker system"""
        self.settings = get_settings()
        self.websocket_server = websocket_server
        self.logger = BrokerLogger("Broker", websocket_server)
        
        # Database connection
        self.client = None
        self.db = None
        self.accounts_collection = None
        self.positions_collection = None
        self.is_connected = False
        
        # Core data
        self.account: Optional[Account] = None
        self.positions: Dict[str, Position] = {}  # position_id -> Position
        self.open_positions: Dict[str, Position] = {}  # symbol -> Position
        self.current_prices: Dict[str, Dict] = {}  # symbol -> price_data
        
        # Trading settings
        self.stop_loss_percentage = self.settings.BROKER_STOP_LOSS_PCT
        self.target_percentage = self.settings.BROKER_TARGET_PCT
        self.min_confidence_threshold = self.settings.BROKER_MIN_CONFIDENCE
        
        # Monitoring
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._last_update = time.time()
        
        # Performance tracking
        self._operation_times = {}
        
    def _time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        class OperationTimer:
            def __init__(self, broker, name):
                self.broker = broker
                self.name = name
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                execution_time = time.time() - self.start_time
                self.broker._operation_times[self.name] = execution_time
        
        return OperationTimer(self, operation_name)
    
    def connect(self) -> bool:
        """Connect to MongoDB database"""
        with self._time_operation("database_connect"):
            try:
                self.client = MongoClient(
                    self.settings.MONGODB_URI,
                    serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT * 1000
                )
                
                # Test connection
                self.client.admin.command('ping')
                
                # Get database and collections with text prefix
                self.db = self.client[self.settings.DATABASE_NAME]
                self.accounts_collection = self.db['text_trading_accounts']
                self.positions_collection = self.db['text_trading_positions']
                
                self.is_connected = True
                
                exec_time = self._operation_times.get("database_connect", 0)
                self.logger.log("info", "Database connected successfully", 
                              {"mongodb_uri": self.settings.MONGODB_URI}, exec_time)
                return True
                
            except Exception as e:
                exec_time = self._operation_times.get("database_connect", 0)
                self.logger.log("error", f"Database connection failed: {e}", 
                              {"error": str(e)}, exec_time)
                return False
    
    def initialize_account(self, account_id: str = "main", initial_balance: float = 10000.0) -> bool:
        """Initialize or load trading account"""
        with self._time_operation("account_initialize"):
            try:
                if not self.is_connected:
                    if not self.connect():
                        return False
                
                # Try to load existing account
                account_doc = self.accounts_collection.find_one({"id": account_id})
                
                if account_doc:
                    self.account = Account.from_dict(account_doc)
                    self.logger.log("info", f"Loaded existing account: {account_id}", 
                                  {"balance": self.account.current_balance})
                else:
                    # Create new account
                    self.account = Account()
                    self.account.id = account_id
                    self.account.name = f"Trading Account {account_id}"
                    self.account.initial_balance = initial_balance
                    self.account.current_balance = initial_balance
                    self.account.daily_trades_limit = 5
                    self.account.max_position_size = initial_balance * 0.1  # 10% max per trade
                    self.account.risk_per_trade = 0.02  # 2% risk per trade
                    self.account.max_leverage = self.settings.BROKER_MAX_LEVERAGE
                    
                    # Save new account
                    self._save_account()
                    
                    exec_time = self._operation_times.get("account_initialize", 0)
                    self.logger.log("info", f"Created new account: {account_id}", 
                                  {"initial_balance": initial_balance}, exec_time)
                
                return True
                
            except Exception as e:
                exec_time = self._operation_times.get("account_initialize", 0)
                self.logger.log("error", f"Account initialization failed: {e}", 
                              {"error": str(e)}, exec_time)
                return False
    
    def load_positions(self) -> bool:
        """Load all positions from database"""
        with self._time_operation("positions_load"):
            try:
                if not self.is_connected:
                    return False
                
                # Clear existing positions
                self.positions.clear()
                self.open_positions.clear()
                
                # Load from database
                cursor = self.positions_collection.find({}).sort("created_at", -1)
                
                loaded_count = 0
                open_count = 0
                
                for doc in cursor:
                    try:
                        position = Position.from_dict(doc)
                        self.positions[position.id] = position
                        
                        if position.status == PositionStatus.OPEN:
                            self.open_positions[position.symbol] = position
                            open_count += 1
                        
                        loaded_count += 1
                        
                    except Exception as e:
                        self.logger.log("warning", f"Failed to load position: {e}")
                
                exec_time = self._operation_times.get("positions_load", 0)
                self.logger.log("info", f"Loaded {loaded_count} positions ({open_count} open)", 
                              {"total": loaded_count, "open": open_count}, exec_time)
                
                return True
                
            except Exception as e:
                exec_time = self._operation_times.get("positions_load", 0)
                self.logger.log("error", f"Failed to load positions: {e}", 
                              {"error": str(e)}, exec_time)
                return False
    
    def execute_trade(self, signal: str, symbol: str, current_price: float, 
                     confidence: float = 100.0, strategy_name: str = "", 
                     leverage: float = 1.0, analysis_id: str = "") -> bool:
        """Execute a trade based on signal"""
        with self._time_operation("trade_execute"):
            try:
                signal = signal.upper().strip()
                
                # Validate signal
                if signal not in ['BUY', 'SELL']:
                    self.logger.log("warning", f"Invalid signal: {signal}", 
                                  {"signal": signal, "symbol": symbol})
                    return False
                
                # Check confidence threshold
                if confidence < self.min_confidence_threshold:
                    self.logger.log("warning", f"Low confidence signal ignored", 
                                  {"confidence": confidence, "threshold": self.min_confidence_threshold})
                    return False
                
                # Check daily trades limit
                if not self._can_trade_today():
                    return False
                
                # Check if we can open this position
                position_type = PositionType.LONG if signal == 'BUY' else PositionType.SHORT
                if symbol in self.open_positions:
                    self.logger.log("warning", f"Position already open for {symbol}")
                    return False
                
                # Calculate position size and margin
                position_value, margin_required, trading_fee = self._calculate_position_size(
                    current_price, leverage
                )
                
                if position_value <= 0:
                    self.logger.log("warning", "Invalid position size calculated")
                    return False
                
                # Reserve margin
                if not self._reserve_margin(margin_required, trading_fee):
                    return False
                
                # Calculate risk levels
                stop_loss, target = self._calculate_risk_levels(
                    current_price, position_type
                )
                
                # Create position
                position = Position()
                position.symbol = symbol
                position.position_type = position_type
                position.entry_price = current_price
                position.quantity = position_value / current_price
                position.invested_amount = position_value
                position.strategy_name = strategy_name
                position.stop_loss = stop_loss
                position.target = target
                position.leverage = leverage
                position.margin_used = margin_required
                position.trading_fee = trading_fee
                position.analysis_id = analysis_id
                position.status = PositionStatus.OPEN
                
                # Calculate initial PnL
                position.calculate_pnl(current_price)
                
                # Save position
                if self._save_position(position):
                    self.positions[position.id] = position
                    self.open_positions[symbol] = position
                    
                    # Update account stats
                    self.account.total_trades += 1
                    self.account.daily_trades_count += 1
                    self.account.last_trade_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    self._save_account()
                    
                    exec_time = self._operation_times.get("trade_execute", 0)
                    self.logger.log("info", f"Trade executed: {signal} {symbol}", {
                        "position_id": position.id,
                        "entry_price": current_price,
                        "quantity": position.quantity,
                        "invested_amount": position_value,
                        "leverage": leverage,
                        "margin_used": margin_required,
                        "trading_fee": trading_fee,
                        "stop_loss": stop_loss,
                        "target": target,
                        "confidence": confidence,
                        "strategy": strategy_name
                    }, exec_time)
                    
                    return True
                else:
                    # Release margin if position creation failed
                    self._release_margin(margin_required, 0, -trading_fee)
                    return False
                
            except Exception as e:
                exec_time = self._operation_times.get("trade_execute", 0)
                self.logger.log("error", f"Trade execution failed: {e}", 
                              {"error": str(e), "symbol": symbol}, exec_time)
                return False
    
    def close_position(self, position_id: str, exit_price: float, reason: str = "Manual") -> bool:
        """Close a position"""
        with self._time_operation("position_close"):
            try:
                position = self.positions.get(position_id)
                if not position or position.status != PositionStatus.OPEN:
                    return False
                
                # Close position
                position.close_position(exit_price)
                position.notes = reason
                
                # Calculate exit fee
                exit_fee = position.trading_fee * 0.5
                
                # Release margin with PnL
                self._release_margin(position.margin_used, position.pnl, exit_fee)
                
                # Update account statistics
                if position.pnl > 0:
                    self.account.profitable_trades += 1
                    self.account.total_profit += position.pnl
                else:
                    self.account.losing_trades += 1
                    self.account.total_loss += abs(position.pnl)
                
                # Calculate win rate
                if self.account.total_trades > 0:
                    self.account.win_rate = (self.account.profitable_trades / self.account.total_trades) * 100
                
                # Save updates
                self._save_position(position)
                self._save_account()
                
                # Remove from open positions
                if position.symbol in self.open_positions:
                    del self.open_positions[position.symbol]
                
                exec_time = self._operation_times.get("position_close", 0)
                self.logger.log("info", f"Position closed: {position.symbol}", {
                    "position_id": position_id,
                    "exit_price": exit_price,
                    "pnl": position.pnl,
                    "reason": reason,
                    "holding_time": position.holding_time
                }, exec_time)
                
                return True
                
            except Exception as e:
                exec_time = self._operation_times.get("position_close", 0)
                self.logger.log("error", f"Failed to close position: {e}", 
                              {"error": str(e), "position_id": position_id}, exec_time)
                return False
    
    def update_prices(self, prices: Dict[str, Dict]) -> None:
        """Update current market prices"""
        with self._time_operation("prices_update"):
            try:
                self.current_prices.update(prices)
                self._last_update = time.time()
                
                # Update PnL for open positions
                updated_positions = []
                for symbol, position in self.open_positions.items():
                    if symbol in prices:
                        current_price = prices[symbol]["price"]
                        old_pnl = position.pnl
                        position.calculate_pnl(current_price)
                        
                        if abs(position.pnl - old_pnl) > 0.01:  # Significant change
                            updated_positions.append({
                                "symbol": symbol,
                                "position_id": position.id,
                                "current_price": current_price,
                                "pnl": position.pnl,
                                "pnl_change": position.pnl - old_pnl
                            })
                
                exec_time = self._operation_times.get("prices_update", 0)
                # Only log P&L updates if there are significant changes or every 10th update
                if updated_positions and (len(updated_positions) > 1 or exec_time > 10):
                    self.logger.log("info", f"Updated {len(updated_positions)} position P&Ls", 
                                  {"updated_positions": updated_positions}, exec_time)
                
            except Exception as e:
                exec_time = self._operation_times.get("prices_update", 0)
                self.logger.log("error", f"Price update failed: {e}", 
                              {"error": str(e)}, exec_time)
    
    def check_risk_levels(self) -> List[str]:
        """Check all open positions for stop loss and target hits"""
        with self._time_operation("risk_check"):
            try:
                positions_to_close = []
                
                for symbol, position in self.open_positions.items():
                    if symbol not in self.current_prices:
                        continue
                    
                    current_price = self.current_prices[symbol]["price"]
                    
                    # Check stop loss
                    if position.stop_loss:
                        if ((position.position_type == PositionType.LONG and current_price <= position.stop_loss) or
                            (position.position_type == PositionType.SHORT and current_price >= position.stop_loss)):
                            
                            if self.close_position(position.id, current_price, "Stop Loss Hit"):
                                positions_to_close.append(position.id)
                    
                    # Check target
                    if position.target:
                        if ((position.position_type == PositionType.LONG and current_price >= position.target) or
                            (position.position_type == PositionType.SHORT and current_price <= position.target)):
                            
                            if self.close_position(position.id, current_price, "Target Hit"):
                                positions_to_close.append(position.id)
                    
                    # Check holding time (48 hours)
                    if self._check_holding_time_exceeded(position):
                        if self.close_position(position.id, current_price, "48 Hours Completed"):
                            positions_to_close.append(position.id)
                
                exec_time = self._operation_times.get("risk_check", 0)
                if positions_to_close:
                    self.logger.log("info", f"Risk check closed {len(positions_to_close)} positions", 
                                  {"closed_positions": positions_to_close}, exec_time)
                
                return positions_to_close
                
            except Exception as e:
                exec_time = self._operation_times.get("risk_check", 0)
                self.logger.log("error", f"Risk check failed: {e}", 
                              {"error": str(e)}, exec_time)
                return []
    
    def update_stop_loss(self, position_id: str, new_stop_loss: float) -> bool:
        """Update stop loss for a position"""
        with self._time_operation("stop_loss_update"):
            try:
                position = self.positions.get(position_id)
                if not position or position.status != PositionStatus.OPEN:
                    return False
                
                old_stop_loss = position.stop_loss
                position.stop_loss = new_stop_loss
                position.updated_at = datetime.now(timezone.utc)
                
                if self._save_position(position):
                    exec_time = self._operation_times.get("stop_loss_update", 0)
                    self.logger.log("info", f"Stop loss updated for {position.symbol}", {
                        "position_id": position_id,
                        "old_stop_loss": old_stop_loss,
                        "new_stop_loss": new_stop_loss
                    }, exec_time)
                    return True
                
                return False
                
            except Exception as e:
                exec_time = self._operation_times.get("stop_loss_update", 0)
                self.logger.log("error", f"Stop loss update failed: {e}", 
                              {"error": str(e), "position_id": position_id}, exec_time)
                return False
    
    def update_target(self, position_id: str, new_target: float) -> bool:
        """Update target for a position"""
        with self._time_operation("target_update"):
            try:
                position = self.positions.get(position_id)
                if not position or position.status != PositionStatus.OPEN:
                    return False
                
                old_target = position.target
                position.target = new_target
                position.updated_at = datetime.now(timezone.utc)
                
                if self._save_position(position):
                    exec_time = self._operation_times.get("target_update", 0)
                    self.logger.log("info", f"Target updated for {position.symbol}", {
                        "position_id": position_id,
                        "old_target": old_target,
                        "new_target": new_target
                    }, exec_time)
                    return True
                
                return False
                
            except Exception as e:
                exec_time = self._operation_times.get("target_update", 0)
                self.logger.log("error", f"Target update failed: {e}", 
                              {"error": str(e), "position_id": position_id}, exec_time)
                return False
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get comprehensive account summary"""
        if not self.account:
            return {}
        
        return {
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
            "algo_status": self.account.algo_status,
            "open_positions_count": len(self.open_positions),
            "total_unrealized_pnl": sum(pos.pnl for pos in self.open_positions.values()),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Get positions summary"""
        open_positions_list = []
        for position in self.open_positions.values():
            pos_data = position.to_dict()
            if position.symbol in self.current_prices:
                pos_data["current_price"] = self.current_prices[position.symbol]["price"]
            open_positions_list.append(pos_data)
        
        closed_positions_list = []
        for position in self.positions.values():
            if position.status == PositionStatus.CLOSED:
                closed_positions_list.append(position.to_dict())
        
        # Sort closed positions by exit time
        closed_positions_list.sort(
            key=lambda x: x.get("exit_time", ""), reverse=True
        )
        
        return {
            "open_positions": open_positions_list,
            "closed_positions": closed_positions_list[:10],  # Last 10
            "total_open": len(self.open_positions),
            "total_closed": len(closed_positions_list),
            "total_unrealized_pnl": sum(pos.pnl for pos in self.open_positions.values())
        }
    
    def start_monitoring(self) -> None:
        """Start real-time monitoring thread"""
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
        
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        
        self.logger.log("info", "Real-time monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop real-time monitoring"""
        self._stop_monitoring.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
        
        self.logger.log("info", "Real-time monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop (runs every 1-2 seconds)"""
        while not self._stop_monitoring.is_set():
            try:
                start_time = time.time()
                
                # Check risk levels for all open positions
                if self.open_positions:
                    closed_positions = self.check_risk_levels()
                    
                    if closed_positions:
                        self.logger.log("info", f"Monitoring closed {len(closed_positions)} positions")
                
                # Send status update via WebSocket
                if self.websocket_server:
                    status_update = {
                        "type": "broker_status",
                        "data": {
                            "account": self.get_account_summary(),
                            "positions": self.get_positions_summary(),
                            "current_prices": self.current_prices,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    }
                    self.websocket_server.queue_message(status_update)
                
                # Sleep for 1-2 seconds
                elapsed = time.time() - start_time
                sleep_time = max(0, 1.5 - elapsed)  # Target 1.5 second intervals
                time.sleep(sleep_time)
                
            except Exception as e:
                self.logger.log("error", f"Monitoring loop error: {e}")
                time.sleep(2)  # Wait before retrying
    
    # Private helper methods
    def _can_trade_today(self) -> bool:
        """Check if we can trade today"""
        if not self.account:
            return False
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Reset daily counter for new day
        if self.account.last_trade_date != today:
            self.account.daily_trades_count = 0
            self.account.last_trade_date = today
            self._save_account()
        
        if self.account.daily_trades_count >= self.account.daily_trades_limit:
            self.logger.log("warning", f"Daily trade limit reached: {self.account.daily_trades_count}/{self.account.daily_trades_limit}")
            return False
        
        return True
    
    def _calculate_position_size(self, price: float, leverage: float = 1.0) -> tuple[float, float, float]:
        """Calculate position size and margin requirements"""
        if not self.account:
            return 0.0, 0.0, 0.0
        
        # Calculate position size based on risk per trade
        risk_amount = self.account.current_balance * self.account.risk_per_trade
        max_position_value = min(risk_amount * leverage, self.account.max_position_size)
        
        # Calculate required margin
        required_margin = max_position_value / leverage
        
        # Calculate trading fee
        trading_fee = required_margin * self.settings.BROKER_TRADING_FEE_PCT
        
        # Ensure we have enough balance
        total_required = required_margin + trading_fee
        if total_required > self.account.current_balance:
            # Reduce position size to fit available balance
            available = self.account.current_balance * 0.95  # 5% buffer
            trading_fee = available * self.settings.BROKER_TRADING_FEE_PCT / (1 + self.settings.BROKER_TRADING_FEE_PCT)
            required_margin = available - trading_fee
            max_position_value = required_margin * leverage
        
        return max_position_value, required_margin, trading_fee
    
    def _calculate_risk_levels(self, entry_price: float, position_type: PositionType) -> tuple[float, float]:
        """Calculate stop loss and target levels"""
        if position_type == PositionType.LONG:
            stop_loss = entry_price * (1 - self.stop_loss_percentage)
            target = entry_price * (1 + self.target_percentage)
        else:  # SHORT
            stop_loss = entry_price * (1 + self.stop_loss_percentage)
            target = entry_price * (1 - self.target_percentage)
        
        return stop_loss, target
    
    def _reserve_margin(self, margin_amount: float, trading_fee: float) -> bool:
        """Reserve margin for a position"""
        if not self.account:
            return False
        
        total_required = margin_amount + trading_fee
        
        if total_required > self.account.current_balance:
            self.logger.log("warning", f"Insufficient balance: {self.account.current_balance:.2f} < {total_required:.2f}")
            return False
        
        self.account.current_balance -= total_required
        self.account.total_margin_used += margin_amount
        self.account.brokerage_charges += trading_fee
        
        return True
    
    def _release_margin(self, margin_amount: float, pnl: float, exit_fee: float = 0.0) -> None:
        """Release margin from closed position"""
        if not self.account:
            return
        
        self.account.current_balance += margin_amount + pnl - exit_fee
        self.account.total_margin_used -= margin_amount
        
        if exit_fee > 0:
            self.account.brokerage_charges += exit_fee
        
        # Ensure margin used doesn't go negative
        if self.account.total_margin_used < 0:
            self.account.total_margin_used = 0
    
    def _check_holding_time_exceeded(self, position: Position) -> bool:
        """Check if position exceeded maximum holding time"""
        try:
            entry_time = position.entry_time
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            holding_hours = (current_time - entry_time).total_seconds() / 3600
            
            return holding_hours >= self.settings.BROKER_MAX_HOLDING_HOURS
        except:
            return False
    
    def _save_account(self) -> bool:
        """Save account to database"""
        if not self.account or not self.is_connected:
            return False
        
        try:
            account_data = self.account.to_dict()
            result = self.accounts_collection.replace_one(
                {'id': self.account.id}, account_data, upsert=True
            )
            return result.acknowledged
        except Exception as e:
            self.logger.log("error", f"Failed to save account: {e}")
            return False
    
    def _save_position(self, position: Position) -> bool:
        """Save position to database"""
        if not self.is_connected:
            return False
        
        try:
            position_data = position.to_dict()
            result = self.positions_collection.replace_one(
                {'id': position.id}, position_data, upsert=True
            )
            return result.acknowledged
        except Exception as e:
            self.logger.log("error", f"Failed to save position: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from database and stop monitoring"""
        self.stop_monitoring()
        
        if self.account:
            self.account.algo_status = False
            self._save_account()
        
        if self.client:
            self.client.close()
        
        self.is_connected = False
        self.logger.log("info", "Broker system disconnected") 