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
from collections import defaultdict

class BrokerLogger:
    """Enhanced logging for broker operations"""
    
    def __init__(self):
        self.logger = logging.getLogger("broker.broker")
        
    def log(self, level: str, category: str, message: str, data: Any = None, execution_time: float = None):
        """Enhanced logging with execution time and data"""
        try:
            # Format log message
            log_msg = f"{level.upper()} - [Broker] {category} | {message}"
            if execution_time is not None:
                log_msg += f" (Time: {execution_time:.3f}s)"
                
            # Add data if provided
            if data:
                try:
                    data_str = json.dumps(data, default=str)
                    log_msg += f" | Data: {data_str}"
                except:
                    pass
            
            # Log using appropriate level
            log_func = getattr(self.logger, level.lower(), self.logger.info)
            log_func(log_msg)
            
        except Exception as e:
            # Fallback logging in case of errors
            self.logger.error(f"Logging error: {str(e)} | Original message: {message}")

    def disconnect(self):
        """Log broker disconnection"""
        self.log("info", "System", "Broker system disconnected")

class UnifiedBroker:
    """Unified broker implementation with enhanced monitoring and risk management"""
    
    def __init__(self):
        """Initialize broker components"""
        # Initialize logger
        self.logger = BrokerLogger()
        
        # Initialize threading components
        self._stop_event = threading.Event()
        self._monitoring_thread = None
        
        # Initialize connection state
        self.is_connected = False
        self.market_data_client = None
        
        # Initialize MongoDB components
        self.db_client = None
        self.db = None
        self.accounts_collection = None
        self.positions_collection = None
        
        # Initialize trading components
        self.account = None
        self.positions = {}
        self.current_prices = {}
        
        # Load settings
        self.settings = get_settings()
        
        # Risk parameters
        self.stop_loss_percentage = self.settings.BROKER_STOP_LOSS_PCT
        self.target_percentage = self.settings.BROKER_TARGET_PCT
        
        # Performance tracking
        self._operation_times = defaultdict(float)
        
        self.logger.log(
            "info",
            "Initialization",
            "Broker system initialized",
            execution_time=0.0
        )
        
    @property
    def open_positions(self) -> Dict[str, Position]:
        """Returns a dictionary of open positions"""
        with self._time_operation("get_open_positions"):
            return {p_id: p for p_id, p in self.positions.items() if p.status == PositionStatus.OPEN}
    
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
                return execution_time
        
        return OperationTimer(self, operation_name)
    
    def connect(self) -> bool:
        """Connect to trading system and initialize components"""
        with self._time_operation("database_connect") as timer:
            try:
                # Connect to MongoDB
                self.db_client = MongoClient(
                    self.settings.MONGODB_URI,
                    serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT * 1000
                )
                
                # Test connection
                self.db_client.admin.command('ping')
                
                # Get database and collections
                self.db = self.db_client[self.settings.DATABASE_NAME]
                self.accounts_collection = self.db['trading_accounts']
                self.positions_collection = self.db['trading_positions']
                
                self.is_connected = True
                
                self.logger.log(
                    "info",
                    "Database",
                    "Connection established successfully",
                    {"database": self.settings.DATABASE_NAME},
                    timer.__exit__(None, None, None)
                )
                
                return True
                
            except Exception as e:
                self.logger.log(
                    "error",
                    "Database",
                    "Connection failed",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return False
    
    def initialize_account(self, account_id: str = "main", initial_balance: float = 10000.0) -> bool:
        """Initialize or load trading account"""
        with self._time_operation("account_initialize") as timer:
            try:
                if not self.is_connected:
                    if not self.connect():
                        return False
                
                # Try to load existing account
                account_doc = self.accounts_collection.find_one({"id": account_id})
                
                if account_doc:
                    self.account = Account.from_dict(account_doc)
                    self.logger.log(
                        "info", "Account", f"Loaded existing account: {account_id}",
                        {"balance": self.account.current_balance},
                        timer.__exit__(None, None, None)
                    )
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
                    
                    self.logger.log(
                        "info", "Account", f"Created new account: {account_id}",
                        {"initial_balance": initial_balance},
                        timer.__exit__(None, None, None)
                    )
                
                return True
                
            except Exception as e:
                self.logger.log(
                    "error", "Account", "Initialization failed",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return False
    
    def load_positions(self) -> bool:
        """Load all positions from database"""
        with self._time_operation("positions_load") as timer:
            try:
                if not self.is_connected:
                    return False
                
                # Clear existing positions
                self.positions.clear()
                
                # Load from database
                cursor = self.positions_collection.find({}).sort("created_at", -1)
                
                loaded_count = 0
                
                for doc in cursor:
                    try:
                        position = Position.from_dict(doc)
                        self.positions[position.id] = position
                        loaded_count += 1
                        
                    except Exception as e:
                        self.logger.log(
                            "error", "Positions", "Failed to load position",
                            {"position_id": doc.get("id"), "error": str(e)}
                        )
                
                self.logger.log(
                    "info", "Positions", "Positions loaded from database",
                    {"total_loaded": loaded_count},
                    timer.__exit__(None, None, None)
                )
                return True
                
            except Exception as e:
                self.logger.log(
                    "error", "Positions", "Failed to load positions",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return False
    
    def execute_trade(self, signal: str, symbol: str, current_price: float, 
                     confidence: float = 100.0, strategy_name: str = "", 
                     leverage: float = 1.0, analysis_id: str = "") -> bool:
        """Execute a trade based on signal"""
        with self._time_operation("trade_execute"):
            try:
                signal = signal.upper().strip()
                
                self.logger.log("info", "Trade", f"🎯 Starting trade execution: {signal} {symbol} at ${current_price:.2f}", {
                    "signal": signal,
                    "symbol": symbol,
                    "price": current_price,
                    "confidence": confidence,
                    "leverage": leverage
                })
                
                # Validate signal
                if signal not in ['BUY', 'SELL']:
                    self.logger.log("warning", "Trade", f"❌ Invalid signal rejected: {signal} for {symbol}")
                    return False
                
                # Check confidence threshold
                if confidence < self.settings.BROKER_MIN_CONFIDENCE:
                    self.logger.log("warning", "Trade", f"❌ Low confidence signal rejected: {confidence}% < {self.settings.BROKER_MIN_CONFIDENCE}%")
                    return False
                
                # Check daily trades limit
                if not self._can_trade_today():
                    self.logger.log("warning", "Trade", f"❌ Daily trade limit reached: {self.account.daily_trades_count}/{self.account.daily_trades_limit}")
                    return False
                
                # Check if we can open this position
                position_type = PositionType.LONG if signal == 'BUY' else PositionType.SHORT
                
                # Check if we already have an open position for this symbol
                for pos in self.open_positions.values():
                    if pos.symbol == symbol:
                        self.logger.log("warning", "Trade", f"❌ Position already open for {symbol}")
                        return False
                
                # Calculate position size and margin
                position_value, margin_required, trading_fee = self._calculate_position_size(
                    current_price, leverage
                )
                
                self.logger.log("info", "Trade", f"💰 Position sizing calculated for {symbol}", {
                    "position_value": position_value,
                    "margin_required": margin_required,
                    "trading_fee": trading_fee,
                    "account_balance": self.account.current_balance
                })
                
                if position_value <= 0:
                    self.logger.log("warning", "Trade", f"❌ Invalid position size: ${position_value:.2f}")
                    return False
                
                # Reserve margin
                if not self._reserve_margin(margin_required, trading_fee):
                    self.logger.log("warning", "Trade", f"❌ Insufficient margin: need ${margin_required + trading_fee:.2f}, have ${self.account.current_balance:.2f}")
                    return False
                
                # Calculate risk levels
                stop_loss, target = self._calculate_risk_levels(
                    current_price, position_type
                )
                
                self.logger.log("info", "Trade", f"🎯 Risk levels set for {symbol}", {
                    "stop_loss": stop_loss,
                    "target": target,
                    "stop_loss_pct": self.stop_loss_percentage * 100,
                    "target_pct": self.target_percentage * 100
                })
                
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
                    
                    # Update account stats
                    self.account.total_trades += 1
                    self.account.daily_trades_count += 1
                    self.account.last_trade_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    self._save_account()
                    
                    exec_time = self._operation_times.get("trade_execute", 0)
                    self.logger.log("info", "Trade", f"✅ Trade executed successfully: {signal} {symbol}", {
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
                        "strategy": strategy_name,
                        "execution_time": f"{exec_time:.3f}s"
                    })
                    
                    return True
                else:
                    # Release margin if position creation failed
                    self._release_margin(margin_required, 0, -trading_fee)
                    self.logger.log("error", "Trade", f"❌ Failed to save position to database")
                    return False
                
            except Exception as e:
                exec_time = self._operation_times.get("trade_execute", 0)
                self.logger.log("error", "Trade", f"❌ Trade execution failed: {e}", {
                    "error": str(e), 
                    "symbol": symbol,
                    "signal": signal,
                    "execution_time": f"{exec_time:.3f}s"
                })
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
                
                # Update PnL for open positions
                updated_positions = []
                for symbol, position in self.positions.items():
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
                
                for symbol, position in self.positions.items():
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
            "open_positions_count": len(self.positions),
            "total_unrealized_pnl": sum(pos.pnl for pos in self.positions.values()),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Get positions summary"""
        open_positions_list = []
        for position in self.positions.values():
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
            "total_open": len(self.positions),
            "total_closed": len(closed_positions_list),
            "total_unrealized_pnl": sum(pos.pnl for pos in self.positions.values())
        }
    
    def start_monitoring(self) -> None:
        """Start real-time monitoring thread"""
        try:
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self.logger.log("warning", "Monitoring", "Monitoring already running")
                return
            
            self._stop_event.clear()
            self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self._monitoring_thread.start()
            
            self.logger.log("info", "Monitoring", "Real-time monitoring started")
            
        except Exception as e:
            self.logger.log(
                "error",
                "Monitoring",
                "Failed to start monitoring system",
                {"error": str(e)},
                execution_time=0.0
            )
    
    def stop_monitoring(self) -> None:
        """Stop monitoring thread"""
        try:
            self._stop_event.set()
            
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=2.0)
            
            self.logger.log("info", "Monitoring", "Monitoring system stopped")
            
        except Exception as e:
            self.logger.log(
                "error",
                "Monitoring",
                "Error stopping monitoring system",
                {"error": str(e)},
                execution_time=0.0
            )
    
    def _monitoring_loop(self):
        """Monitor broker operations and connections"""
        try:
            while not self._stop_event.is_set():
                try:
                    with self._time_operation("monitoring") as timer:
                        # Check database connection
                        if not self.is_connected:
                            self.logger.log(
                                "warning",
                                "Connection",
                                "Database connection lost",
                                execution_time=timer.execution_time
                            )
                            
                        # Check account status
                        if not self._check_account_status():
                            self.logger.log(
                                "warning",
                                "Account",
                                "Account status check failed",
                                execution_time=timer.execution_time
                            )
                            
                        # Sleep for monitoring interval
                        time.sleep(self.settings.MONITORING_INTERVAL)
                        
                except Exception as e:
                    self.logger.log(
                        "error",
                        "Monitoring",
                        "Monitoring loop error",
                        {"error": str(e)},
                        execution_time=0.0
                    )
                    time.sleep(1)
                    
        except Exception as e:
            self.logger.log(
                "error",
                "Monitoring",
                "Fatal error in monitoring loop",
                {"error": str(e)},
                execution_time=0.0
            )
    
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
        """Disconnect from trading system"""
        try:
            # Stop monitoring
            self.stop_monitoring()
            
            # Close database connection
            if self.db_client:
                self.db_client.close()
            
            self.is_connected = False
            self.logger.log("info", "System", "Broker system disconnected")
            
        except Exception as e:
            self.logger.log(
                "error",
                "System",
                "Error during disconnect",
                {"error": str(e)},
                execution_time=0.0
            )
    
    def _check_account_status(self) -> bool:
        """Check account status and connection"""
        try:
            if not self.is_connected:
                return False
                
            if not self.account:
                return False
                
            # Verify we can still access the database
            try:
                self.db_client.admin.command('ping')
            except Exception as e:
                self.logger.log(
                    "error",
                    "Database",
                    "Database connection lost",
                    {"error": str(e)},
                    execution_time=0.0
                )
                self.is_connected = False
                return False
                
            # Check account balance is valid
            if self.account.current_balance <= 0:
                self.logger.log(
                    "warning",
                    "Account",
                    "Invalid account balance",
                    {"balance": self.account.current_balance},
                    execution_time=0.0
                )
                return False
                
            # Check margin usage is within limits
            margin_usage = self.account.total_margin_used / self.account.current_balance
            if margin_usage >= self.settings.BROKER_MARGIN_CALL_THRESHOLD:
                self.logger.log(
                    "warning",
                    "Account",
                    "High margin usage",
                    {
                        "margin_usage": f"{margin_usage:.2%}",
                        "threshold": f"{self.settings.BROKER_MARGIN_CALL_THRESHOLD:.2%}"
                    },
                    execution_time=0.0
                )
                return False
                
            return True
            
        except Exception as e:
            self.logger.log(
                "error",
                "Account",
                "Account status check failed",
                {"error": str(e)},
                execution_time=0.0
            )
            return False 