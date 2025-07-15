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
from src.broker.paper_broker import AsyncBroker, TradeRequest
from src.risk_manager import AsyncRiskManager
from src.notifications import NotificationManager
from src.config import get_settings, get_dummy_settings
# NEW IMPORTS
from src.live_price import LivePriceFetcher
from src.strategies import RandomStrategy

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


class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    WAIT = "WAIT"


@dataclass
class TradingSignal:
    """Trading signal with additional metadata"""
    signal: SignalType
    symbol: str
    confidence: float
    strategy_name: str
    price: float
    quantity: float = 0.01
    leverage: float = 1.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class MarketData:
    """Market data structure"""
    symbol: str
    price: float
    volume: float
    change: float
    timestamp: datetime
    high_24h: float
    low_24h: float
    bid: float
    ask: float


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, symbol: str, name: str):
        self.symbol = symbol
        self.name = name
        self.logger = logging.getLogger(f"strategy.{name}")
        self.price_history = []
        self.last_signal = SignalType.WAIT
        self.signal_count = {"BUY": 0, "SELL": 0, "WAIT": 0}
        
    @abstractmethod
    def signal(self, market_data: MarketData) -> TradingSignal:
        """Generate trading signal based on market data"""
        pass
    
    def update_price_history(self, price: float):
        """Update price history for technical analysis"""
        self.price_history.append(price)
        # Keep only last 100 prices for memory efficiency
        if len(self.price_history) > 100:
            self.price_history.pop(0)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        total_signals = sum(self.signal_count.values())
        return {
            "name": self.name,
            "symbol": self.symbol,
            "total_signals": total_signals,
            "signal_distribution": self.signal_count,
            "last_signal": self.last_signal.value,
            "price_history_length": len(self.price_history)
        }


class MovingAverageStrategy(BaseStrategy):
    """Moving Average Crossover Strategy"""
    
    def __init__(self, symbol: str, short_window: int = 5, long_window: int = 20):
        super().__init__(symbol, f"MA_{short_window}_{long_window}")
        self.short_window = short_window
        self.long_window = long_window
        
    def signal(self, market_data: MarketData) -> TradingSignal:
        """Generate signal based on moving average crossover"""
        self.update_price_history(market_data.price)
        
        if len(self.price_history) < self.long_window:
            signal_type = SignalType.WAIT
            confidence = 0.0
        else:
            # Calculate moving averages
            short_ma = sum(self.price_history[-self.short_window:]) / self.short_window
            long_ma = sum(self.price_history[-self.long_window:]) / self.long_window
            
            # Generate signal
            if short_ma > long_ma and self.last_signal != SignalType.BUY:
                signal_type = SignalType.BUY
                confidence = min(95.0, 70.0 + abs(short_ma - long_ma) / long_ma * 100)
            elif short_ma < long_ma and self.last_signal != SignalType.SELL:
                signal_type = SignalType.SELL
                confidence = min(95.0, 70.0 + abs(short_ma - long_ma) / long_ma * 100)
            else:
                signal_type = SignalType.WAIT
                confidence = 50.0
        
        self.last_signal = signal_type
        self.signal_count[signal_type.value] += 1
        
        return TradingSignal(
            signal=signal_type,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.01
        )


class RSIStrategy(BaseStrategy):
    """RSI (Relative Strength Index) Strategy"""
    
    def __init__(self, symbol: str, period: int = 14, overbought: float = 70.0, oversold: float = 30.0):
        super().__init__(symbol, f"RSI_{period}")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        
    def calculate_rsi(self, prices: List[float]) -> float:
        """Calculate RSI value"""
        if len(prices) < self.period + 1:
            return 50.0  # Neutral RSI
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [max(0, delta) for delta in deltas]
        losses = [abs(min(0, delta)) for delta in deltas]
        
        # Calculate average gain and loss
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def signal(self, market_data: MarketData) -> TradingSignal:
        """Generate signal based on RSI"""
        self.update_price_history(market_data.price)
        
        if len(self.price_history) < self.period + 1:
            signal_type = SignalType.WAIT
            confidence = 0.0
        else:
            rsi = self.calculate_rsi(self.price_history)
            
            if rsi < self.oversold:
                signal_type = SignalType.BUY
                confidence = min(95.0, 70.0 + (self.oversold - rsi) / self.oversold * 25)
            elif rsi > self.overbought:
                signal_type = SignalType.SELL
                confidence = min(95.0, 70.0 + (rsi - self.overbought) / (100 - self.overbought) * 25)
            else:
                signal_type = SignalType.WAIT
                confidence = 50.0
        
        self.last_signal = signal_type
        self.signal_count[signal_type.value] += 1
        
        return TradingSignal(
            signal=signal_type,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.01
        )


class MomentumStrategy(BaseStrategy):
    """Momentum Strategy based on price changes"""
    
    def __init__(self, symbol: str, lookback: int = 10, threshold: float = 0.02):
        super().__init__(symbol, f"Momentum_{lookback}")
        self.lookback = lookback
        self.threshold = threshold
        
    def signal(self, market_data: MarketData) -> TradingSignal:
        """Generate signal based on momentum"""
        self.update_price_history(market_data.price)
        
        if len(self.price_history) < self.lookback:
            signal_type = SignalType.WAIT
            confidence = 0.0
        else:
            # Calculate momentum
            old_price = self.price_history[-self.lookback]
            current_price = market_data.price
            momentum = (current_price - old_price) / old_price
            
            if momentum > self.threshold:
                signal_type = SignalType.BUY
                confidence = min(95.0, 70.0 + abs(momentum) * 500)
            elif momentum < -self.threshold:
                signal_type = SignalType.SELL
                confidence = min(95.0, 70.0 + abs(momentum) * 500)
            else:
                signal_type = SignalType.WAIT
                confidence = 50.0
        
        self.last_signal = signal_type
        self.signal_count[signal_type.value] += 1
        
        return TradingSignal(
            signal=signal_type,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.01
        )


class StrategyManager:
    """Manager for all trading strategies"""
    
    def __init__(self):
        self.strategies: Dict[str, List[BaseStrategy]] = {}
        self.logger = logging.getLogger("strategy_manager")
        
    def add_strategy(self, strategy: BaseStrategy):
        """Add a strategy to the manager"""
        if strategy.symbol not in self.strategies:
            self.strategies[strategy.symbol] = []
        
        self.strategies[strategy.symbol].append(strategy)
        self.logger.info(f"Added strategy {strategy.name} for {strategy.symbol}")
    
    def get_signals(self, symbol: str, market_data: MarketData) -> List[TradingSignal]:
        """Get all signals for a symbol"""
        signals = []
        
        if symbol in self.strategies:
            for strategy in self.strategies[symbol]:
                try:
                    signal = strategy.signal(market_data)
                    signals.append(signal)
                except Exception as e:
                    self.logger.error(f"Error getting signal from {strategy.name}: {e}")
        
        return signals
    
    def get_all_symbols(self) -> List[str]:
        """Get all symbols with strategies"""
        return list(self.strategies.keys())
    
    def get_strategy_stats(self) -> Dict[str, Any]:
        """Get statistics for all strategies"""
        stats = {}
        for symbol, strategies in self.strategies.items():
            stats[symbol] = [strategy.get_stats() for strategy in strategies]
        return stats


class PriceGenerator:
    """Generate realistic price movements"""
    
    def __init__(self):
        self.logger = logging.getLogger("price_generator")
        self.base_prices = {
            "BTC-USD": 50000.0,
            "ETH-USD": 3000.0,
            "AAPL": 150.0,
            "GOOGL": 2800.0,
            "TSLA": 800.0
        }
        self.current_prices = self.base_prices.copy()
        self.price_history = {symbol: [] for symbol in self.base_prices}
        self.volatility = {
            "BTC-USD": 0.03,
            "ETH-USD": 0.04,
            "AAPL": 0.02,
            "GOOGL": 0.025,
            "TSLA": 0.05
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
        self.strategy_manager = StrategyManager()
        # REPLACE price_generator with live_price_fetcher
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
        
        # Setup strategies
        self._setup_strategies()
        
        self.logger.info("Improved trading system initialized")

    def _setup_strategies(self):
        """Setup trading strategies for different symbols"""
        symbols = ["BTC-USD", "ETH-USD", "AAPL", "GOOGL", "TSLA"]
        self.random_strategies = {}
        for symbol in symbols:
            # Add random strategy per symbol
            self.random_strategies[symbol] = RandomStrategy(symbol)
        self.logger.info(f"Setup random strategies for {len(symbols)} symbols")

    async def start(self) -> bool:
        """Start the trading system"""
        try:
            self.logger.info("🚀 Starting Improved Trading System")
            
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
                symbols = list(self.random_strategies.keys())
                prices = {}
                for symbol in symbols:
                    # Get live price
                    price = self.live_price_fetcher.get_price(symbol)
                    # Build market data (minimal for demo)
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
                # Update broker prices (this will update position PnLs in memory)
                asyncio.run_coroutine_threadsafe(
                    self.broker.update_prices_async(prices),
                    asyncio.get_event_loop()
                )
                # Print account and open positions' unrealized PnL
                self._print_account_and_positions()
                # Call risk management
                asyncio.run_coroutine_threadsafe(
                    self._update_risk_management(),
                    asyncio.get_event_loop()
                )
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
                symbols = list(self.random_strategies.keys())
                for symbol in symbols:
                    # Get current market data
                    with self.market_data_lock:
                        market_data = self.current_market_data.get(symbol)
                    if market_data:
                        # Get random signal
                        signal = self.random_strategies[symbol].generate_signal()
                        self.logger.info(f"[RandomStrategy] {symbol}: {signal}")
                        # (Optional) You can trigger trade logic here if needed
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

    def _print_account_and_positions(self):
        """Print account and open positions' unrealized PnL (no DB update)"""
        async def print_async():
            account = await self.broker.get_account_summary_async()
            positions = await self.broker.get_positions_summary_async()
            print("\n[Account Summary]")
            print(f"Balance: ${account.get('current_balance', 0):.2f} | Unrealized PnL: ${account.get('total_unrealized_pnl', 0):.2f}")
            print("[Open Positions]")
            for pos in positions.get('open_positions', []):
                print(f"{pos['symbol']} | Qty: {pos['quantity']} | Entry: {pos['entry_price']} | PnL: {pos['pnl']:.2f} | PnL%: {pos['pnl_percentage']:.2f}%")
        # Run async print in event loop
        asyncio.run_coroutine_threadsafe(print_async(), asyncio.get_event_loop())
    
    async def _execute_signal(self, signal: TradingSignal):
        """Execute a trading signal"""
        try:
            self.logger.info(f"📊 Processing signal: {signal.signal.value} {signal.symbol} "
                           f"from {signal.strategy_name} (confidence: {signal.confidence:.1f}%)")
            
            # Check if signal is actionable
            if signal.signal == SignalType.WAIT:
                return
            
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
                return
            
            # Execute trade
            success = await self.broker.execute_trade_async(trade_request)
            
            if success:
                self._stats["trades_executed"] += 1
                self._stats["trades_successful"] += 1
                
                self.logger.info(f"✅ Trade executed: {signal.signal.value} {signal.symbol} "
                               f"at ${signal.price:.2f} via {signal.strategy_name}")
                
                # Send notification
                await self.notification_manager.notify_trade_execution(
                    symbol=signal.symbol,
                    signal=signal.signal.value,
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
            
            # Update account summary based on current prices
            await self.broker.update_account_summary_async()
            
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
            
            self.logger.info("📊 System Summary:")
            self.logger.info(f"   Account Balance: ${account_summary.get('current_balance', 0):.2f}")
            self.logger.info(f"   Total Trades: {self._stats['trades_executed']}")
            self.logger.info(f"   Win Rate: {account_summary.get('win_rate', 0):.1f}%")
            self.logger.info(f"   Open Positions: {positions_summary.get('total_open', 0)}")
            self.logger.info(f"   Signals Generated: {self._stats['signals_generated']}")
            self.logger.info(f"   Price Updates: {self._stats['price_updates']}")
            self.logger.info(f"   Active Strategies: {len([s for strategies in strategy_stats.values() for s in strategies])}")
            
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
            "strategy_stats": self.strategy_manager.get_strategy_stats()
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