#!/usr/bin/env python3
"""
Improved High-Speed Trading System with Independent Strategy Classes
Features:
- Independent strategy classes with signal() method
- Separate threads for strategy execution (30s) and price updates (5s)
- Proper risk management integration
- Real-time price-dependent calculations

Usage:
    python improved_app.py
    python improved_app.py --delete  # Delete all data
"""

import asyncio
import logging
import signal
import sys
import time
import argparse
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from enum import Enum
import os
import random
from dataclasses import dataclass

# Import simplified components
from src.broker.paper_broker import AsyncBroker
from src.risk_manager import AsyncRiskManager
from src.notifications import NotificationManager
from src.config import get_settings, get_dummy_settings
# NEW IMPORTS
from src.live_price import LivePriceFetcher
from src.strategy_manager import StrategyManager
from src.schemas import TradingSignal, MarketData, SignalType

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/trading.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("trading")


# SignalType, TradingSignal, and MarketData are now imported from schemas


# Strategy classes are now in src/strategies.py and StrategyManager is in src/strategy_manager.py


class PriceGenerator:
    """Generate realistic price movements"""
    
    def __init__(self):
        self.logger = logging.getLogger("price_generator")
        self.base_prices = {
            "BTC-USD": 50000.0,
            "ETH-USD": 3000.0
        }
        self.current_prices = self.base_prices.copy()
        self.price_history = {symbol: [] for symbol in self.base_prices}
        self.volatility = {
            "BTC-USD": 0.03,
            "ETH-USD": 0.04
        }
        
    def generate_market_data(self, symbol: str) -> MarketData:
        """Generate realistic market data for a symbol"""
        if symbol not in self.current_prices:
            self.current_prices[symbol] = 100.0
            self.volatility[symbol] = 0.02
        
        # Generate price movement
        volatility = self.volatility[symbol]
        change_percent = random.normalvariate(0, volatility)
        
        # Apply trend bias (small upward bias)
        trend_bias = 0.0001
        change_percent += trend_bias
        
        # Update price
        old_price = self.current_prices[symbol]
        new_price = old_price * (1 + change_percent)
        self.current_prices[symbol] = new_price
        
        # Update price history
        self.price_history[symbol].append(new_price)
        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol].pop(0)
        
        # Calculate 24h high/low
        recent_prices = self.price_history[symbol][-288:]  # Last 24h (5s intervals)
        high_24h = max(recent_prices) if recent_prices else new_price
        low_24h = min(recent_prices) if recent_prices else new_price
        
        # Generate bid/ask spread
        spread = new_price * 0.001  # 0.1% spread
        bid = new_price - spread / 2
        ask = new_price + spread / 2
        
        return MarketData(
            symbol=symbol,
            price=new_price,
            volume=random.uniform(100, 1000),
            change=change_percent * 100,
            timestamp=datetime.now(timezone.utc),
            high_24h=high_24h,
            low_24h=low_24h,
            bid=bid,
            ask=ask
        )
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        return self.current_prices.get(symbol, 0.0)


class ImprovedTradingSystem:
    """Improved trading system with strategy classes and threading"""
    
    def __init__(self):
        """Initialize the improved trading system"""
        self.settings = get_settings()
        self.dummy_settings = get_dummy_settings()
        self.logger = logging.getLogger("improved_trading_system")
        
        # Initialize components
        self.broker = AsyncBroker()
        self.risk_manager = AsyncRiskManager(self.broker)
        self.notification_manager = NotificationManager()
        self.strategy_manager = StrategyManager(max_workers=4)
        self.live_price_fetcher = LivePriceFetcher()
        
        # Control flags
        self._running = False
        self._shutdown_event = threading.Event()
        
        # Threading
        self.price_thread = None
        self.strategy_thread = None
        
        # Current market data
        self.current_market_data: Dict[str, MarketData] = {}
        self.market_data_lock = threading.Lock()
        
        # Statistics
        self._stats = {
            "trades_executed": 0,
            "trades_successful": 0,
            "trades_failed": 0,
            "total_pnl": 0.0,
            "signals_generated": 0,
            "price_updates": 0,
            "strategies_executed": 0
        }
        # Store main event loop reference (will be set in start)
        self._main_loop = None
        
        # Setup strategies
        self._setup_strategies()
        
        self.logger.info("Improved trading system initialized")

    def _setup_strategies(self):
        """Setup trading strategies for different symbols"""
        symbols = ["BTC-USD", "ETH-USD"]
        # Add default strategies (Random, Volatility, MovingAverage, RSI) for each symbol
        self.strategy_manager.add_default_strategies(symbols)
        self.logger.info(f"Setup default strategies for {len(symbols)} symbols")

    async def start(self) -> bool:
        """Start the trading system"""
        try:
            self.logger.info("🚀 Starting Improved Trading System")
            # Store the main event loop
            self._main_loop = asyncio.get_running_loop()
            # Start all async components
            if not await self.broker.start():
                self.logger.error("❌ Failed to start broker")
                return False
            if not await self.risk_manager.start():
                self.logger.error("❌ Failed to start risk manager")
                return False
            await self.notification_manager.start()
            # Start threading components
            self._running = True
            self.price_thread = threading.Thread(target=self._price_update_loop, daemon=True)
            self.strategy_thread = threading.Thread(target=self._strategy_execution_loop, daemon=True)
            self.price_thread.start()
            self.strategy_thread.start()
            # Send startup notification
            await self.notification_manager.notify_system_error(
                error_message="Improved system started successfully",
                component="ImprovedTradingSystem"
            )
            self.logger.info("✅ Improved trading system started successfully")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading system: {e}")
            return False
    
    async def stop(self):
        """Stop the trading system"""
        if not self._running:
            return
        
        self.logger.info("🛑 Stopping Improved Trading System")
        self._running = False
        self._shutdown_event.set()
        
        # Wait for threads to finish
        if self.price_thread and self.price_thread.is_alive():
            self.price_thread.join(timeout=10)
        
        if self.strategy_thread and self.strategy_thread.is_alive():
            self.strategy_thread.join(timeout=10)
        
        # Shutdown strategy manager
        self.strategy_manager.shutdown()
        
        # Stop async components
        await self.broker.stop()
        await self.risk_manager.stop()
        await self.notification_manager.stop()
        
        self.logger.info("✅ Improved trading system stopped")
    
    def _price_update_loop(self):
        """Price update loop - runs every 5 seconds"""
        self.logger.info("📈 Starting price update loop (5s interval)")
        while self._running and not self._shutdown_event.is_set():
            try:
                symbols = self.strategy_manager.get_all_symbols()
                prices = {}
                for symbol in symbols:
                    price = self.live_price_fetcher.get_price(symbol)
                    market_data = MarketData(
                        symbol=symbol,
                        price=price,
                        volume=0.0,
                        change=0.0,
                        timestamp=datetime.now(timezone.utc),
                        high_24h=price,
                        low_24h=price,
                        bid=price-0.1,
                        ask=price+0.1
                    )
                    with self.market_data_lock:
                        self.current_market_data[symbol] = market_data
                    prices[symbol] = {"price": price}
                # Use the main event loop for all async calls from this thread
                if self._main_loop is not None:
                    asyncio.run_coroutine_threadsafe(
                        self.broker.update_prices_async(prices),
                        self._main_loop
                    )
                    self._print_account_and_positions(prices)
                    asyncio.run_coroutine_threadsafe(
                        self._update_risk_management(),
                        self._main_loop
                    )
                else:
                    self.logger.error("Main event loop not set!")
                self._stats["price_updates"] += 1
                if not self._shutdown_event.wait(5):
                    continue
                else:
                    break
            except Exception as e:
                self.logger.error(f"Error in price update loop: {e}")
                if not self._shutdown_event.wait(5):
                    continue
                else:
                    break
        self.logger.info("📈 Price update loop stopped")

    def _strategy_execution_loop(self):
        """Strategy execution loop - runs every 30 seconds"""
        self.logger.info("🎯 Starting strategy execution loop (30s interval)")
        while self._running and not self._shutdown_event.is_set():
            try:
                symbols = self.strategy_manager.get_all_symbols()
                for symbol in symbols:
                    with self.market_data_lock:
                        market_data = self.current_market_data.get(symbol)
                    
                    if market_data:
                        # Execute all strategies in parallel and get the best signal
                        strategy_result = self.strategy_manager.execute_strategies_parallel(symbol, market_data)
                        selected_signal = strategy_result.selected_signal
                        
                        self.logger.info(f"[StrategyManager] {symbol}: {selected_signal.signal} "
                                       f"from {selected_signal.strategy_name} "
                                       f"(confidence: {selected_signal.confidence:.1f}%)")
                        
                        # Log all strategy results
                        for result in strategy_result.strategy_results:
                            self.logger.info(f"  - {result.strategy_name}: {result.signal.signal} "
                                           f"(confidence: {result.signal.confidence:.1f}%)")
                        
                        # If signal is actionable, execute trade
                        if selected_signal.signal in (SignalType.BUY, SignalType.SELL):
                            if self._main_loop is not None:
                                asyncio.run_coroutine_threadsafe(
                                    self._execute_signal(selected_signal),
                                    self._main_loop
                                )
                            else:
                                self.logger.error("Main event loop not set for trade execution!")
                        
                        self._stats["signals_generated"] += 1
                
                self._stats["strategies_executed"] += 1
                if not self._shutdown_event.wait(30):
                    continue
                else:
                    break
            except Exception as e:
                self.logger.error(f"Error in strategy execution loop: {e}")
                if not self._shutdown_event.wait(30):
                    continue
                else:
                    break
        self.logger.info("🎯 Strategy execution loop stopped")

    def _print_account_and_positions(self, prices: Dict[str, Dict[str, float]]):
        """Print account and open positions' unrealized PnL (no DB update)"""
        async def print_async():
            account = await self.broker.get_account_summary_async()
            positions = await self.broker.get_positions_summary_async()
            print("---------------------------------------------------------------")
            print("\n[Prices]")
            for symbol, price in prices.items():
                print(f"{symbol}: ${price['price']:.2f}")
            print("\n[Account Summary]")
            print(f"Current Balance: ${account.get('current_balance', 0):.2f} out of ${account.get('initial_balance', 0):.2f}")
            print(f"Realized PnL: ${account.get('realized_pnl', 0):.2f} | Unrealized PnL: ${account.get('total_unrealized_pnl', 0):.2f}")
            print(f"Total Trades: {account.get('total_trades', 0)}")
            print(f"Profitable / Losing Trades: {account.get('profitable_trades', 0)} / {account.get('losing_trades', 0)}")
            print(f"Win Rate: {account.get('win_rate', 0):.2f}%")
            print(f"Daily Trades: {account.get('daily_trades_count', 0)} / {account.get('daily_trades_limit', 0)}")
            print(f"Total Margin Used: ${account.get('total_margin_used', 0):.2f}")
            print(f"Brokerage Charges: ${account.get('brokerage_charges', 0):.2f}")
            print("[Open Positions]")
            for pos in positions.get('open_positions', []):
                print(f"{pos['symbol']} | Qty: {pos['quantity']} | Entry: {pos['entry_price']} | PnL: {pos['pnl']:.2f} | PnL%: {pos['pnl_percentage']:.2f}%")
            print("---------------------------------------------------------------")

        if self._main_loop is not None:
            asyncio.run_coroutine_threadsafe(print_async(), self._main_loop)
        else:
            self.logger.error("Main event loop not set for print!")
    
    async def _execute_signal(self, signal: TradingSignal):
        """Execute a trading signal"""
        try:
            self.logger.info(f"📊 Processing signal: {signal.signal} {signal.symbol} "
                           f"from {signal.strategy_name} (confidence: {signal.confidence:.1f}%)")
            
            # Check if signal is actionable
            if signal.signal == SignalType.WAIT:
                return
            
            # Import TradeRequest from broker
            from src.broker.paper_broker import TradeRequest
            
            # Create trade request
            trade_request = TradeRequest(
                symbol=signal.symbol,
                signal=signal.signal.value,  # Convert enum to string
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
                    signal=signal.signal.value,  # Convert enum to string
                    price=signal.price,
                    trade_id=trade_request.id,
                    position_id=trade_request.position_id or "N/A"
                )
                
            else:
                self._stats["trades_failed"] += 1
                self.logger.error(f"❌ Trade execution failed: {signal.symbol}")
                
        except Exception as e:
            self.logger.error(f"Error executing signal: {e}")
            self._stats["trades_failed"] += 1
    
    async def _update_risk_management(self):
        """Update risk management based on current prices"""
        try:
            # Monitor positions
            actions_taken = await self.risk_manager.monitor_positions_async()
            
            if actions_taken:
                self.logger.info(f"🛡️ Risk actions taken: {actions_taken}")
            
            # Analyze portfolio risk
            portfolio_risk = await self.risk_manager.analyze_portfolio_risk_async()
            
            if portfolio_risk.get("overall_risk_level") in ["high", "critical"]:
                await self.notification_manager.notify_risk_alert(
                    symbol="PORTFOLIO",
                    alert_type="High Portfolio Risk",
                    current_price=0.0,
                    risk_level=portfolio_risk.get("overall_risk_level", "unknown")
                )
                        
        except Exception as e:
            self.logger.error(f"Error updating risk management: {e}")
    
    async def delete_all_data(self) -> bool:
        """Delete all trading data"""
        try:
            self.logger.info("🗑️ Deleting all trading data...")
            success = await self.broker.delete_all_data()
            
            if success:
                self.logger.info("✅ All trading data deleted successfully")
                return True
            else:
                self.logger.error("❌ Failed to delete trading data")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error deleting data: {e}")
            return False
    
    async def run_main_loop(self):
        """Main monitoring loop"""
        self.logger.info("🔄 Starting main monitoring loop")
        
        while self._running and not self._shutdown_event.is_set():
            try:
                # Log system summary every 60 seconds
                await self._log_system_summary()
                
                # Check system health
                await self._check_system_health()
                
                # Sleep for 60 seconds
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(10)
    
    async def _log_system_summary(self):
        """Log comprehensive system summary"""
        try:
            # Get various summaries
            account_summary = await self.broker.get_account_summary_async()
            positions_summary = await self.broker.get_positions_summary_async()
            strategy_stats = self.strategy_manager.get_strategy_stats()
            manager_stats = self.strategy_manager.get_manager_stats()
            
            self.logger.info("📊 System Summary:")
            self.logger.info(f"   Account Balance: ${account_summary.get('current_balance', 0):.2f}")
            self.logger.info(f"   Total Trades: {self._stats['trades_executed']}")
            self.logger.info(f"   Win Rate: {account_summary.get('win_rate', 0):.1f}%")
            self.logger.info(f"   Open Positions: {positions_summary.get('total_open', 0)}")
            self.logger.info(f"   Signals Generated: {self._stats['signals_generated']}")
            self.logger.info(f"   Price Updates: {self._stats['price_updates']}")
            self.logger.info(f"   Strategy Executions: {manager_stats.get('total_executions', 0)}")
            self.logger.info(f"   Strategy Success Rate: {manager_stats.get('success_rate', 0):.1f}%")
            self.logger.info(f"   Active Strategies: {manager_stats.get('total_strategies', 0)}")
            
        except Exception as e:
            self.logger.error(f"Error logging system summary: {e}")
    
    async def _check_system_health(self):
        """Check system health and performance"""
        try:
            # Check if threads are alive
            if self.price_thread and not self.price_thread.is_alive():
                self.logger.error("❌ Price update thread died")
                
            if self.strategy_thread and not self.strategy_thread.is_alive():
                self.logger.error("❌ Strategy execution thread died")
            
            # Check broker connection
            broker_stats = self.broker.get_performance_stats()
            if not broker_stats.get("mongodb_connected", False):
                self.logger.warning("⚠️ MongoDB connection lost")
            
        except Exception as e:
            self.logger.error(f"Error checking system health: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        return {
            **self._stats,
            "system_running": self._running,
            "price_thread_alive": self.price_thread.is_alive() if self.price_thread else False,
            "strategy_thread_alive": self.strategy_thread.is_alive() if self.strategy_thread else False,
            "active_symbols": len(self.current_market_data),
            "strategy_stats": self.strategy_manager.get_strategy_stats(),
            "manager_stats": self.strategy_manager.get_manager_stats()
        }


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Improved Trading System")
    parser.add_argument(
        "--new", 
        action="store_true", 
        help="Delete all trading data from database and start a new session"
    )
    return parser.parse_args()


async def main():
    """Main function to run the improved trading system"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Create trading system
    trading_system = ImprovedTradingSystem()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        trading_system._shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Handle --new flag
        if args.new:
            logger.info("🗑️ Deleting all trading data...")
            await trading_system.delete_all_data()
            logger.info("✅ Data deletion completed")
    
        
        # Start the system
        if not await trading_system.start():
            logger.error("Failed to start trading system")
            return
        
        # Run main monitoring loop
        await trading_system.run_main_loop()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        # Stop the system
        await trading_system.stop()
        
        # Log final statistics
        final_stats = trading_system.get_system_stats()
        logger.info("📊 Final System Statistics:")
        for key, value in final_stats.items():
            if key != "strategy_stats":
                logger.info(f"   {key}: {value}")


if __name__ == "__main__":
    # Run the improved trading system
    asyncio.run(main())