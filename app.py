#!/usr/bin/env python3
"""
Real-time Trading System
Complete trading platform with real-time updates for:
- Live Prices
- Position Details (with P&L)
- Account Details 
- Strategy Signals
- Risk Management
"""

import signal
import sys
import time
import threading
import logging
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Import system components
from src.broker.broker import UnifiedBroker
from src.broker.risk_management import RiskManager
from src.data.market_data_client import RealTimeMarketData
from src.strategies.simple_random_strategy import OptimizedStrategyManager
from src.config import get_settings

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(module)s | %(message)s',
    handlers=[
        logging.FileHandler('logs/trading_bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class OperationTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.execution_time = 0.0
        
    def __enter__(self):
        """Start timing the operation"""
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and return execution time"""
        if self.start_time is not None:
            self.execution_time = time.time() - self.start_time
        return self.execution_time

class SystemLogger:
    """Enhanced logging system for trading system operations"""
    
    def __init__(self):
        self.logger = logging.getLogger("tradingsystem")
        
    def log(self, level: str, category: str, message: str, data: Any = None, execution_time: float = None):
        """Enhanced logging with execution time and data"""
        try:
            # Format log message
            log_msg = f"{level.upper()} - [tradingsystem] {category} | {message}"
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

class OptimizedTradingSystem:
    """
    High-Performance Real-time Trading System
    - Real-time updates for all components
    - Optimized position caching
    - Real-time P&L calculations
    - Advanced account metrics
    """
    
    def __init__(self):
        """Initialize optimized trading system"""
        self.logger = SystemLogger()
        self.settings = get_settings()
        
        # Core system components
        self.broker: UnifiedBroker = None
        self.risk_manager: RiskManager = None
        self.market_data: RealTimeMarketData = None
        self.strategy_manager: OptimizedStrategyManager = None
        
        # System state
        self.is_running = False
        self.start_time = None
        
        # Real-time update threads
        self._position_update_thread = None
        self._account_update_thread = None
        self._strategy_thread = None
        self._risk_thread = None
        self._main_thread = None
        self._stop_event = threading.Event()
        
        # Optimized caching for performance
        self.cached_positions: Dict[str, Any] = {}
        self.cached_account: Dict[str, Any] = {}
        self.position_cache_lock = threading.Lock()
        self.account_cache_lock = threading.Lock()
        
        # Performance tracking
        self._update_cycles = 0
        self._last_performance_log = time.time()
        self._operation_times = {}
        
        # Real-time data storage
        self.current_prices: Dict[str, Dict] = {}
        self.latest_signals: Dict[str, Any] = {}
        self.risk_alerts: list = []
        
        # Shutdown handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        return OperationTimer(operation_name)
    
    def initialize(self) -> bool:
        """Initialize all system components"""
        with self._time_operation("system_initialization") as timer:
            try:
                self.logger.log("info", "System", "Initializing Trading System")
                
                # 1. Initialize Unified Broker
                self.logger.log("info", "Broker", "Initializing broker system")
                self.broker = UnifiedBroker()
                
                if not self.broker.connect():
                    self.logger.log("error", "Broker", "Failed to connect broker to database")
                    return False
                
                if not self.broker.initialize_account("main", self.settings.BROKER_INITIAL_BALANCE):
                    self.logger.log("error", "Broker", "Failed to initialize trading account")
                    return False
                
                if not self.broker.load_positions():
                    self.logger.log("error", "Broker", "Failed to load positions")
                    return False
                
                # 2. Initialize Risk Manager
                self.logger.log("info", "Risk", "Initializing risk management system")
                self.risk_manager = RiskManager(self.broker)
                
                # 3. Initialize Market Data Client
                self.logger.log("info", "MarketData", "Initializing real-time data feed")
                self.market_data = RealTimeMarketData(price_callback=self._on_price_update)
                
                if not self.market_data.start():
                    self.logger.log("error", "MarketData", "Failed to start market data client")
                    return False
                
                # 4. Initialize Strategy Manager
                self.logger.log("info", "Strategy", "Initializing strategy system")
                self.strategy_manager = OptimizedStrategyManager()
                
                if not self.strategy_manager.start():
                    self.logger.log("error", "Strategy", "Failed to start strategy manager")
                    return False
                
                # 5. Initialize caches
                self._initialize_caches()
                
                self.logger.log(
                    "info", "System", "System initialization completed successfully",
                    {"components": ["broker", "risk", "market_data", "strategy"]},
                    timer.__exit__(None, None, None)
                )
                return True
                
            except Exception as e:
                self.logger.log(
                    "error", "System", "System initialization failed",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return False
    
    def start_real_time_trading(self) -> bool:
        """Start the real-time trading system"""
        with self._time_operation("system_start") as timer:
            try:
                if self.is_running:
                    self.logger.log("warning", "System", "Trading system already running")
                    return True
                
                self.logger.log("info", "System", "Starting real-time trading operations")
                
                # Set running state
                self.is_running = True
                self.start_time = datetime.now(timezone.utc)
                self._stop_event.clear()
                
                # Start all real-time update threads
                self._start_real_time_threads()
                
                # Start monitoring systems
                self.broker.start_monitoring()
                self.risk_manager.start_risk_monitoring()
                
                self.logger.log(
                    "info", "System", "Real-time trading system started",
                    {
                        "update_interval": f"{self.settings.LIVE_PRICE_UPDATE_INTERVAL}s",
                        "components": ["prices", "positions", "account", "strategy", "risk"]
                    },
                    timer.__exit__(None, None, None)
                )
                return True
                
            except Exception as e:
                self.logger.log(
                    "error", "System", "Failed to start real-time trading",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return False
    
    def stop_trading(self) -> None:
        """Stop trading operations"""
        with self._time_operation("system_stop") as timer:
            try:
                self.logger.log("info", "System", "Stopping real-time trading system")
                
                # Set stop flag
                self._stop_event.set()
                self.is_running = False
                
                # Stop all threads
                self._stop_all_threads()
                
                # Stop monitoring systems
                if self.risk_manager:
                    self.risk_manager.stop_risk_monitoring()
                
                if self.broker:
                    self.broker.stop_monitoring()
                
                # Stop market data
                if self.market_data:
                    self.market_data.stop()
                
                # Stop strategy manager
                if self.strategy_manager:
                    self.strategy_manager.stop()
                
                uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
                self.logger.log(
                    "info", "System", "Trading system stopped successfully",
                    {"uptime_seconds": round(uptime, 2)},
                    timer.__exit__(None, None, None)
                )
                
            except Exception as e:
                self.logger.log(
                    "error", "System", "Error during system shutdown",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
    
    def _start_real_time_threads(self) -> None:
        """Start all real-time update threads"""
        # Position updates every 1 second
        self._position_update_thread = threading.Thread(
            target=self._position_update_loop, daemon=True
        )
        self._position_update_thread.start()
        
        # Account updates every 1 second
        self._account_update_thread = threading.Thread(
            target=self._account_update_loop, daemon=True
        )
        self._account_update_thread.start()
        
        # Strategy checks every 1 second
        self._strategy_thread = threading.Thread(
            target=self._strategy_loop, daemon=True
        )
        self._strategy_thread.start()
        
        # Risk management every 1 second
        self._risk_thread = threading.Thread(
            target=self._risk_management_loop, daemon=True
        )
        self._risk_thread.start()
        
        # Main system monitoring
        self._main_thread = threading.Thread(
            target=self._main_system_loop, daemon=True
        )
        self._main_thread.start()
    
    def _stop_all_threads(self) -> None:
        """Stop all running threads"""
        threads = [
            self._position_update_thread,
            self._account_update_thread,
            self._strategy_thread,
            self._risk_thread,
            self._main_thread
        ]
        
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=2.0)
    
    def _on_price_update(self, symbol: str, price_data: Dict) -> None:
        """Handle real-time price updates"""
        try:
            # Update current prices
            self.current_prices[symbol] = price_data
            
            # Update position PnL if we have a position for this symbol
            with self.position_cache_lock:
                for position in self.cached_positions.values():
                    if position["symbol"] == symbol:
                        current_price = price_data["price"]
                        entry_price = position["entry_price"]
                        size = position["size"]
                        
                        if position["type"] == "LONG":
                            pnl = (current_price - entry_price) * size
                        else:  # SHORT
                            pnl = (entry_price - current_price) * size
                            
                        position["current_price"] = current_price
                        position["pnl"] = pnl
                        position["pnl_percentage"] = (pnl / (entry_price * size)) * 100
                        position["last_update"] = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            self.logger.log(
                "error",
                "PriceUpdate",
                "Error processing price update",
                {"error": str(e), "symbol": symbol},
                execution_time=0.0
            )
    
    def _position_update_loop(self) -> None:
        """Real-time position updates every 1 second"""
        self.logger.log("info", "Position", "Position update loop started (1-second interval)")
        
        while not self._stop_event.is_set():
            try:
                with self._time_operation("position_update") as timer:
                    start_time = time.time()
                    
                    # Get current positions and update with live prices
                    self._update_position_cache()
                    
                    # Log position details
                    self._log_position_updates()
                    
                    # Precise 1-second interval
                    elapsed = time.time() - start_time
                    sleep_time = max(0, self.settings.POSITION_UPDATE_INTERVAL - elapsed)
                    time.sleep(sleep_time)
                    
            except Exception as e:
                self.logger.log(
                    "error", "Position", "Error in position update loop",
                    {"error": str(e)},
                    0.0
                )
                time.sleep(1)
    
    def _account_update_loop(self) -> None:
        """Real-time account updates"""
        self.logger.log("info", "Account", "Account update loop started")
        
        while not self._stop_event.is_set():
            try:
                with self._time_operation("account_update") as timer:
                    # Update account cache
                    self._update_account_cache()
                    
                    # Log updates periodically
                    if time.time() - self._last_performance_log >= 10:
                        self._log_account_updates()
                        self._last_performance_log = time.time()
                    
                    # Sleep for update interval
                    time.sleep(self.settings.ACCOUNT_UPDATE_INTERVAL)
                    
            except Exception as e:
                self.logger.log(
                    "error", "Account", "Error in account update loop",
                    {"error": str(e)},
                    0.0
                )
                time.sleep(1)
    
    def _strategy_loop(self) -> None:
        """Real-time strategy checks"""
        self.logger.log("info", "Strategy", "Strategy loop started")
        
        while not self._stop_event.is_set():
            try:
                with self._time_operation("strategy_loop") as timer:
                    if self.current_prices:
                        self._check_strategy_signals()
                    time.sleep(self.settings.STRATEGY_CHECK_INTERVAL)
                    
            except Exception as e:
                self.logger.log(
                    "error", "Strategy", "Error in strategy loop",
                    {"error": str(e)},
                    0.0
                )
                time.sleep(1)
    
    def _risk_management_loop(self) -> None:
        """Real-time risk management"""
        self.logger.log("info", "Risk", "Risk management loop started")
        
        while not self._stop_event.is_set():
            try:
                with self._time_operation("risk_management") as timer:
                    self._check_risk_management()
                    time.sleep(self.settings.RISK_CHECK_INTERVAL)
                    
            except Exception as e:
                self.logger.log(
                    "error", "Risk", "Error in risk management loop",
                    {"error": str(e)},
                    0.0
                )
                time.sleep(1)
    
    def _main_system_loop(self) -> None:
        """Main system monitoring and performance tracking"""
        while not self._stop_event.is_set():
            try:
                self._update_cycles += 1
                
                # Log comprehensive system status every X seconds
                if self._update_cycles % self.settings.COMPREHENSIVE_STATUS_LOG_INTERVAL == 0:
                    self._log_comprehensive_status()
                
                time.sleep(1)
                
            except Exception as e:
                self.logger.log(
                    "error", "System", "Error in main system loop",
                    {"error": str(e)},
                    0.0
                )
                time.sleep(1)
    
    def _initialize_caches(self) -> None:
        """Initialize position and account caches"""
        self._update_position_cache()
        self._update_account_cache()
    
    def _update_position_cache(self) -> None:
        """Update position cache with real-time P&L calculations"""
        with self.position_cache_lock:
            try:
                positions_data = {}
                
                for pos_id, position in self.broker.positions.items():
                    if position.status.value == "OPEN":
                        # Get current price for P&L calculation
                        current_price = self.current_prices.get(position.symbol, {}).get("price", 0)
                        
                        if current_price > 0:
                            # Calculate real-time P&L
                            pnl = position.calculate_pnl(current_price)
                            position.calculate_holding_time()
                            
                            positions_data[pos_id] = {
                                "id": position.id,
                                "symbol": position.symbol,
                                "type": position.position_type.value,
                                "entry_price": position.entry_price,
                                "current_price": current_price,
                                "quantity": position.quantity,
                                "invested_amount": position.invested_amount,
                                "leverage": position.leverage,
                                "pnl": pnl,
                                "pnl_percentage": (pnl / position.invested_amount) * 100 if position.invested_amount > 0 else 0,
                                "profit_after_amount": position.profit_after_amount,
                                "holding_time": position.holding_time,
                                "stop_loss": position.stop_loss,
                                "target": position.target,
                                "margin_used": position.margin_used,
                                "margin_usage": position.calculate_margin_usage(current_price),
                                "status": position.status.value
                            }
                
                self.cached_positions = positions_data
                
            except Exception as e:
                self.logger.log(
                    "error", "Position", "Error updating position cache",
                    {"error": str(e)},
                    0.0
                )
    
    def _update_account_cache(self) -> None:
        """Update account cache with comprehensive metrics"""
        with self.account_cache_lock:
            try:
                if not self.broker.account:
                    return
                
                account = self.broker.account
                
                # Calculate unrealized P&L from open positions
                unrealized_pnl = sum(
                    pos_data.get("pnl", 0) for pos_data in self.cached_positions.values()
                )
                
                # Calculate account growth
                account_growth = ((account.current_balance - account.initial_balance) / account.initial_balance) * 100
                
                # Calculate today's stats
                open_trades = len([p for p in self.cached_positions.values() if p.get("status") == "OPEN"])
                
                self.cached_account = {
                    "current_balance": account.current_balance,
                    "initial_balance": account.initial_balance,
                    "account_growth": round(account_growth, 2),
                    "margin_used": account.total_margin_used,
                    "max_leverage": account.max_leverage,
                    "realized_pnl": account.total_profit - account.total_loss,
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "open_trades": open_trades,
                    "closed_trades": account.total_trades,
                    "win_rate": round(account.win_rate, 2),
                    "daily_trades": account.daily_trades_count,
                    "daily_limit": account.daily_trades_limit,
                    "max_profit": max([p.get("pnl", 0) for p in self.cached_positions.values()], default=0),
                    "max_loss": min([p.get("pnl", 0) for p in self.cached_positions.values()], default=0),
                    "total_profit": account.total_profit,
                    "total_loss": account.total_loss,
                    "brokerage_charges": account.brokerage_charges,
                    "algo_status": "RUNNING" if self.is_running else "STOPPED"
                }
                
            except Exception as e:
                self.logger.log(
                    "error", "Account", "Error updating account cache",
                    {"error": str(e)},
                    0.0
                )
    
    def _check_strategy_signals(self) -> None:
        """Check for trading signals and execute trades"""
        try:
            # Generate signals for current prices
            analysis_result = self.strategy_manager.analyze_and_generate_signals(self.current_prices)
            
            if analysis_result.get("status") == "completed":
                actionable_signals = analysis_result.get("actionable_signals", {})
                
                for symbol, signal_data in actionable_signals.items():
                    signal = signal_data.get("signal")
                    confidence = signal_data.get("confidence", 0)
                    current_price = signal_data.get("current_price", 0)
                    
                    if signal in ["BUY", "SELL"] and confidence >= self.settings.BROKER_MIN_CONFIDENCE:
                        # Execute trade
                        if self._can_execute_trade(signal_data):
                            success = self.broker.execute_trade(
                                signal=signal,
                                symbol=symbol,
                                current_price=current_price,
                                confidence=confidence,
                                strategy_name="Simple Random Strategy",
                                leverage=self.settings.BROKER_DEFAULT_LEVERAGE
                            )
                            
                            if success:
                                self.logger.log(
                                    "info", "Trade", f"🎯 Executed {signal} for {symbol} at ${current_price:.2f}",
                                    {"signal": signal, "symbol": symbol, "current_price": current_price},
                                    0.0
                                )
                            else:
                                self.logger.log(
                                    "warning", "Trade", f"⚠️ Failed to execute {signal} for {symbol}",
                                    {"signal": signal, "symbol": symbol},
                                    0.0
                                )
                
                # Store latest signals
                self.latest_signals = actionable_signals
                
        except Exception as e:
            self.logger.log(
                "error", "Strategy", "Error checking strategy signals",
                {"error": str(e)},
                0.0
            )
    
    def _check_risk_management(self) -> None:
        """Check risk management for all positions"""
        try:
            risk_alerts = []
            
            for pos_id, position in self.broker.positions.items():
                if position.status.value == "OPEN":
                    current_price = self.current_prices.get(position.symbol, {}).get("price", 0)
                    
                    if current_price > 0:
                        # Analyze position risk
                        risk_metrics = self.risk_manager.analyze_position_risk(position, current_price)
                        
                        # Execute risk actions if needed
                        action_taken = self.risk_manager.execute_risk_action(position, risk_metrics, current_price)
                        
                        if action_taken:
                            risk_alerts.append(f"Risk action taken for {position.symbol}")
                        
                        # Check for stop loss or target hits
                        if position.stop_loss and current_price <= position.stop_loss:
                            self.broker.close_position(pos_id, current_price, "Stop Loss Hit")
                            risk_alerts.append(f"Stop Loss hit for {position.symbol}")
                        
                        elif position.target and current_price >= position.target:
                            self.broker.close_position(pos_id, current_price, "Target Hit")
                            risk_alerts.append(f"Target hit for {position.symbol}")
            
            self.risk_alerts = risk_alerts
            
        except Exception as e:
            self.logger.log(
                "error", "Risk", "Error in risk management",
                {"error": str(e)},
                0.0
            )
    
    def _can_execute_trade(self, signal_data: dict) -> bool:
        """Check if we can execute a trade"""
        try:
            # Check daily trade limits
            if not self.broker.account.can_trade_today():
                return False
            
            # Check if we already have a position in this symbol
            symbol = signal_data.get("symbol")
            if symbol in self.broker.open_positions:
                return False
            
            # Check account balance
            if self.broker.account.current_balance < self.settings.BROKER_MAX_POSITION_SIZE:
                return False
            
            return True
            
        except Exception as e:
            self.logger.log(
                "error", "Trade", "Error checking trade execution",
                {"error": str(e)},
                0.0
            )
            return False
    
    def _log_position_updates(self) -> None:
        """Log real-time position updates"""
        try:
            if self.cached_positions:
                position_summary = []
                for pos_data in self.cached_positions.values():
                    summary = (f"{pos_data['symbol']} | "
                             f"{pos_data['type']} | "
                             f"Entry: ${pos_data['entry_price']:.2f} | "
                             f"Current: ${pos_data['current_price']:.2f} | "
                             f"P&L: ${pos_data['pnl']:.2f} ({pos_data['pnl_percentage']:+.2f}%) | "
                             f"Time: {pos_data['holding_time']}")
                    position_summary.append(summary)
            
                # Log position details
                for summary in position_summary:
                    self.logger.log(
                        "info", "Position", f"📍 [Position] {summary}",
                        {"summary": summary},
                        0.0
                    )
            
        except Exception as e:
            self.logger.log(
                "error", "Position", "Error logging position updates",
                {"error": str(e)},
                0.0
            )
    
    def _log_account_updates(self) -> None:
        """Log account updates"""
        try:
            with self._time_operation("log_account_updates") as timer:
                if self.cached_account:
                    self.logger.log(
                        "info", "Account", "Account status update",
                        {"account": self.cached_account},
                        timer.__exit__(None, None, None)
                    )
            
        except Exception as e:
            self.logger.log(
                "error", "Account", "Error logging account updates",
                {"error": str(e)},
                0.0
            )
    
    def _log_comprehensive_status(self) -> None:
        """Log comprehensive system status"""
        try:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
            
            # Market data stats
            market_stats = self.market_data.get_performance_stats() if self.market_data else {}
            
            # Position summary
            open_positions = len(self.cached_positions)
            total_pnl = sum(pos.get("pnl", 0) for pos in self.cached_positions.values())
            
            status_summary = {
                "uptime_seconds": round(uptime, 2),
                "update_cycles": self._update_cycles,
                "market_data_status": market_stats.get("status", "unknown"),
                "open_positions": open_positions,
                "total_unrealized_pnl": round(total_pnl, 2),
                "latest_signals": len(self.latest_signals),
                "risk_alerts": len(self.risk_alerts),
                "account_balance": self.cached_account.get("current_balance", 0)
            }
            
            self.logger.log(
                "info", "System", f"🚀 [System Status] {json.dumps(status_summary, indent=2)}",
                {"status_summary": status_summary},
                0.0
            )
            
        except Exception as e:
            self.logger.log(
                "error", "System", "Error logging comprehensive status",
                {"error": str(e)},
                0.0
            )
    
    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals"""
        self.logger.log(
            "info", "System", f"🛑 Received signal {signum}, shutting down...",
            {"signal": signum},
            0.0
        )
        self.stop_trading()
        sys.exit(0)
    
    def get_system_status(self) -> dict:
        """Get current system status"""
        try:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
            
            return {
                    "is_running": self.is_running,
                "uptime_seconds": uptime,
                "update_cycles": self._update_cycles,
                "current_prices": len(self.current_prices),
                "open_positions": len(self.cached_positions),
                "account_balance": self.cached_account.get("current_balance", 0),
                "market_data_status": self.market_data.get_performance_stats() if self.market_data else {},
                "last_update": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.log(
                "error", "System", "Error getting system status",
                {"error": str(e)},
                0.0
            )
            return {"error": str(e)}


def main():
    """Main function to start the optimized trading system"""
    system = OptimizedTradingSystem()
    
    try:
        # Initialize system
        if not system.initialize():
            print("❌ Failed to initialize trading system")
            return 1
        
        # Start real-time trading
        if not system.start_real_time_trading():
            print("❌ Failed to start real-time trading")
            return 1
        
        print("\n" + "="*80)
        print("🚀 OPTIMIZED REAL-TIME TRADING SYSTEM - LIVE")
        print("="*80)
        print("📊 Live Price Updates: Every 1 second")
        print("📍 Position Updates: Every 1 second (with real-time P&L)")
        print("💰 Account Updates: Every 1 second")
        print("🎯 Strategy Checks: Every 1 second")
        print("⚠️ Risk Management: Every 1 second")
        print("="*80)
        print("Press Ctrl+C to stop the system\n")
        
        # Keep main thread alive
        try:
            while system.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        
        return 0
        
    except Exception as e:
        print(f"❌ System error: {e}")
        return 1
    
    finally:
        system.stop_trading()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)