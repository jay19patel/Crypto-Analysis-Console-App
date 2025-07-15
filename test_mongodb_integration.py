#!/usr/bin/env python3
"""
Test MongoDB Integration and Config Functionality
Tests the new async MongoDB client and config system
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Import components
from src.config import get_settings, get_broker_settings, get_risk_settings, get_dummy_settings
from src.mongodb_client import AsyncMongoDBClient
from src.async_broker import AsyncBroker
from src.async_risk_manager import AsyncRiskManager
from src.broker.models import Account, Position, PositionType, PositionStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_mongodb")


async def test_config_system():
    """Test the new config system"""
    logger.info("🧪 Testing Config System")
    
    try:
        # Test settings
        settings = get_settings()
        logger.info(f"✅ MongoDB URI: {settings.MONGODB_URI}")
        logger.info(f"✅ Database Name: {settings.DATABASE_NAME}")
        logger.info(f"✅ Initial Balance: ${settings.BROKER_INITIAL_BALANCE}")
        logger.info(f"✅ Max Leverage: {settings.BROKER_MAX_LEVERAGE}")
        logger.info(f"✅ Trading Fee: {settings.BROKER_TRADING_FEE_PCT * 100}%")
        
        # Test broker settings
        broker_settings = get_broker_settings()
        logger.info(f"✅ Broker Settings: {broker_settings}")
        
        # Test risk settings
        risk_settings = get_risk_settings()
        logger.info(f"✅ Risk Settings: {risk_settings}")
        
        # Test dummy settings
        dummy_settings = get_dummy_settings()
        logger.info(f"✅ Dummy Settings: {dummy_settings}")
        
        logger.info("✅ Config system test passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Config system test failed: {e}")
        return False


async def test_mongodb_connection():
    """Test MongoDB connection"""
    logger.info("🧪 Testing MongoDB Connection")
    
    try:
        # Reset singleton instance
        AsyncMongoDBClient.reset_instance()
        mongodb_client = AsyncMongoDBClient()
        
        # Test connection
        connected = await mongodb_client.connect()
        if not connected:
            logger.error("❌ Failed to connect to MongoDB")
            return False
        
        # Test connection test
        test_result = await mongodb_client.test_connection()
        if not test_result:
            logger.error("❌ MongoDB connection test failed")
            return False
        
        logger.info("✅ MongoDB connection test passed")
        
        # Disconnect
        await mongodb_client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB connection test failed: {e}")
        return False


async def test_account_operations():
    """Test account operations with MongoDB"""
    logger.info("🧪 Testing Account Operations")
    
    try:
        # Reset singleton instance
        AsyncMongoDBClient.reset_instance()
        mongodb_client = AsyncMongoDBClient()
        await mongodb_client.connect()
        
        # Create test account
        test_account = Account()
        test_account.id = "test_account"
        test_account.name = "Test Account"
        test_account.initial_balance = 5000.0
        test_account.current_balance = 5000.0
        test_account.total_trades = 10
        test_account.profitable_trades = 7
        test_account.losing_trades = 3
        test_account.win_rate = 70.0
        test_account.total_profit = 500.0
        test_account.total_loss = 200.0
        
        # Save account
        saved = await mongodb_client.save_account(test_account.to_dict())
        if not saved:
            logger.error("❌ Failed to save account")
            return False
        
        # Load account
        loaded_data = await mongodb_client.load_account("test_account")
        if not loaded_data:
            logger.error("❌ Failed to load account")
            return False
        
        # Verify data
        loaded_account = Account.from_dict(loaded_data)
        if loaded_account.id != test_account.id:
            logger.error("❌ Account ID mismatch")
            return False
        
        logger.info(f"✅ Account operations test passed - Balance: ${loaded_account.current_balance}")
        
        # Clean up
        await mongodb_client.delete_document("accounts", {"id": "test_account"})
        await mongodb_client.disconnect()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Account operations test failed: {e}")
        return False


async def test_position_operations():
    """Test position operations with MongoDB"""
    logger.info("🧪 Testing Position Operations")
    
    try:
        # Reset singleton instance
        AsyncMongoDBClient.reset_instance()
        mongodb_client = AsyncMongoDBClient()
        await mongodb_client.connect()
        
        # Create test position
        test_position = Position()
        test_position.symbol = "BTC-USD"
        test_position.position_type = PositionType.LONG
        test_position.entry_price = 50000.0
        test_position.quantity = 0.1
        test_position.invested_amount = 5000.0
        test_position.strategy_name = "Test Strategy"
        test_position.leverage = 1.0
        test_position.margin_used = 5000.0
        test_position.trading_fee = 5.0
        test_position.stop_loss = 47500.0
        test_position.target = 55000.0
        
        # Calculate PnL
        test_position.calculate_pnl(52000.0)
        
        # Save position
        saved = await mongodb_client.save_position(test_position.to_dict())
        if not saved:
            logger.error("❌ Failed to save position")
            return False
        
        # Load positions
        positions = await mongodb_client.load_positions()
        if not positions:
            logger.error("❌ Failed to load positions")
            return False
        
        # Find our test position
        test_pos_data = None
        for pos_data in positions:
            if pos_data.get("symbol") == "BTC-USD":
                test_pos_data = pos_data
                break
        
        if not test_pos_data:
            logger.error("❌ Test position not found")
            return False
        
        # Verify data
        loaded_position = Position.from_dict(test_pos_data)
        if loaded_position.symbol != test_position.symbol:
            logger.error("❌ Position symbol mismatch")
            return False
        
        logger.info(f"✅ Position operations test passed - P&L: ${loaded_position.pnl:.2f}")
        
        # Clean up
        await mongodb_client.delete_document("positions", {"id": test_position.id})
        await mongodb_client.disconnect()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Position operations test failed: {e}")
        return False


async def test_broker_integration():
    """Test broker integration with MongoDB"""
    logger.info("🧪 Testing Broker Integration")
    
    try:
        # Reset singleton instance
        AsyncMongoDBClient.reset_instance()
        
        # Create broker
        broker = AsyncBroker()
        
        # Start broker
        started = await broker.start()
        if not started:
            logger.error("❌ Failed to start broker")
            return False
        
        # Check if account was created/loaded
        if not broker.account:
            logger.error("❌ No account available")
            return False
        
        logger.info(f"✅ Broker account loaded - Balance: ${broker.account.current_balance}")
        
        # Test trade execution
        from src.async_broker import TradeRequest
        
        trade_request = TradeRequest(
            symbol="BTC-USD",
            signal="BUY",
            price=50000.0,
            quantity=0.001,
            leverage=1.0,
            strategy_name="Test Strategy",
            confidence=85.0
        )
        
        # Execute trade
        success = await broker.execute_trade_async(trade_request)
        if not success:
            logger.error("❌ Trade execution failed")
            return False
        
        logger.info("✅ Trade executed successfully")
        
        # Check positions
        positions_summary = await broker.get_positions_summary_async()
        logger.info(f"✅ Positions summary - Open: {positions_summary.get('total_open', 0)}")
        
        # Stop broker
        await broker.stop()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Broker integration test failed: {e}")
        return False


async def test_risk_manager_integration():
    """Test risk manager integration"""
    logger.info("🧪 Testing Risk Manager Integration")
    
    try:
        # Reset singleton instance
        AsyncMongoDBClient.reset_instance()
        
        # Create broker and risk manager
        broker = AsyncBroker()
        risk_manager = AsyncRiskManager(broker)
        
        # Start components
        await broker.start()
        await risk_manager.start()
        
        # Test portfolio risk analysis
        portfolio_risk = await risk_manager.analyze_portfolio_risk_async()
        logger.info(f"✅ Portfolio risk analysis: {portfolio_risk.get('overall_risk_level', 'unknown')}")
        
        # Test position risk analysis
        if broker.positions:
            for position in list(broker.positions.values())[:1]:  # Test first position
                if position.symbol in broker._price_cache:
                    current_price = broker._price_cache[position.symbol].get("price", 0.0)
                    if current_price > 0:
                        risk_metrics = await risk_manager.analyze_position_risk_async(position, current_price)
                        logger.info(f"✅ Position risk analysis: {risk_metrics.risk_level.value}")
        
        # Stop components
        await risk_manager.stop()
        await broker.stop()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Risk manager integration test failed: {e}")
        return False


async def test_data_deletion():
    """Test data deletion functionality"""
    logger.info("🧪 Testing Data Deletion")
    
    try:
        # Reset singleton instance
        AsyncMongoDBClient.reset_instance()
        mongodb_client = AsyncMongoDBClient()
        await mongodb_client.connect()
        
        # Create some test data
        test_account = Account()
        test_account.id = "delete_test"
        test_account.name = "Delete Test Account"
        test_account.initial_balance = 1000.0
        test_account.current_balance = 1000.0
        
        await mongodb_client.save_account(test_account.to_dict())
        
        test_position = Position()
        test_position.symbol = "DELETE-TEST"
        test_position.position_type = PositionType.LONG
        test_position.entry_price = 100.0
        test_position.quantity = 1.0
        test_position.invested_amount = 100.0
        
        await mongodb_client.save_position(test_position.to_dict())
        
        # Test deletion
        deleted = await mongodb_client.delete_all_data()
        if not deleted:
            logger.error("❌ Failed to delete all data")
            return False
        
        # Verify deletion
        accounts = await mongodb_client.load_account("delete_test")
        positions = await mongodb_client.load_positions()
        
        if accounts or positions:
            logger.error("❌ Data not properly deleted")
            return False
        
        logger.info("✅ Data deletion test passed")
        
        await mongodb_client.disconnect()
        return True
        
    except Exception as e:
        logger.error(f"❌ Data deletion test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    logger.info("🚀 Starting MongoDB Integration Tests")
    
    tests = [
        ("Config System", test_config_system),
        ("MongoDB Connection", test_mongodb_connection),
        ("Account Operations", test_account_operations),
        ("Position Operations", test_position_operations),
        ("Broker Integration", test_broker_integration),
        ("Risk Manager Integration", test_risk_manager_integration),
        ("Data Deletion", test_data_deletion)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = await test_func()
            if result:
                passed += 1
                logger.info(f"✅ {test_name}: PASSED")
            else:
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"Test Results: {passed}/{total} tests passed")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 All tests passed! MongoDB integration is working correctly.")
    else:
        logger.error(f"❌ {total - passed} tests failed. Please check the configuration.")
    
    return passed == total


if __name__ == "__main__":
    # Run all tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1) 