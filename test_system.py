#!/usr/bin/env python3
"""
Test Simplified Trading System
Demonstrates the simplified async broker and risk manager functionality
"""

import asyncio
import logging
from datetime import datetime, timezone

from src.broker.paper_broker import AsyncBroker, TradeRequest
from src.risk_manager import AsyncRiskManager
from src.notifications import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)

logger = logging.getLogger("test_system")


async def test_broker_functionality():
    """Test broker functionality"""
    logger.info("🧪 Testing Broker Functionality")
    
    # Initialize broker
    broker = AsyncBroker()
    await broker.start()
    
    # Test account summary
    account_summary = await broker.get_account_summary_async()
    logger.info(f"Account Balance: ${account_summary.get('current_balance', 0):.2f}")
    
    # Test trade execution
    trade_request = TradeRequest(
        symbol="BTC-USD",
        signal="BUY",
        price=50000.0,
        quantity=0.001,
        leverage=1.0,
        strategy_name="Test Strategy",
        confidence=85.0
    )
    
    success = await broker.execute_trade_async(trade_request)
    logger.info(f"Trade execution: {'✅ Success' if success else '❌ Failed'}")
    
    # Test positions summary
    positions_summary = await broker.get_positions_summary_async()
    logger.info(f"Open positions: {positions_summary.get('total_open', 0)}")
    
    # Test price updates
    dummy_prices = {
        "BTC-USD": {"price": 51000.0, "volume": 1000.0, "change": 2.0},
        "ETH-USD": {"price": 3000.0, "volume": 500.0, "change": -1.0}
    }
    await broker.update_prices_async(dummy_prices)
    
    # Get updated positions
    updated_positions = await broker.get_positions_summary_async()
    for position in updated_positions.get("open_positions", []):
        pnl = position.get("pnl", 0.0)
        logger.info(f"Position {position.get('symbol')}: P&L ${pnl:.2f}")
    
    await broker.stop()
    logger.info("✅ Broker test completed")


async def test_risk_manager_functionality():
    """Test risk manager functionality"""
    logger.info("🛡️ Testing Risk Manager Functionality")
    
    # Initialize broker and risk manager
    broker = AsyncBroker()
    risk_manager = AsyncRiskManager(broker)
    
    await broker.start()
    await risk_manager.start()
    
    # Create some test positions
    test_trades = [
        TradeRequest("BTC-USD", "BUY", 50000.0, 0.001, 1.0, "Test", 85.0),
        TradeRequest("ETH-USD", "SELL", 3000.0, 0.01, 1.0, "Test", 80.0)
    ]
    
    for trade in test_trades:
        await broker.execute_trade_async(trade)
    
    # Update prices to simulate market movement
    prices = {
        "BTC-USD": {"price": 48000.0, "volume": 1000.0, "change": -4.0},  # Loss
        "ETH-USD": {"price": 2800.0, "volume": 500.0, "change": -6.7}     # Profit for short
    }
    await broker.update_prices_async(prices)
    
    # Test portfolio risk analysis
    portfolio_risk = await risk_manager.analyze_portfolio_risk_async()
    logger.info(f"Portfolio Risk Level: {portfolio_risk.get('overall_risk_level', 'unknown')}")
    logger.info(f"Portfolio Risk Percentage: {portfolio_risk.get('portfolio_risk_percentage', 0):.1f}%")
    
    # Test position monitoring
    actions_taken = await risk_manager.monitor_positions_async()
    logger.info(f"Risk actions taken: {actions_taken}")
    
    # Test new position approval
    allowed, reason = await risk_manager.should_allow_new_position_async("AAPL", 1000.0)
    logger.info(f"New position allowed: {'✅ Yes' if allowed else '❌ No'} - {reason}")
    
    await risk_manager.stop()
    await broker.stop()
    logger.info("✅ Risk manager test completed")


async def test_notification_system():
    """Test notification system"""
    logger.info("📧 Testing Notification System")
    
    notification_manager = NotificationManager()
    await notification_manager.start()
    
    # Test different notification types
    await notification_manager.notify_trade_execution(
        symbol="BTC-USD",
        signal="BUY",
        price=50000.0,
        trade_id="test-123",
        position_id="pos-456"
    )
    
    await notification_manager.notify_risk_alert(
        symbol="BTC-USD",
        alert_type="High Risk",
        current_price=48000.0,
        risk_level="high"
    )
    
    await notification_manager.notify_profit_alert(
        symbol="ETH-USD",
        pnl=500.0,
        profit_percentage=15.0
    )
    
    stats = notification_manager.get_stats()
    logger.info(f"Notifications sent: {stats.get('emails_sent', 0)}")
    
    await notification_manager.stop()
    logger.info("✅ Notification test completed")


async def main():
    """Main test function"""
    logger.info("🚀 Starting Simplified Trading System Tests")
    
    try:
        # Test broker functionality
        await test_broker_functionality()
        
        # Test risk manager functionality
        await test_risk_manager_functionality()
        
        # Test notification system
        await test_notification_system()
        
        logger.info("✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 