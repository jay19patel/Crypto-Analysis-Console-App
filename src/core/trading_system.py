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
from src.config import get_settings, get_dummy_settings
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
    
    def __init__(self, live_save: bool = False, websocket_port: int = 8765):
        """Initialize the trading system with all components"""
        self.settings = get_settings()
        self.dummy_settings = get_dummy_settings()
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
            self.notification_manager = NotificationManager()
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
        
        # Setup strategies
        self._setup_strategies()
        
        # Memory management
        self._last_gc_time = time.time()
        self._gc_interval = 300  # 5 minutes
        
        self.logger.info("✅ Trading system initialized successfully")

    def _setup_strategies(self):
        """Setup trading strategies for different symbols with error handling"""
        try:
            symbols = ["BTCUSD", "ETHUSD"]
            historical_data_provider = HistoricalDataProvider()
            
            self.strategy_manager.add_default_strategies(
                symbols, 
                historical_data_provider=historical_data_provider
            )
            
            self.logger.info(f"✅ Setup strategies for {len(symbols)} symbols")
            
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
                    
                    # Live save logic with circuit breaker
                    if self.live_save:
                        self._handle_live_save(market_data)
                    
                    # Update broker prices with circuit breaker
                    if self._main_loop is not None:
                        self._update_broker_prices_safe(symbol, price_data)
                        self._update_risk_management_safe()
                    
                    # Broadcast to WebSocket clients
                    self._broadcast_price_update_safe(live_prices)
                    
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
            
            # Store the main event loop
            self._main_loop = asyncio.get_running_loop()
            
            # Start WebSocket server first
            if not await self.websocket_server.start():
                self.logger.error("❌ Failed to start WebSocket server")
                return False
            
            # Start WebSocket live price system
            if not self.live_price_system.start():
                self.logger.error("❌ Failed to start WebSocket live price system")
                await self.websocket_server.stop()
                return False
            
            # Start all async components with error handling
            components = [
                ("broker", self.broker.start()),
                ("risk_manager", self.risk_manager.start()),
                ("notification_manager", self.notification_manager.start())
            ]
            
            for name, coro in components:
                try:
                    if not await coro:
                        self.logger.error(f"❌ Failed to start {name}")
                        await self.stop()
                        return False
                except Exception as e:
                    self.logger.error(f"❌ Error starting {name}: {e}")
                    await self.stop()
                    return False
            
            # Start threading components
            self._running = True
            
            self.strategy_thread = threading.Thread(
                target=self._strategy_execution_loop, 
                daemon=True,
                name="StrategyThread"
            )
            self.strategy_thread.start()
            
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True,
                name="MonitoringThread"
            )
            self.monitoring_thread.start()
            
            # Send startup notification
            await self.notification_manager.notify_system_error(
                error_message="Professional trading system started successfully",
                component="TradingSystem"
            )
            
            # Broadcast system status
            await self.websocket_server.broadcast_notification(
                "system_startup",
                "Trading system started successfully",
                "info"
            )
            
            self.logger.info("✅ Trading system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading system: {e}")
            self._record_error(str(e))
            await self.stop()
            return False

    async def stop(self):
        """Stop the trading system with proper cleanup"""
        if not self._running:
            return
        
        self.logger.info("🛑 Stopping Trading System")
        self._running = False
        self._shutdown_event.set()
        
        try:
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
            
            self.logger.info("✅ Trading system stopped successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")

    def _strategy_execution_loop(self):
        """Enhanced strategy execution loop with error handling"""
        self.logger.info("🎯 Starting strategy execution loop (30s interval)")
        
        while self._running and not self._shutdown_event.is_set():
            execution_start = time.time()
            
            try:
                symbols = self.strategy_manager.get_all_symbols()
                
                for symbol in symbols:
                    if self._shutdown_event.is_set():
                        break
                    
                    try:
                        with self.market_data_lock:
                            market_data = self.current_market_data.get(symbol)
                        
                        if market_data:
                            self._execute_strategies_for_symbol(symbol, market_data)
                            
                    except Exception as e:
                        self.logger.error(f"❌ Error executing strategies for {symbol}: {e}")
                        self._record_error(str(e))
                        continue
                
                # Record execution time
                execution_time = time.time() - execution_start
                self.strategy_execution_times.append(execution_time)
                self._stats["strategies_executed"] += 1
                
                # Wait for next execution or shutdown
                if not self._shutdown_event.wait(30):
                    continue
                else:
                    break
                    
            except Exception as e:
                self.logger.error(f"❌ Critical error in strategy execution loop: {e}")
                self._record_error(str(e))
                
                if not self._shutdown_event.wait(30):
                    continue
                else:
                    break
        
        self.logger.info("🎯 Strategy execution loop stopped")

    def _execute_strategies_for_symbol(self, symbol: str, market_data: MarketData):
        """Execute strategies for a specific symbol with error handling"""
        try:
            # Execute all strategies in parallel and get the best signal
            strategy_result = self.strategy_manager.execute_strategies_parallel(symbol, market_data)
            selected_signal = strategy_result.selected_signal
            
            self.logger.info(f"[Strategy] {symbol}: {selected_signal.signal} "
                           f"from {selected_signal.strategy_name} "
                           f"(confidence: {selected_signal.confidence:.1f}%)")
            
            # Broadcast strategy signal to WebSocket clients
            if self._main_loop is not None:
                asyncio.run_coroutine_threadsafe(
                    self.websocket_server.broadcast_strategy_signal(selected_signal),
                    self._main_loop
                )
            
            # Execute trade if signal is actionable
            if selected_signal.signal in (SignalType.BUY, SignalType.SELL):
                if self._main_loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        self._execute_signal(selected_signal),
                        self._main_loop
                    )
                else:
                    self.logger.error("❌ Main event loop not available for trade execution")
            
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
            await self.websocket_server._broadcast_to_subscribers(
                self.websocket_server.MessageType.SYSTEM_STATUS,
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
                
                # Broadcast updated positions
                positions_summary = await self.broker.get_positions_summary_async()
                await self.websocket_server.broadcast_positions_update(
                    positions_summary.get("open_positions", [])
                )
                
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
        
        while self._running and not self._shutdown_event.is_set():
            try:
                # Perform periodic tasks
                await self._periodic_maintenance()
                
                # Sleep for 60 seconds or until shutdown
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"❌ Error in main loop: {e}")
                self._record_error(str(e))
                await asyncio.sleep(10)

    async def _periodic_maintenance(self):
        """Perform periodic maintenance tasks"""
        try:
            # Update system statistics
            current_time = time.time()
            uptime = current_time - self._start_time
            
            # Log periodic summary
            if int(uptime) % 300 == 0:  # Every 5 minutes
                await self._log_system_summary()
            
            # Check for memory leaks (every hour)
            if int(uptime) % 3600 == 0:
                self._check_memory_management()
            
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


# Legacy compatibility
ImprovedTradingSystem = TradingSystem