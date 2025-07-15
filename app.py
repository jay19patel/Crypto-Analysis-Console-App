#!/usr/bin/env python3
"""
Simplified High-Speed Trading System - Complete Example
Demonstrates basic trading execution with async/await, dummy data, 
and essential functionality.

Usage:
    python run_high_speed_trading.py
    python run_high_speed_trading.py --delete  # Delete all data

Features:
    - Simplified async broker with dummy data
    - Basic risk management
    - Email notifications
    - Performance monitoring
    - MongoDB persistence
"""

import asyncio
import logging
import signal
import sys
import time
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List
import os

# Import simplified components
from broker.paper_broker import AsyncBroker, TradeRequest
from risk_manager import AsyncRiskManager
from src.notifications import NotificationManager
from src.config import get_settings, get_dummy_settings

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/high_speed_trading.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("high_speed_trading")


class SimplifiedTradingSystem:
    """Simplified trading system with dummy data and MongoDB persistence"""
    
    def __init__(self):
        """Initialize simplified trading system"""
        self.settings = get_settings()
        self.dummy_settings = get_dummy_settings()
        self.logger = logging.getLogger("trading_system")
        
        # Initialize components
        self.broker = AsyncBroker()
        self.risk_manager = AsyncRiskManager(self.broker)
        self.notification_manager = NotificationManager()
        
        # Control flags
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # Performance tracking
        self._start_time = time.time()
        self._trade_count = 0
        self._total_pnl = 0.0
        
        # Statistics
        self._stats = {
            "trades_executed": 0,
            "trades_successful": 0,
            "trades_failed": 0,
            "total_pnl": 0.0,
            "avg_execution_time": 0.0,
            "risk_alerts": 0,
            "notifications_sent": 0
        }
        
        # Dummy price data from config
        self._dummy_prices = {
            "BTC-USD": {"price": 50000.0, "volume": 1000.0, "change": 2.5},
            "ETH-USD": {"price": 3000.0, "volume": 500.0, "change": -1.2},
            "AAPL": {"price": 150.0, "volume": 2000.0, "change": 0.8},
            "GOOGL": {"price": 2800.0, "volume": 800.0, "change": 1.5},
            "TSLA": {"price": 800.0, "volume": 1200.0, "change": -0.5}
        }
        
        self.logger.info("Simplified trading system initialized")
    
    async def start(self) -> bool:
        """Start the simplified trading system"""
        try:
            self.logger.info("🚀 Starting Simplified Trading System")
            
            # Start all components
            if not await self.broker.start():
                self.logger.error("❌ Failed to start broker")
                return False
            
            if not await self.risk_manager.start():
                self.logger.error("❌ Failed to start risk manager")
                return False
            
            await self.notification_manager.start()
            
            # Send startup notification
            await self.notification_manager.notify_system_error(
                error_message="System started successfully",
                component="SimplifiedTradingSystem"
            )
            
            self._running = True
            self.logger.info("✅ Simplified trading system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start trading system: {e}")
            return False
    
    async def stop(self):
        """Stop the simplified trading system"""
        if not self._running:
            return
        
        self.logger.info("🛑 Stopping Simplified Trading System")
        self._running = False
        
        # Stop all components
        await self.broker.stop()
        await self.risk_manager.stop()
        await self.notification_manager.stop()
        
        # Send shutdown notification
        await self.notification_manager.notify_system_error(
            error_message="System shutdown completed",
            component="SimplifiedTradingSystem"
        )
        
        self.logger.info("✅ Simplified trading system stopped")
    
    async def delete_all_data(self) -> bool:
        """Delete all trading data"""
        try:
            self.logger.info("🗑️ Deleting all trading data...")
            
            # Delete data from broker (which handles MongoDB)
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
    
    async def run_trading_loop(self):
        """Main trading loop with simplified execution"""
        try:
            self.logger.info("🔄 Starting simplified trading loop")
            
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Update dummy prices
                    await self._update_dummy_prices()
                    
                    # Execute trading strategies
                    await self._execute_trading_strategies()
                    
                    # Monitor risk
                    await self._monitor_risk()
                    
                    # Update statistics
                    await self._update_statistics()
                    
                    # Sleep for next iteration
                    await asyncio.sleep(self.dummy_settings["trading_loop_interval"])
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(f"Error in trading loop: {e}")
                    await asyncio.sleep(5)
            
        except Exception as e:
            self.logger.error(f"Fatal error in trading loop: {e}")
    
    async def _update_dummy_prices(self):
        """Update dummy prices with small random changes"""
        import random
        
        for symbol in self._dummy_prices:
            current_price = self._dummy_prices[symbol]["price"]
            
            # Add small random change based on config
            change_percent = random.uniform(
                -self.dummy_settings["price_change_range"], 
                self.dummy_settings["price_change_range"]
            )
            new_price = current_price * (1 + change_percent)
            
            self._dummy_prices[symbol]["price"] = new_price
            self._dummy_prices[symbol]["change"] = change_percent * 100
        
        # Update broker prices
        await self.broker.update_prices_async(self._dummy_prices)
        
        self.logger.debug(f"📈 Updated dummy prices: {list(self._dummy_prices.keys())}")
    
    async def _execute_trading_strategies(self):
        """Execute trading strategies with dummy data"""
        try:
            import random
            
            # 10% chance to generate a trade signal
            if random.random() < 0.1:
                # Pick a random symbol from config
                symbol = random.choice(self.dummy_settings["symbols"])
                current_price = self._dummy_prices[symbol]["price"]
                
                # Generate signal
                signal = "BUY" if random.random() < 0.5 else "SELL"
                confidence = random.uniform(70, 95)
                
                # Create trade request
                trade_request = TradeRequest(
                    symbol=symbol,
                    signal=signal,
                    price=current_price,
                    quantity=0.01,  # Small position for demo
                    leverage=1.0,
                    strategy_name="Dummy Strategy",
                    confidence=confidence
                )
                
                # Execute trade
                await self._execute_trade(trade_request)
                
        except Exception as e:
            self.logger.error(f"Error executing trading strategies: {e}")
    
    async def _execute_trade(self, trade_request: TradeRequest):
        """Execute trade with simplified processing"""
        try:
            self.logger.info(f"🎯 Executing trade: {trade_request.signal} {trade_request.symbol} at ${trade_request.price:.2f}")
            
            # Check risk limits
            allowed, reason = await self.risk_manager.should_allow_new_position_async(
                trade_request.symbol, 
                trade_request.price * trade_request.quantity
            )
            
            if not allowed:
                self.logger.warning(f"❌ Trade rejected: {reason}")
                return
            
            # Execute trade
            success = await self.broker.execute_trade_async(trade_request)
            
            if success:
                self._trade_count += 1
                self._stats["trades_executed"] += 1
                self._stats["trades_successful"] += 1
                
                self.logger.info(f"✅ Trade executed successfully: {trade_request.signal} {trade_request.symbol}")
                
                # Send notification
                await self.notification_manager.notify_trade_execution(
                    symbol=trade_request.symbol,
                    signal=trade_request.signal,
                    price=trade_request.price,
                    trade_id=trade_request.id,
                    position_id=trade_request.position_id or "N/A"
                )
                
            else:
                self._stats["trades_failed"] += 1
                self.logger.error(f"❌ Trade execution failed: {trade_request.symbol}")
                
        except Exception as e:
            self.logger.error(f"Error executing trade: {e}")
            self._stats["trades_failed"] += 1
    
    async def _monitor_risk(self):
        """Monitor risk levels and take actions"""
        try:
            # Monitor positions
            actions_taken = await self.risk_manager.monitor_positions_async()
            
            if actions_taken:
                self.logger.info(f"🛡️ Risk actions taken: {actions_taken}")
                self._stats["risk_alerts"] += len(actions_taken)
            
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
            self.logger.error(f"Error monitoring risk: {e}")
    
    async def _update_statistics(self):
        """Update and log statistics"""
        try:
            # Get account summary
            account_summary = await self.broker.get_account_summary_async()
            
            # Get positions summary
            positions_summary = await self.broker.get_positions_summary_async()
            
            # Get performance stats
            broker_stats = self.broker.get_performance_stats()
            risk_stats = self.risk_manager.get_risk_summary()
            notification_stats = self.notification_manager.get_stats()
            
            # Update our stats
            self._stats["total_pnl"] = account_summary.get("total_profit", 0.0) - account_summary.get("total_loss", 0.0)
            
            # Log summary every 30 seconds
            if int(time.time()) % 30 == 0:
                self._log_system_summary(
                    account_summary, positions_summary, 
                    broker_stats, risk_stats, notification_stats
                )
                
        except Exception as e:
            self.logger.error(f"Error updating statistics: {e}")
    
    def _log_system_summary(self, account_summary: Dict, positions_summary: Dict,
                           broker_stats: Dict, risk_stats: Dict, notification_stats: Dict):
        """Log comprehensive system summary"""
        try:
            self.logger.info("📊 System Summary:")
            self.logger.info(f"   Account Balance: ${account_summary.get('current_balance', 0):.2f}")
            self.logger.info(f"   Total Trades: {account_summary.get('total_trades', 0)}")
            self.logger.info(f"   Win Rate: {account_summary.get('win_rate', 0):.1f}%")
            self.logger.info(f"   Open Positions: {positions_summary.get('total_open', 0)}")
            self.logger.info(f"   Unrealized P&L: ${positions_summary.get('total_unrealized_pnl', 0):.2f}")
            self.logger.info(f"   Risk Alerts: {self._stats['risk_alerts']}")
            self.logger.info(f"   Notifications Sent: {notification_stats.get('emails_sent', 0)}")
            self.logger.info(f"   MongoDB Connected: {broker_stats.get('mongodb_connected', False)}")
            
        except Exception as e:
            self.logger.error(f"Error logging system summary: {e}")
    
    async def demo_trading_scenarios(self):
        """Demonstrate various trading scenarios"""
        try:
            self.logger.info("🎭 Starting demo trading scenarios")
            
            # Scenario 1: Execute a BUY trade
            await self._demo_buy_trade()
            
            # Wait a bit
            await asyncio.sleep(3)
            
            # Scenario 2: Execute a SELL trade
            await self._demo_sell_trade()
            
            # Wait a bit
            await asyncio.sleep(3)
            
            # Scenario 3: Simulate price movement and risk management
            await self._demo_risk_management()
            
        except Exception as e:
            self.logger.error(f"Error in demo scenarios: {e}")
    
    async def _demo_buy_trade(self):
        """Demonstrate BUY trade execution"""
        try:
            self.logger.info("📈 Demo: Executing BUY trade")
            
            trade_request = TradeRequest(
                symbol="BTC-USD",
                signal="BUY",
                price=50000.0,
                quantity=0.001,  # Small position
                leverage=1.0,
                strategy_name="Demo Strategy",
                confidence=85.0
            )
            
            await self._execute_trade(trade_request)
            
        except Exception as e:
            self.logger.error(f"Error in demo BUY trade: {e}")
    
    async def _demo_sell_trade(self):
        """Demonstrate SELL trade execution"""
        try:
            self.logger.info("📉 Demo: Executing SELL trade")
            
            trade_request = TradeRequest(
                symbol="ETH-USD",
                signal="SELL",
                price=3000.0,
                quantity=0.01,  # Small position
                leverage=1.0,
                strategy_name="Demo Strategy",
                confidence=80.0
            )
            
            await self._execute_trade(trade_request)
            
        except Exception as e:
            self.logger.error(f"Error in demo SELL trade: {e}")
    
    async def _demo_risk_management(self):
        """Demonstrate risk management features"""
        try:
            self.logger.info("🛡️ Demo: Risk management features")
            
            # Get portfolio risk analysis
            portfolio_risk = await self.risk_manager.analyze_portfolio_risk_async()
            
            self.logger.info(f"Portfolio Risk Level: {portfolio_risk.get('overall_risk_level', 'unknown')}")
            self.logger.info(f"Portfolio Risk Percentage: {portfolio_risk.get('portfolio_risk_percentage', 0):.1f}%")
            
            # Get positions summary
            positions_summary = await self.broker.get_positions_summary_async()
            
            for position in positions_summary.get("open_positions", []):
                symbol = position.get("symbol", "Unknown")
                pnl = position.get("pnl", 0.0)
                self.logger.info(f"Position {symbol}: P&L ${pnl:.2f}")
                
                # Analyze individual position risk
                if symbol in self.broker._price_cache:
                    current_price = self.broker._price_cache[symbol].get("price", 0.0)
                    if current_price > 0:
                        # This would analyze the position risk
                        pass
            
        except Exception as e:
            self.logger.error(f"Error in demo risk management: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        uptime = time.time() - self._start_time
        
        return {
            **self._stats,
            "uptime_seconds": uptime,
            "trades_per_minute": (self._stats["trades_executed"] / (uptime / 60)) if uptime > 0 else 0,
            "system_running": self._running,
            "start_time": datetime.fromtimestamp(self._start_time, tz=timezone.utc).isoformat()
        }


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Simplified Trading System")
    parser.add_argument(
        "--delete", 
        action="store_true", 
        help="Delete all trading data from database"
    )
    return parser.parse_args()


async def main():
    """Main function to run the simplified trading system"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Create trading system
    trading_system = SimplifiedTradingSystem()
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        trading_system._shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Handle --delete flag
        if args.delete:
            logger.info("🗑️ Deleting all trading data...")
            await trading_system.delete_all_data()
            logger.info("✅ Data deletion completed")
            return
        
        # Start the system
        if not await trading_system.start():
            logger.error("Failed to start trading system")
            return
        
        # Run demo scenarios
        await trading_system.demo_trading_scenarios()
        
        # Run main trading loop
        await trading_system.run_trading_loop()
        
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
            logger.info(f"   {key}: {value}")


if __name__ == "__main__":
    # Run the simplified trading system
    asyncio.run(main()) 