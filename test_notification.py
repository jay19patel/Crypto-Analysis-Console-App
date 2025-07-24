import asyncio
import logging
from src.services.notifications import NotificationManager

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_notifications():
    """Test all notification types with detailed logging"""
    print("=" * 60)
    print("STARTING NOTIFICATION SYSTEM TESTS")
    print("=" * 60)
    
    # Initialize manager
    manager = NotificationManager()
    await manager.start()
    
    # Test email connection first
    print("\n1. Testing Email Connection...")
    email_test = await manager.test_email_connection()
    print(f"Email Connection Test: {'✅' if email_test else '❌'}")
    
    if not email_test:
        print("⚠️  Warning: Email test failed. Check your email configuration.")
        print("   - Verify FASTAPI_MAIL_FROM is set correctly")
        print("   - Verify EMAIL_TO has valid recipients")
        print("   - Check SMTP settings in your config")
    
    # Wait a moment for the test email to process
    await asyncio.sleep(2)
    
    print("\n2. Testing Trade Execution Notification...")
    result1 = await manager.notify_trade_execution(
        symbol="BTC-USD",
        signal="BUY",
        price=50000.0,
        trade_id="T123456",
        position_id="P123456",
        pnl=150.0,
        user_id="test_user_001"
    )
    print(f"Trade Execution: {'✅' if result1 else '❌'}")
    await asyncio.sleep(1)
    
    print("\n3. Testing Position Close Notification...")
    result2 = await manager.notify_position_close(
        symbol="ETH-USD",
        position_id="P456789",
        exit_price=3500.0,
        pnl=-50.0,
        reason="Stop Loss Triggered",
        user_id="test_user_001"
    )
    print(f"Position Close: {'✅' if result2 else '❌'}")
    await asyncio.sleep(1)
    
    print("\n4. Testing Risk Alert Notification...")
    result3 = await manager.notify_risk_alert(
        symbol="ADA-USD",
        alert_type="High Volatility Detected",
        current_price=2.5,
        risk_level="High",
        user_id="test_user_001"
    )
    print(f"Risk Alert: {'✅' if result3 else '❌'}")
    await asyncio.sleep(1)
    
    print("\n5. Testing System Error Notification...")
    result4 = await manager.notify_system_error(
        error_message="API connection lost - attempting reconnection",
        component="Price Feed Service",
        user_id="system"
    )
    print(f"System Error: {'✅' if result4 else '❌'}")
    await asyncio.sleep(1)
    
    print("\n6. Testing Profit Alert Notification...")
    result5 = await manager.notify_profit_alert(
        symbol="SOL-USD",
        pnl=200.0,
        profit_percentage=12.5,
        user_id="test_user_001"
    )
    print(f"Profit Alert: {'✅' if result5 else '❌'}")
    await asyncio.sleep(1)
    
    print("\n7. Testing Margin Call Notification...")
    result6 = await manager.notify_margin_call(
        account_id="test_user_001",
        margin_usage=85.0
    )
    print(f"Margin Call: {'✅' if result6 else '❌'}")
    await asyncio.sleep(1)
    
    # Wait for all notifications to be processed
    print("\n8. Waiting for all notifications to be processed...")
    await asyncio.sleep(5)
    
    # Get statistics
    stats = manager.get_stats()
    print("\n" + "=" * 60)
    print("NOTIFICATION STATISTICS")
    print("=" * 60)
    print(f"Total Notifications: {stats['total_notifications']}")
    print(f"Emails Sent: {stats['emails_sent']}")
    print(f"Emails Failed: {stats['emails_failed']}")
    print(f"Queue Size: {stats['queue_size']}")
    print(f"Manager Running: {stats['running']}")
    
    if stats['last_notification']:
        print(f"Last Notification: {stats['last_notification']}")
    
    # Stop manager
    await manager.stop()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_results = [email_test, result1, result2, result3, result4, result5, result6]
    success_count = sum(all_results)
    total_tests = len(all_results)
    
    print(f"Tests Passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Notification system is working correctly.")
    elif success_count > 0:
        print("⚠️  Some tests passed. Check the logs above for details.")
    else:
        print("❌ All tests failed. Please check your configuration:")
        print("   1. Email settings in your .env file")
        print("   2. MongoDB connection")
        print("   3. Required packages are installed")
    
    print("\n📧 Check your email inbox for test notifications")
    print("🗄️  Check your MongoDB 'notifications' collection for logged entries")
    print("=" * 60)

async def test_database_only():
    """Test only database logging without email"""
    print("Testing database logging only...")
    
    manager = NotificationManager()
    await manager.start()
    
    # Temporarily disable email notifications for this test
    manager.email_notifier.settings.EMAIL_NOTIFICATIONS_ENABLED = False
    
    try:
        result = await manager.notify_trade_execution(
            symbol="TEST-DB",
            signal="BUY",
            price=100.0,
            trade_id="DB_TEST_001",
            position_id="DB_POS_001",
            pnl=0.0,
            user_id="db_test_user"
        )
        
        await asyncio.sleep(3)  # Wait for processing
        
        # Get statistics to see what happened
        stats = manager.get_stats()
        print(f"\nDatabase Test Statistics:")
        print(f"Total Notifications: {stats['total_notifications']}")
        print(f"Queue Size: {stats['queue_size']}")
        
        await manager.stop()
        print(f"Database-only test result: {'✅' if result else '❌'}")
        print("Check your MongoDB 'notifications' collection for the test entry")
        
        if not result:
            print("\n⚠️  Database test failed. Common issues:")
            print("   1. MongoDB connection not working")
            print("   2. Database credentials incorrect")
            print("   3. MongoDB service not running")
            print("   4. Collection permissions issue")
            
    except Exception as e:
        print(f"❌ Database test failed with exception: {e}")
        await manager.stop()

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Full test (email + database)")
    print("2. Database only test")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_database_only())
    else:
        asyncio.run(test_notifications())