#!/usr/bin/env python3
"""
Professional Trading System with WebSocket Server Integration
Features:
- Professional error handling and type hints
- WebSocket server for real-time frontend broadcasting
- Optimized performance and memory management
- Circuit breaker patterns for reliability
- Comprehensive monitoring and health checks
"""

import asyncio
import logging
import signal
import sys
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Union
from contextlib import asynccontextmanager
import os
from dataclasses import dataclass
import weakref
from collections import deque
import gc

# Core imports
from src.broker.paper_broker import AsyncBroker
from src.services.risk_manager import AsyncRiskManager
from src.services.notifications import NotificationManager
from src.config import get_settings, get_trading_config, get_system_intervals
from src.services.live_price_ws import RealTimeMarketData
from src.strategies.strategy_manager import StrategyManager
from src.database.schemas import TradingSignal, MarketData, SignalType
from src.broker.historical_data import HistoricalDataProvider
from src.api.websocket_server import WebSocketServer, get_websocket_server


@dataclass
class SystemHealth:
    """System health status"""
    is_healthy: bool
    components: Dict[str, bool]
    error_count: int
    last_error: Optional[str]
    uptime: float
    memory_usage: float


class CircuitBreaker:
    """Circuit breaker pattern for resilient operations"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            
            raise e


class TradingSystem:
    """Professional trading system with WebSocket server integration"""
    
    def __init__(self, live_save: bool = False, websocket_port: int = 8765, email_enabled: bool = True):
        """Initialize the trading system with all components"""
        self.settings = get_settings()
        self.trading_config = get_trading_config()
        self.intervals = get_system_intervals()
        self.logger = logging.getLogger("trading_system")
        
        # System state
        self._running = False
        self._shutdown_event = threading.Event()
        self._start_time = time.time()
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Initialize core components with error handling
        try:
            self.broker = AsyncBroker()
            self.risk_manager = AsyncRiskManager(self.broker)
            self.notification_manager = NotificationManager(email_enabled=email_enabled)
            self.strategy_manager = StrategyManager(max_workers=4)
            
            # WebSocket server for real-time data broadcasting
            self.websocket_server = get_websocket_server()
            self.websocket_server.port = websocket_port
            
            # Initialize WebSocket live price system with callback
            self.live_price_system = RealTimeMarketData(
                price_callback=self._on_live_price_update
            )
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize components: {e}")
            raise
        
        # Threading
        self.strategy_thread: Optional[threading.Thread] = None
        self.monitoring_thread: Optional[threading.Thread] = None
        
        # Current market data with thread safety
        self.current_market_data: Dict[str, MarketData] = {}
        self.market_data_lock = threading.RLock()
        
        # Performance optimization - use deque for rolling statistics
        self.price_update_times = deque(maxlen=1000)
        self.strategy_execution_times = deque(maxlen=100)
        
        # Circuit breakers for resilience
        self.circuit_breakers = {
            "broker": CircuitBreaker(failure_threshold=3, recovery_timeout=30),
            "risk_manager": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            "websocket": CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        }
        
        # Statistics with atomic operations
        self._stats = {
            "trades_executed": 0,
            "trades_successful": 0,
            "trades_failed": 0,
            "total_pnl": 0.0,
            "signals_generated": 0,
            "price_updates": 0,
            "strategies_executed": 0,
            "websocket_updates": 0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0
        }
        
        # Error tracking
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.error_history = deque(maxlen=100)
        
        # Live save configuration
        self.live_save = live_save
        self._last_live_save_time: Dict[str, float] = {}
        
        # Real-time broadcast throttling (prevent spam but allow immediate updates)
        self._last_broadcast_time = 0.0
        self._broadcast_cooldown = 1.0  # Minimum 1 second between broadcasts
        
        # Setup strategies
        self._setup_strategies()
        
        # Memory management
        self._last_gc_time = time.time()
        self._gc_interval = 300  # 5 minutes
        
        self.logger.info("✅ Trading system initialized successfully")

    def _setup_strategies(self):
        """Setup trading strategies for different symbols with error handling"""
        try:
            symbols = self.settings.TRADING_SYMBOLS
            historical_data_provider = HistoricalDataProvider()
            
            self.strategy_manager.add_default_strategies(
                symbols, 
                historical_data_provider=historical_data_provider
            )
            
            self.logger.info(f"✅ Setup strategies for {len(symbols)} symbols: {symbols}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to setup strategies: {e}")
            self.error_count += 1
            self.last_error = str(e)
            raise

    def _on_live_price_update(self, live_prices: Dict[str, Dict]):
        """Enhanced callback function with error handling and WebSocket broadcasting"""
        start_time = time.time()
        
        try:
            # Process each price update
            for symbol, price_data in live_prices.items():
                try:
                    # Log raw price data for debugging
                    self.logger.debug(f"📊 Processing live price update for {symbol}")
                    self.logger.debug(f"   💰 Price: {price_data.get('price', 'N/A')}")
                    self.logger.debug(f"   📈 Data keys: {list(price_data.keys())}")
                    
                    # Convert WebSocket data to MarketData format
                    market_data = MarketData(
                        symbol=symbol,
                        price=price_data.get("price", 0.0),
                        mark_price=price_data.get("mark_price"),
                        spot_price=price_data.get("spot_price"),
                        volume=price_data.get("volume"),
                        turnover=price_data.get("turnover"),
                        turnover_usd=price_data.get("turnover_usd"),
                        high=price_data.get("high"),
                        low=price_data.get("low"),
                        open=price_data.get("open"),
                        close=price_data.get("close"),
                        open_interest=price_data.get("open_interest"),
                        oi_value=price_data.get("oi_value"),
                        oi_contracts=price_data.get("oi_contracts"),
                        oi_value_usd=price_data.get("oi_value_usd"),
                        oi_change_usd_6h=price_data.get("oi_change_usd_6h"),
                        funding_rate=price_data.get("funding_rate"),
                        mark_basis=price_data.get("mark_basis"),
                        mark_change_24h=price_data.get("mark_change_24h"),
                        underlying_asset_symbol=price_data.get("underlying_asset_symbol"),
                        description=price_data.get("description"),
                        initial_margin=price_data.get("initial_margin"),
                        tick_size=price_data.get("tick_size"),
                        price_band_lower=price_data.get("price_band_lower"),
                        price_band_upper=price_data.get("price_band_upper"),
                        best_bid=price_data.get("best_bid"),
                        best_ask=price_data.get("best_ask"),
                        bid_size=price_data.get("bid_size"),
                        ask_size=price_data.get("ask_size"),
                        mark_iv=price_data.get("mark_iv"),
                        size=price_data.get("size"),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Thread-safe update of market data
                    with self.market_data_lock:
                        self.current_market_data[symbol] = market_data
                        self.logger.debug(f"✅ Market data stored for {symbol} - Price: ${market_data.price:.2f}")
                        self.logger.debug(f"   📊 Current market data symbols: {list(self.current_market_data.keys())}")
                    
                    # Live save logic with circuit breaker
                    if self.live_save:
                        self._handle_live_save(market_data)
                    
                    # Update broker prices with circuit breaker
                    if self._main_loop is not None:
                        self._update_broker_prices_safe(symbol, price_data)
                        self._update_risk_management_safe()
                    
                    # Broadcast to WebSocket clients
                    self._broadcast_price_update_safe(live_prices)
                    
                    # Immediately broadcast updated account and position data
                    self._broadcast_account_and_positions_safe()
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing price update for {symbol}: {e}")
                    self._record_error(str(e))
                    continue
            
            # Update statistics
            self._stats["websocket_updates"] += 1
            self._stats["price_updates"] += 1
            
            # Record performance
            processing_time = time.time() - start_time
            self.price_update_times.append(processing_time)
            
            # Memory management check
            self._check_memory_management()
            
        except Exception as e:
            self.logger.error(f"❌ Critical error in live price callback: {e}")
            self._record_error(str(e))

    def _handle_live_save(self, market_data: MarketData):
        """Handle live save with rate limiting and error handling"""
        try:
            now = time.time()
            last_save = self._last_live_save_time.get(market_data.symbol, 0)
            
            if now - last_save >= 20:  # Rate limit: once per 20 seconds
                from src.database.mongodb_client import AsyncMongoDBClient
                
                if self._main_loop is not None:
                    client = AsyncMongoDBClient()
                    asyncio.run_coroutine_threadsafe(
                        client.save_live_price_async(market_data),
                        self._main_loop
                    )
                    self._last_live_save_time[market_data.symbol] = now
                    
        except Exception as e:
            self.logger.error(f"❌ Error saving live price for {market_data.symbol}: {e}")

    def _update_broker_prices_safe(self, symbol: str, price_data: Dict):
        """Update broker prices with circuit breaker protection"""
        try:
            def update_prices():
                prices = {symbol: {"price": price_data.get("price", 0.0)}}
                return asyncio.run_coroutine_threadsafe(
                    self.broker.update_prices_async(prices),
                    self._main_loop
                )
            
            self.circuit_breakers["broker"].call(update_prices)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Broker update failed (circuit breaker): {e}")

    def _update_risk_management_safe(self):
        """Update risk management with circuit breaker protection"""
        try:
            def update_risk():
                return asyncio.run_coroutine_threadsafe(
                    self._update_risk_management(),
                    self._main_loop
                )
            
            self.circuit_breakers["risk_manager"].call(update_risk)
            
        except Exception as e:
            self.logger.warning(f"⚠️ Risk management update failed (circuit breaker): {e}")

    def _broadcast_price_update_safe(self, live_prices: Dict[str, Dict]):
        """Broadcast price updates to WebSocket clients with circuit breaker"""
        try:
            def broadcast():
                if self._main_loop is not None:
                    return asyncio.run_coroutine_threadsafe(
                        self.websocket_server.broadcast_live_prices(live_prices),
                        self._main_loop
                    )
            
            self.circuit_breakers["websocket"].call(broadcast)
            
        except Exception as e:
            self.logger.warning(f"⚠️ WebSocket broadcast failed (circuit breaker): {e}")

    def _broadcast_account_and_positions_safe(self):
        """Broadcast account and position updates with smart throttling"""
        try:
            current_time = time.time()
            
            # Smart throttling: allow immediate updates but prevent spam
            if current_time - self._last_broadcast_time >= self._broadcast_cooldown:
                self._last_broadcast_time = current_time
                
                def broadcast():
                    if self._main_loop is not None:
                        return asyncio.run_coroutine_threadsafe(
                            self._broadcast_live_updates(),
                            self._main_loop
                        )
                
                self.circuit_breakers["websocket"].call(broadcast)
                self.logger.debug(f"📡 Broadcasting live updates triggered by price change")
            else:
                self.logger.debug(f"⏱️ Broadcast throttled (cooldown: {self._broadcast_cooldown}s)")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Account/positions broadcast failed (circuit breaker): {e}")

    async def _broadcast_live_updates(self):
        """Broadcast live account and position updates"""
        try:
            # Get fresh account summary with live PnL
            account_summary = await self.broker.get_account_summary_async()
            
            # Get fresh positions with live prices
            positions_summary = await self.broker.get_positions_summary_async()
            open_positions = positions_summary.get("open_positions", [])
            
            # Broadcast both updates immediately
            await self.websocket_server.broadcast_account_summary(account_summary)
            await self.websocket_server.broadcast_positions_update(open_positions)
            
            self.logger.debug(f"📡 Real-time update: {len(open_positions)} positions, balance: ${account_summary.get('current_balance', 0):.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Error broadcasting live updates: {e}")

    def _check_memory_management(self):
        """Check and perform memory management if needed"""
        current_time = time.time()
        
        if current_time - self._last_gc_time > self._gc_interval:
            try:
                # Force garbage collection
                collected = gc.collect()
                self._last_gc_time = current_time
                
                if collected > 0:
                    self.logger.debug(f"🧹 Garbage collected {collected} objects")
                    
                # Update memory usage statistics
                import psutil
                process = psutil.Process()
                self._stats["memory_usage"] = process.memory_info().rss / 1024 / 1024  # MB
                
            except Exception as e:
                self.logger.warning(f"⚠️ Memory management error: {e}")

    def _record_error(self, error_message: str):
        """Record error for monitoring and alerting"""
        self.error_count += 1
        self.last_error = error_message
        self.error_history.append({
            "timestamp": datetime.now(timezone.utc),
            "error": error_message
        })

    async def start(self) -> bool:
        """Start the trading system with comprehensive error handling"""
        try:
            self.logger.info("🚀 Starting Professional Trading System")
            self.logger.info("📋 STEP 1: System Setup & Configuration")
            
            # Store the main event loop
            self._main_loop = asyncio.get_running_loop()
            self.logger.info("✅ STEP 1.1: Event loop configured")
            
            self.logger.info("📋 STEP 2: Initializing WebSocket Infrastructure")
            
            # Start WebSocket server first
            self.logger.info("🔄 STEP 2.1: Starting WebSocket server...")
            if not await self.websocket_server.start():
                self.logger.error("❌ STEP 2.1 FAILED: WebSocket server startup failed")
                return False
            self.logger.info("✅ STEP 2.1: WebSocket server started successfully")
            
            self.logger.info("📋 STEP 3: Starting Live Market Data System") 
            # Start WebSocket live price system
            self.logger.info("🔄 STEP 3.1: Connecting to live price WebSocket...")
            if not self.live_price_system.start():
                self.logger.error("❌ STEP 3.1 FAILED: Live price WebSocket connection failed")
                await self.websocket_server.stop()
                return False
            self.logger.info("✅ STEP 3.1: Live price WebSocket connected successfully")
            
            self.logger.info("📋 STEP 4: Starting Core Trading Components")
            # Start all async components with detailed error handling
            components = [
                ("broker", self.broker.start()),
                ("risk_manager", self.risk_manager.start()),
                ("notification_manager", self.notification_manager.start())
            ]
            
            for i, (name, coro) in enumerate(components, 1):
                try:
                    self.logger.info(f"🔄 STEP 4.{i}: Starting {name}...")
                    result = await coro
                    
                    self.logger.info(f"📋 STEP 4.{i}: Component {name} returned: {result} (type: {type(result)})")
                    
                    if result is False:
                        self.logger.error(f"❌ STEP 4.{i} FAILED: {name} returned False - Component failed to start")
                        self.logger.error(f"❌ LOCATION: Component startup failure in {name}")
                        self.logger.error(f"❌ ACTION: System will shutdown due to {name} failure")
                        await self.stop()
                        return False
                    elif result is None:
                        self.logger.error(f"❌ STEP 4.{i} FAILED: {name} returned None - Invalid return value")
                        self.logger.error(f"❌ LOCATION: Component {name} start() method should return True/False")
                        self.logger.error(f"❌ ACTION: System will shutdown due to {name} invalid return")
                        await self.stop()
                        return False
                    else:
                        self.logger.info(f"✅ STEP 4.{i}: {name} started successfully")
                        
                except Exception as e:
                    self.logger.error(f"❌ STEP 4.{i} EXCEPTION in {name}:")
                    self.logger.error(f"❌ ERROR MESSAGE: {str(e)}")
                    self.logger.error(f"❌ ERROR TYPE: {type(e).__name__}")
                    self.logger.error(f"❌ LOCATION: Exception occurred while starting {name}")
                    
                    # Print full traceback
                    import traceback
                    tb_lines = traceback.format_exc().split('\n')
                    for j, line in enumerate(tb_lines):
                        if line.strip():
                            self.logger.error(f"❌ TRACEBACK[{j:02d}]: {line}")
                    
                    self.logger.error(f"❌ ACTION: System will shutdown due to {name} exception")
                    await self.stop()
                    return False
            
            self.logger.info("📋 STEP 5: Starting Background Processing Threads")
            # Start threading components
            self._running = True
            
            self.logger.info("🔄 STEP 5.1: Starting strategy execution thread...")
            self.strategy_thread = threading.Thread(
                target=self._strategy_execution_loop, 
                daemon=True,
                name="StrategyThread"
            )
            self.strategy_thread.start()
            self.logger.info("✅ STEP 5.1: Strategy execution thread started")
            
            self.logger.info("🔄 STEP 5.2: Starting monitoring thread...")
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MonitoringThread"
            )
            self.monitoring_thread.start()
            self.logger.info("✅ STEP 5.2: Monitoring thread started")
            
            self.logger.info("📋 STEP 6: Finalizing System Startup & Sending Notifications")
            
            # Send comprehensive startup notification with account summary
            self.logger.info("🔄 STEP 6.1: Sending comprehensive startup notification...")
            try:
                # Get current account summary for startup email
                startup_account_summary = await self.broker.get_account_summary_async()
                startup_positions_summary = await self.broker.get_positions_summary_async()
                
                self.logger.info("📊 Current account status at startup:")
                self.logger.info(f"   💰 Balance: ${startup_account_summary.get('current_balance', 0):,.2f}")
                self.logger.info(f"   📈 Total P&L: ${startup_account_summary.get('total_pnl', 0):,.2f}")
                self.logger.info(f"   📊 Open Positions: {startup_positions_summary.get('total_open', 0)}")
                self.logger.info(f"   🎯 Win Rate: {startup_account_summary.get('win_rate', 0):.1f}%")
                
                await self.notification_manager.notify_system_startup(
                    account_summary=startup_account_summary,
                    positions_summary=startup_positions_summary,
                    user_id="system"
                )
                self.logger.info("✅ STEP 6.1: Comprehensive startup notification sent with account summary")
            except Exception as e:
                self.logger.error(f"❌ Error sending startup notification: {e}")
                # Fallback to basic startup notification
                await self.notification_manager.notify_system_startup(user_id="system")
                self.logger.info("✅ STEP 6.1: Basic startup notification sent")
            
            # Broadcast system status
            self.logger.info("🔄 STEP 6.2: Broadcasting system status to WebSocket clients...")
            await self.websocket_server.broadcast_notification(
                "system_startup",
                "Trading system started successfully",
                "info"
            )
            self.logger.info("✅ STEP 6.2: System status broadcasted")
            
            # Log current position status for transparency
            self.logger.info("📊 STEP 6.3: Checking existing positions...")
            try:
                position_counts = self.broker.get_open_positions_count_by_symbol()
                if position_counts:
                    self.logger.info(f"📊 Existing open positions: {position_counts}")
                    for symbol, count in position_counts.items():
                        existing_pos = self.broker.get_open_position_for_symbol(symbol)
                        if existing_pos:
                            self.logger.info(f"   📈 {symbol}: {existing_pos.position_type.value} "
                                           f"qty={existing_pos.quantity} entry=${existing_pos.entry_price:.2f}")
                else:
                    self.logger.info("📊 No existing open positions found")
                self.logger.info("💡 IMPORTANT: Only ONE position per symbol allowed")
            except Exception as e:
                self.logger.warning(f"⚠️ Error checking existing positions: {e}")
            
            self.logger.info("🎉 ALL STEPS COMPLETED: Trading system started successfully")
            self.logger.info("📧 Startup notification email sent with complete system configuration")
            self.logger.info("🔔 System will send shutdown notification with final statistics when stopped")
            self.logger.info("🚨 POSITION LIMIT: Only ONE position per symbol is allowed")
            self.logger.info("💡 EMAIL FEATURES:")
            self.logger.info("   📧 Startup: System config + Account summary + Position status")
            self.logger.info("   📧 Shutdown: Final statistics + Account summary + Complete session data")
            self.logger.info("   ⏱️ Email delivery: 3-second wait for proper processing")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading system: {e}")
            self._record_error(str(e))
            await self.stop()
            return False

    async def stop(self):
        """Stop the trading system with proper cleanup and comprehensive shutdown notification"""
        if not self._running:
            return
        
        self.logger.info("🛑 Stopping Trading System")
        shutdown_start_time = time.time()
        
        # Calculate uptime
        uptime_seconds = time.time() - self._start_time
        
        try:
            # Collect final statistics before shutdown
            self.logger.info("📊 Collecting final system statistics...")
            
            # Get final account summary
            try:
                account_summary = await self.broker.get_account_summary_async()
                formatted_account = {
                    "current_balance": f"${account_summary.get('current_balance', 0):,.2f}",
                    "total_pnl": f"${account_summary.get('total_pnl', 0):,.2f}",
                    "open_positions": str(account_summary.get('open_positions', 0)),
                    "win_rate": f"{account_summary.get('win_rate', 0):.1f}%",
                    "daily_trades": str(account_summary.get('daily_trades', 0))
                }
            except Exception as e:
                self.logger.warning(f"Could not get final account summary: {e}")
                formatted_account = {
                    "current_balance": "$0.00",
                    "total_pnl": "$0.00",
                    "open_positions": "0",
                    "win_rate": "0.0%",
                    "daily_trades": "0"
                }
            
            # Get final positions
            try:
                positions_summary = await self.broker.get_positions_summary_async()
                final_positions = positions_summary.get("open_positions", [])
            except Exception as e:
                self.logger.warning(f"Could not get final positions: {e}")
                final_positions = []
            
            # Format final statistics
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds_remainder = int(uptime_seconds % 60)
            
            if hours > 0:
                uptime_str = f"{hours}h {minutes}m {seconds_remainder}s"
            elif minutes > 0:
                uptime_str = f"{minutes}m {seconds_remainder}s"
            else:
                uptime_str = f"{uptime_seconds:.1f} seconds"
            
            final_statistics = {
                "uptime": uptime_str,
                "trades_executed": str(self._stats.get('trades_executed', 0)),
                "successful_trades": str(self._stats.get('trades_successful', 0)),
                "failed_trades": str(self._stats.get('trades_failed', 0)),
                "signals_generated": str(self._stats.get('signals_generated', 0)),
                "websocket_updates": str(self._stats.get('websocket_updates', 0)),
                "strategy_executions": str(self._stats.get('strategies_executed', 0)),
                "total_errors": str(self.error_count)
            }
            
            # Log final statistics
            self.logger.info("📊 Final System Statistics:")
            self.logger.info(f"   ⏱️  Uptime: {uptime_str}")
            self.logger.info(f"   📊 Trades Executed: {self._stats.get('trades_executed', 0)}")
            self.logger.info(f"   ✅ Successful Trades: {self._stats.get('trades_successful', 0)}")
            self.logger.info(f"   ❌ Failed Trades: {self._stats.get('trades_failed', 0)}")
            self.logger.info(f"   🎯 Signals Generated: {self._stats.get('signals_generated', 0)}")
            self.logger.info(f"   📡 WebSocket Updates: {self._stats.get('websocket_updates', 0)}")
            self.logger.info(f"   🧠 Strategy Executions: {self._stats.get('strategies_executed', 0)}")
            self.logger.info(f"   ❌ Total Errors: {self.error_count}")
            
            # Send comprehensive shutdown notification before stopping components
            self.logger.info("📧 Sending comprehensive shutdown notification...")
            try:
                await self.notification_manager.notify_system_shutdown(
                    uptime_seconds=uptime_seconds,
                    statistics=final_statistics,
                    account_summary=formatted_account,
                    final_positions=final_positions,
                    user_id="system"
                )
                self.logger.info("✅ Shutdown notification sent successfully")
                
                # CRITICAL: Wait for email to be processed and sent
                self.logger.info("⏱️ Waiting for email delivery...")
                await asyncio.sleep(5)  # Wait 5 seconds for email processing
                self.logger.info("✅ Email delivery wait completed")
                
                # Cancel any pending notification tasks
                await self._cleanup_pending_tasks()
                
            except Exception as e:
                self.logger.error(f"❌ Failed to send shutdown notification: {e}")
                # Still wait a bit in case of partial success
                await asyncio.sleep(3)
            
            # Now proceed with normal shutdown
            self._running = False
            self._shutdown_event.set()
            
            # Stop WebSocket server
            await self.websocket_server.stop()
            
            # Stop WebSocket price system
            self.live_price_system.stop()
            
            # Wait for threads to finish
            threads = [self.strategy_thread, self.monitoring_thread]
            for thread in threads:
                if thread and thread.is_alive():
                    thread.join(timeout=10)
                    if thread.is_alive():
                        self.logger.warning(f"⚠️ Thread {thread.name} did not stop gracefully")
            
            # Shutdown strategy manager
            self.strategy_manager.shutdown()
            
            # Stop async components
            await self.broker.stop()
            await self.risk_manager.stop()
            await self.notification_manager.stop()
            
            shutdown_duration = time.time() - shutdown_start_time
            self.logger.info(f"✅ Trading system stopped successfully (shutdown took {shutdown_duration:.2f}s)")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")

    def _strategy_execution_loop(self):
        """Enhanced strategy execution loop with configurable interval"""
        strategy_interval = self.intervals['strategy_execution']
        minutes = strategy_interval // 60
        self.logger.info(f"🎯 Starting strategy execution loop ({strategy_interval}s / {minutes} minutes interval)")
        self.logger.info(f"🚨 POSITION RULE: Maximum ONE position per symbol")
        
        loop_count = 0
        while self._running and not self._shutdown_event.is_set():
            loop_count += 1
            execution_start = time.time()
            
            try:
                symbols = self.strategy_manager.get_all_symbols()
                self.logger.info(f"🔄 Strategy Loop #{loop_count} - Processing {len(symbols)} symbols: {symbols}")
                
                for symbol in symbols:
                    if self._shutdown_event.is_set():
                        break
                    
                    try:
                        # Get market data
                        with self.market_data_lock:
                            market_data = self.current_market_data.get(symbol)
                            available_symbols = list(self.current_market_data.keys())
                        
                        if market_data:
                            self.logger.info(f"📊 Processing {symbol} - Price: ${market_data.price:.2f}")
                            self._execute_strategies_for_symbol(symbol, market_data)
                        else:
                            self.logger.warning(f"⚠️ No market data available for {symbol}")
                            self.logger.warning(f"   📋 Available symbols: {available_symbols}")
                            self.logger.warning(f"   🔍 Requested symbol: '{symbol}' (type: {type(symbol)})")
                            
                            # Check if symbol exists with different case/format
                            for avail_symbol in available_symbols:
                                if avail_symbol.upper() == symbol.upper():
                                    self.logger.warning(f"   ⚠️ Found symbol with different case: '{avail_symbol}'")
                                elif symbol in avail_symbol or avail_symbol in symbol:
                                    self.logger.warning(f"   ⚠️ Found similar symbol: '{avail_symbol}'")
                            
                    except Exception as e:
                        self.logger.error(f"❌ Error executing strategies for {symbol}: {e}")
                        self._record_error(str(e))
                        continue
                
                # Record execution time
                execution_time = time.time() - execution_start
                self.strategy_execution_times.append(execution_time)
                self._stats["strategies_executed"] += 1
                
                self.logger.info(f"✅ Strategy Loop #{loop_count} completed in {execution_time:.3f}s")
                
                # Wait for next execution or shutdown
                self.logger.info(f"⏱️ Waiting {strategy_interval} seconds ({minutes} minutes) for next strategy execution...")
                if not self._shutdown_event.wait(strategy_interval):
                    continue
                else:
                    break
                    
            except Exception as e:
                self.logger.error(f"❌ Critical error in strategy execution loop #{loop_count}: {e}")
                self._record_error(str(e))
                
                if not self._shutdown_event.wait(strategy_interval):
                    continue
                else:
                    break
        
        self.logger.info("🎯 Strategy execution loop stopped")

    def _execute_strategies_for_symbol(self, symbol: str, market_data: MarketData):
        """Execute strategies for a specific symbol with comprehensive logging"""
        strategy_start_time = time.time()
        try:
            self.logger.info(f"🎯 Executing strategies for {symbol} at price ${market_data.price:.2f}")
            
            # Execute all strategies in parallel and get the best signal
            execution_start = time.time()
            strategy_result = self.strategy_manager.execute_strategies_parallel(symbol, market_data)
            execution_time = time.time() - execution_start
            selected_signal = strategy_result.selected_signal
            
            self.logger.info(f"⏱️ Strategy execution time for {symbol}: {execution_time:.3f}s")
            
            # Log all strategy results
            successful_strategies = sum(1 for result in strategy_result.strategy_results if result.success)
            total_strategies = len(strategy_result.strategy_results)
            self.logger.info(f"📈 Strategy Results for {symbol} ({successful_strategies}/{total_strategies} successful):")
            
            for result in strategy_result.strategy_results:
                if result.success:
                    self.logger.info(f"   ✅ {result.strategy_name}: {result.signal.signal} "
                                   f"(confidence: {result.signal.confidence:.1f}%, execution: {result.execution_time:.3f}s)")
                else:
                    self.logger.warning(f"   ❌ {result.strategy_name}: Failed - {result.error_message}")
            
            # Log selected signal
            self.logger.info(f"🎯 Selected Signal for {symbol}: {selected_signal.signal} "
                           f"from {selected_signal.strategy_name} "
                           f"(confidence: {selected_signal.confidence:.1f}%)")
            
            # Broadcast strategy signal to WebSocket clients
            if self._main_loop is not None:
                self.logger.debug(f"📡 Broadcasting strategy signal for {symbol}")
                asyncio.run_coroutine_threadsafe(
                    self.websocket_server.broadcast_strategy_signal(selected_signal),
                    self._main_loop
                )
            
            # Execute trade if signal is actionable
            if selected_signal.signal in (SignalType.BUY, SignalType.SELL):
                # Check if position already exists before attempting trade
                has_open_position = self.broker.has_open_position_for_symbol(symbol)
                if has_open_position:
                    existing_position = self.broker.get_open_position_for_symbol(symbol)
                    self.logger.info(f"⏸️ Signal SKIPPED for {symbol}: {selected_signal.signal}")
                    self.logger.info(f"   📊 Reason: Position already open ({existing_position.position_type.value})")
                    self.logger.info(f"   💰 Existing: {existing_position.quantity} units at ${existing_position.entry_price:.2f}")
                    self.logger.info(f"   🎯 New Signal: {selected_signal.signal.value} at ${selected_signal.price:.2f}")
                else:
                    self.logger.info(f"💰 Actionable signal detected for {symbol}: {selected_signal.signal}")
                    if self._main_loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            self._execute_signal(selected_signal),
                            self._main_loop
                        )
                    else:
                        self.logger.error("❌ Main event loop not available for trade execution")
            else:
                self.logger.info(f"⏸️ No actionable signal for {symbol} (signal: {selected_signal.signal})")
            
            self._stats["signals_generated"] += 1
            
        except Exception as e:
            self.logger.error(f"❌ Error executing strategies for {symbol}: {e}")
            self._record_error(str(e))

    def _monitoring_loop(self):
        """Background monitoring loop for system health"""
        self.logger.info("📊 Starting monitoring loop")
        
        while self._running and not self._shutdown_event.is_set():
            try:
                # Perform health checks
                health_status = self._perform_health_check()
                
                # Log system summary periodically
                if not self._shutdown_event.is_set():
                    if self._main_loop is not None:
                        asyncio.run_coroutine_threadsafe(
                            self._log_system_summary(),
                            self._main_loop
                        )
                
                # Broadcast system status
                if self._main_loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        self._broadcast_system_status(health_status),
                        self._main_loop
                    )
                
                # Wait for next check
                if not self._shutdown_event.wait(60):
                    continue
                else:
                    break
                    
            except Exception as e:
                self.logger.error(f"❌ Error in monitoring loop: {e}")
                self._record_error(str(e))
                
                if not self._shutdown_event.wait(60):
                    continue
                else:
                    break
        
        self.logger.info("📊 Monitoring loop stopped")

    def _perform_health_check(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        try:
            components = {}
            
            # Check core components
            components["broker"] = self.broker is not None
            components["risk_manager"] = self.risk_manager is not None
            components["websocket_server"] = self.websocket_server.running
            components["live_price_system"] = self.live_price_system.is_connected
            components["strategy_manager"] = len(self.strategy_manager.get_all_symbols()) > 0
            
            # Check threads
            components["strategy_thread"] = (
                self.strategy_thread is not None and self.strategy_thread.is_alive()
            )
            components["monitoring_thread"] = (
                self.monitoring_thread is not None and self.monitoring_thread.is_alive()
            )
            
            # Calculate overall health
            is_healthy = all(components.values()) and self.error_count < 10
            
            # Calculate uptime
            uptime = time.time() - self._start_time
            
            # Get memory usage
            try:
                import psutil
                memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            except:
                memory_usage = 0.0
            
            return SystemHealth(
                is_healthy=is_healthy,
                components=components,
                error_count=self.error_count,
                last_error=self.last_error,
                uptime=uptime,
                memory_usage=memory_usage
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error performing health check: {e}")
            return SystemHealth(
                is_healthy=False,
                components={},
                error_count=self.error_count + 1,
                last_error=str(e),
                uptime=time.time() - self._start_time,
                memory_usage=0.0
            )

    async def _broadcast_system_status(self, health_status: SystemHealth):
        """Broadcast system status to WebSocket clients"""
        try:
            status_data = {
                "healthy": health_status.is_healthy,
                "uptime": health_status.uptime,
                "error_count": health_status.error_count,
                "memory_usage": health_status.memory_usage,
                "components": health_status.components,
                "stats": self.get_system_stats()
            }
            
            # Broadcast to WebSocket clients
            from src.api.websocket_server import MessageType
            await self.websocket_server._broadcast_to_subscribers(
                MessageType.SYSTEM_STATUS,
                status_data
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error broadcasting system status: {e}")

    async def _execute_signal(self, signal: TradingSignal):
        """Execute a trading signal with enhanced error handling"""
        try:
            self.logger.info(f"📊 Processing signal: {signal.signal} {signal.symbol} "
                           f"from {signal.strategy_name} (confidence: {signal.confidence:.1f}%)")
            
            if signal.signal == SignalType.WAIT:
                return
            
            # CRITICAL CHECK: Only one position per symbol allowed
            has_open_position = self.broker.has_open_position_for_symbol(signal.symbol)
            if has_open_position:
                existing_position = self.broker.get_open_position_for_symbol(signal.symbol)
                
                self.logger.warning(f"🚫 Trade REJECTED: {signal.symbol} already has an open position")
                self.logger.warning(f"   📊 Existing Position: {existing_position.position_type.value} "
                                  f"qty={existing_position.quantity} entry=${existing_position.entry_price:.2f}")
                self.logger.warning(f"   🎯 New Signal: {signal.signal.value} at ${signal.price:.2f}")
                self.logger.warning(f"   💡 Reason: Only one position per symbol allowed")
                
                # Broadcast rejection notification
                await self.websocket_server.broadcast_notification(
                    "trade_rejected",
                    f"Trade rejected: {signal.symbol} already has an open position ({existing_position.position_type.value})",
                    "warning"
                )
                
                # Show position counts for debugging
                position_counts = self.broker.get_open_positions_count_by_symbol()
                self.logger.info(f"📊 Current open positions by symbol: {position_counts}")
                
                return
            
            from src.broker.paper_broker import TradeRequest
            
            # Create trade request
            trade_request = TradeRequest(
                symbol=signal.symbol,
                signal=signal.signal.value,
                price=signal.price,
                quantity=signal.quantity,
                leverage=signal.leverage,
                strategy_name=signal.strategy_name,
                confidence=signal.confidence
            )
            
            # Check risk limits
            allowed, reason = await self.risk_manager.should_allow_new_position_async(
                signal.symbol, 
                signal.price * signal.quantity
            )
            
            if not allowed:
                self.logger.warning(f"❌ Trade rejected by risk manager: {reason}")
                await self.websocket_server.broadcast_notification(
                    "trade_rejected",
                    f"Trade rejected: {reason}",
                    "warning"
                )
                return
            
            # Execute trade
            success = await self.broker.execute_trade_async(trade_request)
            
            if success:
                self._stats["trades_executed"] += 1
                self._stats["trades_successful"] += 1
                
                self.logger.info(f"✅ Trade executed: {signal.signal} {signal.symbol} "
                               f"at ${signal.price:.2f} via {signal.strategy_name}")
                
                # Send notification
                await self.notification_manager.notify_trade_execution(
                    symbol=signal.symbol,
                    signal=signal.signal.value,
                    price=signal.price,
                    trade_id=trade_request.id,
                    position_id=trade_request.position_id or "N/A"
                )
                
                # Broadcast to WebSocket clients
                await self.websocket_server.broadcast_notification(
                    "trade_executed",
                    f"Trade executed: {signal.signal} {signal.symbol} at ${signal.price:.2f}",
                    "success"
                )
                
                # Immediately broadcast updated positions and account (bypass throttling for trades)
                self._last_broadcast_time = 0.0  # Reset throttling for immediate update
                positions_summary = await self.broker.get_positions_summary_async()
                open_positions = positions_summary.get("open_positions", [])
                account_summary = await self.broker.get_account_summary_async()
                
                self.logger.info(f"📊 Broadcasting immediate updates after trade: {len(open_positions)} open positions")
                for pos in open_positions:
                    self.logger.info(f"   📈 {pos['symbol']}: {pos['position_type']} "
                                   f"qty={pos['quantity']} pnl=${pos['pnl']:.2f}")
                
                await self.websocket_server.broadcast_positions_update(open_positions)
                await self.websocket_server.broadcast_account_summary(account_summary)
                
            else:
                self._stats["trades_failed"] += 1
                self.logger.error(f"❌ Trade execution failed: {signal.symbol}")
                
                await self.websocket_server.broadcast_notification(
                    "trade_failed",
                    f"Trade execution failed for {signal.symbol}",
                    "error"
                )
                
        except Exception as e:
            self.logger.error(f"❌ Error executing signal: {e}")
            self._stats["trades_failed"] += 1
            self._record_error(str(e))

    async def _update_risk_management(self):
        """Update risk management with enhanced error handling"""
        try:
            # Monitor positions
            actions_taken = await self.risk_manager.monitor_positions_async()
            
            if actions_taken:
                self.logger.info(f"🛡️ Risk actions taken: {actions_taken}")
                
                # Broadcast risk actions to clients
                await self.websocket_server.broadcast_notification(
                    "risk_action",
                    f"Risk management actions: {actions_taken}",
                    "warning"
                )
            
            # Analyze portfolio risk
            portfolio_risk = await self.risk_manager.analyze_portfolio_risk_async()
            
            if portfolio_risk.get("overall_risk_level") in ["high", "critical"]:
                await self.notification_manager.notify_risk_alert(
                    symbol="PORTFOLIO",
                    alert_type="High Portfolio Risk",
                    current_price=0.0,
                    risk_level=portfolio_risk.get("overall_risk_level", "unknown")
                )
                
                await self.websocket_server.broadcast_notification(
                    "portfolio_risk",
                    f"Portfolio risk level: {portfolio_risk.get('overall_risk_level')}",
                    "error"
                )
                        
        except Exception as e:
            self.logger.error(f"❌ Error updating risk management: {e}")
            self._record_error(str(e))

    async def _log_system_summary(self):
        """Log comprehensive system summary with performance metrics"""
        try:
            # Get summaries
            account_summary = await self.broker.get_account_summary_async()
            positions_summary = await self.broker.get_positions_summary_async()
            strategy_stats = self.strategy_manager.get_strategy_stats()
            manager_stats = self.strategy_manager.get_manager_stats()
            websocket_stats = self.live_price_system.get_performance_stats()
            
            # Calculate performance metrics
            avg_price_update_time = (
                sum(self.price_update_times) / len(self.price_update_times)
                if self.price_update_times else 0
            )
            
            avg_strategy_time = (
                sum(self.strategy_execution_times) / len(self.strategy_execution_times)
                if self.strategy_execution_times else 0
            )
            
            self.logger.info("📊 System Summary:")
            self.logger.info(f"   💰 Balance: ${account_summary.get('current_balance', 0):.2f}")
            self.logger.info(f"   📈 Total Trades: {self._stats['trades_executed']}")
            self.logger.info(f"   🎯 Win Rate: {account_summary.get('win_rate', 0):.1f}%")
            self.logger.info(f"   📊 Open Positions: {positions_summary.get('total_open', 0)}")
            self.logger.info(f"   🚀 Signals Generated: {self._stats['signals_generated']}")
            self.logger.info(f"   📡 WebSocket Updates: {self._stats['websocket_updates']}")
            self.logger.info(f"   ⚡ Avg Price Update: {avg_price_update_time:.3f}s")
            self.logger.info(f"   🧠 Avg Strategy Time: {avg_strategy_time:.3f}s")
            self.logger.info(f"   🔌 WebSocket Status: {websocket_stats.get('status', 'unknown')}")
            self.logger.info(f"   ⏱️ Uptime: {websocket_stats.get('uptime_seconds', 0):.1f}s")
            self.logger.info(f"   🧹 Memory: {self._stats.get('memory_usage', 0):.1f} MB")
            self.logger.info(f"   ❌ Errors: {self.error_count}")
            
            # Broadcast account summary to WebSocket clients
            await self.websocket_server.broadcast_account_summary(account_summary)
            
        except Exception as e:
            self.logger.error(f"❌ Error logging system summary: {e}")
            self._record_error(str(e))

    async def delete_all_data(self) -> bool:
        """Delete all trading data with error handling"""
        try:
            self.logger.info("🗑️ Deleting all trading data...")
            success = await self.broker.delete_all_data()
            
            if success:
                self.logger.info("✅ All trading data deleted successfully")
                
                # Reset statistics
                self._stats.update({
                    "trades_executed": 0,
                    "trades_successful": 0,
                    "trades_failed": 0,
                    "total_pnl": 0.0,
                    "signals_generated": 0
                })
                
                # Broadcast deletion notification
                await self.websocket_server.broadcast_notification(
                    "data_deleted",
                    "All trading data has been deleted",
                    "info"
                )
                
                return True
            else:
                self.logger.error("❌ Failed to delete trading data")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error deleting data: {e}")
            self._record_error(str(e))
            return False

    async def run_main_loop(self):
        """Main monitoring loop with enhanced error handling"""
        self.logger.info("🔄 Starting main monitoring loop")
        self.logger.info("📋 MAIN LOOP FLOW:")
        self.logger.info("   1. Live price data collection (WebSocket)")
        self.logger.info("   2. Strategy execution every 30s")
        self.logger.info("   3. Risk management checks")
        self.logger.info("   4. Performance monitoring")
        self.logger.info("   5. WebSocket broadcasts")
        self.logger.info("   6. System maintenance every 60s")
        
        loop_iteration = 0
        while self._running and not self._shutdown_event.is_set():
            try:
                loop_iteration += 1
                loop_start = time.time()
                self.logger.debug(f"🔄 Main monitoring loop iteration #{loop_iteration}")
                
                # Perform periodic tasks
                await self._periodic_maintenance()
                
                loop_duration = time.time() - loop_start
                self.logger.debug(f"✅ Main loop iteration #{loop_iteration} completed in {loop_duration:.3f}s")
                
                # Sleep for 60 seconds or until shutdown
                try:
                    await asyncio.wait_for(asyncio.sleep(60), timeout=60)
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    pass
                
                # Check shutdown event
                if self._shutdown_event.is_set():
                    self.logger.info("🛑 Shutdown event detected, exiting main loop")
                    break
                
            except asyncio.CancelledError:
                self.logger.info("🛑 Main monitoring loop cancelled")
                break
            except KeyboardInterrupt:
                self.logger.info("🛑 Keyboard interrupt in main loop")
                self._shutdown_event.set()
                break
            except Exception as e:
                self.logger.error(f"❌ Error in main loop iteration #{loop_iteration}: {e}")
                self._record_error(str(e))
                await asyncio.sleep(10)
        
        self.logger.info("🔄 Main monitoring loop ended, initiating shutdown...")
        # Ensure shutdown is called
        if self._running:
            await self.stop()

    async def _periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        try:
            maintenance_start = time.time()
            self.logger.debug("🔧 Starting periodic maintenance tasks")
            
            # Update system statistics
            current_time = time.time()
            uptime = current_time - self._start_time
            
            # Log periodic summary and broadcast data
            if int(uptime) % 300 == 0:  # Every 5 minutes
                self.logger.info("📊 Generating 5-minute system summary...")
                await self._log_system_summary()
                self.logger.debug("✅ System summary completed")
            
            # Removed periodic broadcasting - now using real-time updates in price callback
            
            # Check for memory leaks (every hour)
            if int(uptime) % 3600 == 0:
                self.logger.info("🧹 Running hourly memory management check...")
                self._check_memory_management()
                self.logger.debug("✅ Memory management check completed")
                
            maintenance_duration = time.time() - maintenance_start
            self.logger.debug(f"✅ Periodic maintenance completed in {maintenance_duration:.3f}s")
            
            # Cleanup old data (daily)
            if int(uptime) % 86400 == 0:
                await self._cleanup_old_data()
                
        except Exception as e:
            self.logger.error(f"❌ Error in periodic maintenance: {e}")

    async def _cleanup_old_data(self):
        """Cleanup old data for memory management"""
        try:
            from src.database.mongodb_client import AsyncMongoDBClient
            
            client = AsyncMongoDBClient()
            await client.cleanup_old_data(days=90)
            
            self.logger.info("🧹 Old data cleanup completed")
            
        except Exception as e:
            self.logger.error(f"❌ Error during data cleanup: {e}")


    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            **self._stats,
            "system_running": self._running,
            "uptime": time.time() - self._start_time,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "strategy_thread_alive": (
                self.strategy_thread.is_alive() if self.strategy_thread else False
            ),
            "monitoring_thread_alive": (
                self.monitoring_thread.is_alive() if self.monitoring_thread else False
            ),
            "active_symbols": len(self.current_market_data),
            "strategy_stats": self.strategy_manager.get_strategy_stats(),
            "manager_stats": self.strategy_manager.get_manager_stats(),
            "websocket_stats": self.live_price_system.get_performance_stats(),
            "websocket_server_stats": self.websocket_server.get_server_stats(),
            "circuit_breaker_status": {
                name: {"state": cb.state, "failure_count": cb.failure_count}
                for name, cb in self.circuit_breakers.items()
            },
            "avg_price_update_time": (
                sum(self.price_update_times) / len(self.price_update_times)
                if self.price_update_times else 0
            ),
            "avg_strategy_execution_time": (
                sum(self.strategy_execution_times) / len(self.strategy_execution_times)
                if self.strategy_execution_times else 0
            )
        }

    def get_health_status(self) -> SystemHealth:
        """Get current system health status"""
        return self._perform_health_check()
    
    async def _cleanup_pending_tasks(self):
        """Clean up any pending async tasks to prevent 'Task was destroyed' warnings"""
        try:
            self.logger.info("🧹 Cleaning up pending async tasks...")
            
            # Get all pending tasks
            pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
            
            if pending_tasks:
                self.logger.info(f"📋 Found {len(pending_tasks)} pending tasks")
                
                # Cancel notification manager tasks first
                if hasattr(self.notification_manager, '_notification_task') and self.notification_manager._notification_task:
                    self.notification_manager._notification_task.cancel()
                    try:
                        await asyncio.wait_for(self.notification_manager._notification_task, timeout=2.0)
                    except (asyncio.CancelledError, asyncio.TimeoutError):
                        pass
                
                # Cancel other pending tasks with timeout
                for task in pending_tasks:
                    if not task.done() and task != asyncio.current_task():
                        task.cancel()
                
                # Wait for cancellation with timeout
                if pending_tasks:
                    await asyncio.wait(pending_tasks, timeout=3.0, return_when=asyncio.ALL_COMPLETED)
                
                self.logger.info("✅ Async task cleanup completed")
            else:
                self.logger.info("✅ No pending tasks to clean up")
                
        except Exception as e:
            self.logger.warning(f"⚠️ Error during task cleanup: {e}")


# Legacy compatibility
ImprovedTradingSystem = TradingSystem