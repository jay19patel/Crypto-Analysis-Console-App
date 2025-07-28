#!/usr/bin/env python3
"""
Comprehensive Trading System Test Suite
Tests all notification types, trading operations, and system functionality
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid

# Setup path for imports
sys.path.append('.')

from src.core.trading_system import TradingSystem
from src.services.notifications import NotificationManager, NotificationEvent, NotificationType, NotificationPriority
from src.services.risk_manager import AsyncRiskManager
from src.broker.paper_broker import AsyncBroker, TradeRequest
from src.broker.models import Position, PositionType, PositionStatus
from src.core.email_formatter import TradeExecutionData, PositionExitData
from src.config import get_settings, get_trading_config


class TradingSystemTester:
    """Comprehensive trading system tester"""
    
    def __init__(self):
        """Initialize the test system"""
        self.settings = get_settings()
        self.trading_config = get_trading_config() 
        self.logger = logging.getLogger("test_system")
        
        # Initialize components
        self.notification_manager = NotificationManager(email_enabled=True)
        self.broker = AsyncBroker()
        self.risk_manager = AsyncRiskManager()
        
        # Test results tracking
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": []
        }
        
        # Test data
        self.test_symbols = ["BTCUSD", "ETHUSD", "ADAUSD"]
        self.test_prices = {"BTCUSD": 67500.0, "ETHUSD": 2650.0, "ADAUSD": 0.45}
        
        print("🧪 Trading System Tester Initialized")
        print("=" * 60)
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Comprehensive Trading System Tests")
        print("=" * 60)
        
        try:
            # Initialize system components
            await self._initialize_components()
            
            # Test 1: System Startup Notification
            await self._test_system_startup()
            
            # Test 2: Trade Execution Notifications
            await self._test_trade_execution()
            
            # Test 3: Position Exit Notifications (Target Hit)
            await self._test_target_hit()
            
            # Test 4: Position Exit Notifications (Stop Loss Hit)
            await self._test_stop_loss_hit()
            
            # Test 5: Risk Alert Notifications
            await self._test_risk_alerts()
            
            # Test 6: System Error Notifications
            await self._test_system_errors()
            
            # Test 7: Multiple Position Management
            await self._test_multiple_positions()
            
            # Test 8: Position Liquidation (High Risk Exit)
            await self._test_liquidation_exit()
            
            # Test 9: Email Deduplication
            await self._test_email_deduplication()
            
            # Test 10: System Shutdown Notification
            await self._test_system_shutdown()
            
            # Show final results
            await self._show_test_results()
            
        except Exception as e:
            self.logger.error(f"Test suite failed with error: {e}")
            print(f"❌ Test suite failed: {e}")
        
        finally:
            # Cleanup
            await self._cleanup_components()
    
    async def _initialize_components(self):
        """Initialize all system components"""
        print("\n🔧 Initializing System Components...")
        
        try:
            # Start notification manager
            await self.notification_manager.start()
            print("✅ Notification Manager started")
            
            # Start broker
            await self.broker.start()
            print("✅ Paper Broker started")
            
            # Initialize risk manager
            await self.risk_manager.start()
            print("✅ Risk Manager started")
            
            print("✅ All components initialized successfully\n")
            
        except Exception as e:
            print(f"❌ Component initialization failed: {e}")
            raise
    
    async def _test_system_startup(self):
        """Test system startup notification"""
        print("📧 Test 1: System Startup Notification...")
        
        try:
            # Get account and position summaries
            account_summary = await self.broker.get_account_summary_async()
            positions_summary = await self.broker.get_positions_summary_async()
            
            # Send startup notification
            result = await self.notification_manager.notify_system_startup(
                system_config={
                    "strategy_execution_interval": "600s (10 minutes)",
                    "historical_data_update": "900s (15 minutes)",
                    "live_price_updates": "realtime",
                    "risk_check_interval": "60s"
                },
                trading_params={
                    "initial_balance": f"${self.trading_config['initial_balance']:,.2f}",
                    "balance_per_trade": f"{self.trading_config['balance_per_trade_pct']*100:.0f}%",
                    "default_leverage": f"{self.trading_config['default_leverage']:.0f}x",
                    "stop_loss": f"{self.trading_config['stop_loss_pct']*100:.1f}%",
                    "target_profit": f"{self.trading_config['target_pct']*100:.1f}%",
                    "min_confidence": f"{self.trading_config['min_confidence']:.1f}%",
                    "daily_trade_limit": str(self.trading_config['daily_trades_limit'])
                },
                active_strategies=self.settings.STRATEGY_CLASSES,
                trading_symbols=self.settings.TRADING_SYMBOLS,
                system_status={
                    "websocket_port": str(self.settings.WEBSOCKET_PORT),
                    "email_notifications": "Enabled" if self.settings.EMAIL_NOTIFICATIONS_ENABLED else "Disabled",
                    "log_level": self.settings.LOG_LEVEL
                },
                account_summary=account_summary,
                positions_summary=positions_summary
            )
            
            await self._record_test_result("System Startup Notification", result, 
                                         "System startup email sent successfully")
            
        except Exception as e:
            await self._record_test_result("System Startup Notification", False, str(e))
    
    async def _test_trade_execution(self):
        """Test trade execution notifications"""
        print("💰 Test 2: Trade Execution Notifications...")
        
        test_cases = [
            {"symbol": "BTCUSD", "signal": "BUY", "price": 67500.0, "leverage": 1.0},
            {"symbol": "ETHUSD", "signal": "BUY", "price": 2650.0, "leverage": 2.0},
            {"symbol": "ADAUSD", "signal": "SELL", "price": 0.45, "leverage": 1.5}
        ]
        
        for i, case in enumerate(test_cases):
            try:
                print(f"  🔸 Test 2.{i+1}: {case['signal']} {case['symbol']} at ${case['price']}")
                
                # Calculate trade details
                quantity = await self._calculate_safe_quantity(case['symbol'], case['price'], case['leverage'])
                position_value = case['price'] * quantity
                margin_used = position_value / case['leverage']
                trading_fee = margin_used * self.trading_config["trading_fee_pct"]
                
                # Get account balances
                account_before = self.broker.account.current_balance
                account_after = account_before - margin_used - trading_fee
                
                # Create trade execution data
                trade_data = TradeExecutionData(
                    symbol=case['symbol'],
                    signal=case['signal'],
                    price=case['price'],
                    quantity=quantity,
                    leverage=case['leverage'],
                    margin_used=margin_used,
                    capital_remaining=account_after,
                    investment_amount=position_value,
                    leveraged_amount=position_value * case['leverage'],
                    trade_id=str(uuid.uuid4()),
                    position_id=str(uuid.uuid4()),
                    strategy_name="EMAStrategy",
                    confidence=85.5,
                    trading_fee=trading_fee,
                    timestamp=datetime.now(timezone.utc),
                    account_balance_before=account_before,
                    account_balance_after=account_after
                )
                
                # Send trade execution notification
                result = await self.notification_manager.notify_trade_execution(
                    symbol=case['symbol'],
                    signal=case['signal'],
                    price=case['price'],
                    trade_id=trade_data.trade_id,
                    position_id=trade_data.position_id,
                    quantity=quantity,
                    leverage=case['leverage'],
                    margin_used=margin_used,
                    capital_remaining=account_after,
                    investment_amount=position_value,
                    leveraged_amount=position_value * case['leverage'],
                    trading_fee=trading_fee,
                    strategy_name="EMAStrategy",
                    confidence=85.5,
                    account_balance_before=account_before,
                    account_balance_after=account_after
                )
                
                await self._record_test_result(f"Trade Execution {case['symbol']}", result,
                                             f"{case['signal']} {case['symbol']} notification sent")
                
                # Wait between tests
                await asyncio.sleep(1)
                
            except Exception as e:
                await self._record_test_result(f"Trade Execution {case['symbol']}", False, str(e))
    
    async def _test_target_hit(self):
        """Test target hit (profit) notifications"""
        print("🎯 Test 3: Target Hit Notifications...")
        
        test_cases = [
            {
                "symbol": "BTCUSD", "position_type": "LONG", "entry_price": 67000.0, 
                "exit_price": 73700.0, "quantity": 0.1, "leverage": 1.0, "pnl": 670.0
            },
            {
                "symbol": "ETHUSD", "position_type": "LONG", "entry_price": 2600.0,
                "exit_price": 2860.0, "quantity": 2.0, "leverage": 2.0, "pnl": 520.0
            }
        ]
        
        for i, case in enumerate(test_cases):
            try:
                print(f"  🔸 Test 3.{i+1}: {case['symbol']} Target Hit - P&L: ${case['pnl']}")
                
                # Calculate position details
                position_value = case['entry_price'] * case['quantity']
                margin_used = position_value / case['leverage']
                trading_fee = margin_used * self.trading_config["trading_fee_pct"]
                exit_fee = trading_fee * self.trading_config["exit_fee_multiplier"]
                total_fees = trading_fee + exit_fee
                
                # Calculate durations and growth
                account_before = self.broker.account.current_balance
                account_after = account_before + case['pnl']
                account_growth = case['pnl']
                account_growth_pct = (account_growth / account_before) * 100 if account_before > 0 else 0
                
                # Create position exit data
                exit_data = PositionExitData(
                    symbol=case['symbol'],
                    position_type=case['position_type'],
                    entry_price=case['entry_price'],
                    exit_price=case['exit_price'],
                    quantity=case['quantity'],
                    leverage=case['leverage'],
                    pnl=case['pnl'],
                    pnl_percentage=(case['pnl'] / margin_used) * 100,
                    investment_amount=position_value,
                    leveraged_amount=position_value * case['leverage'],
                    margin_used=margin_used,
                    trading_fee=trading_fee,
                    exit_fee=exit_fee,
                    total_fees=total_fees,
                    position_id=str(uuid.uuid4()),
                    trade_duration="2h 15m",
                    exit_reason="Target Hit - 10% Profit Achieved",
                    account_balance_before=account_before,
                    account_balance_after=account_after,
                    account_growth=account_growth,
                    account_growth_percentage=account_growth_pct,
                    total_portfolio_pnl=case['pnl'],
                    win_rate=75.5,
                    timestamp=datetime.now(timezone.utc)
                )
                
                # Send position close notification
                result = await self.notification_manager.notify_position_close(
                    symbol=case['symbol'],
                    position_id=exit_data.position_id,
                    exit_price=case['exit_price'],
                    pnl=case['pnl'],
                    reason="Target Hit - 10% Profit Achieved",
                    position_type=case['position_type'],
                    entry_price=case['entry_price'],
                    quantity=case['quantity'],
                    leverage=case['leverage'],
                    pnl_percentage=exit_data.pnl_percentage,
                    investment_amount=position_value,
                    leveraged_amount=position_value * case['leverage'],
                    margin_used=margin_used,
                    trading_fee=trading_fee,
                    exit_fee=exit_fee,
                    total_fees=total_fees,
                    trade_duration="2h 15m",
                    account_balance_before=account_before,
                    account_balance_after=account_after,
                    account_growth=account_growth,
                    account_growth_percentage=account_growth_pct,
                    total_portfolio_pnl=case['pnl'],
                    win_rate=75.5
                )
                
                await self._record_test_result(f"Target Hit {case['symbol']}", result,
                                             f"Profit exit notification sent: ${case['pnl']}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                await self._record_test_result(f"Target Hit {case['symbol']}", False, str(e))
    
    async def _test_stop_loss_hit(self):
        """Test stop loss hit (loss) notifications"""
        print("🛑 Test 4: Stop Loss Hit Notifications...")
        
        test_cases = [
            {
                "symbol": "BTCUSD", "position_type": "LONG", "entry_price": 67000.0,
                "exit_price": 63650.0, "quantity": 0.1, "leverage": 1.0, "pnl": -335.0
            },
            {
                "symbol": "ETHUSD", "position_type": "SHORT", "entry_price": 2600.0,
                "exit_price": 2730.0, "quantity": 1.5, "leverage": 1.5, "pnl": -195.0
            }
        ]
        
        for i, case in enumerate(test_cases):
            try:
                print(f"  🔸 Test 4.{i+1}: {case['symbol']} Stop Loss Hit - P&L: ${case['pnl']}")
                
                # Calculate position details
                position_value = case['entry_price'] * case['quantity']
                margin_used = position_value / case['leverage']
                trading_fee = margin_used * self.trading_config["trading_fee_pct"]
                exit_fee = trading_fee * self.trading_config["exit_fee_multiplier"]
                total_fees = trading_fee + exit_fee
                
                # Calculate account impact
                account_before = self.broker.account.current_balance
                account_after = account_before + case['pnl']  # pnl is negative
                account_growth = case['pnl']
                account_growth_pct = (account_growth / account_before) * 100 if account_before > 0 else 0
                
                # Send position close notification
                result = await self.notification_manager.notify_position_close(
                    symbol=case['symbol'],
                    position_id=str(uuid.uuid4()),
                    exit_price=case['exit_price'],
                    pnl=case['pnl'],
                    reason="Stop Loss Hit - 5% Loss Protection",
                    position_type=case['position_type'],
                    entry_price=case['entry_price'],
                    quantity=case['quantity'],
                    leverage=case['leverage'],
                    pnl_percentage=(case['pnl'] / margin_used) * 100,
                    investment_amount=position_value,
                    leveraged_amount=position_value * case['leverage'],
                    margin_used=margin_used,
                    trading_fee=trading_fee,
                    exit_fee=exit_fee,
                    total_fees=total_fees,
                    trade_duration="45m",
                    account_balance_before=account_before,
                    account_balance_after=account_after,
                    account_growth=account_growth,
                    account_growth_percentage=account_growth_pct,
                    total_portfolio_pnl=case['pnl'],
                    win_rate=73.2
                )
                
                await self._record_test_result(f"Stop Loss {case['symbol']}", result,
                                             f"Stop loss notification sent: ${case['pnl']}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                await self._record_test_result(f"Stop Loss {case['symbol']}", False, str(e))
    
    async def _test_risk_alerts(self):
        """Test risk alert notifications"""
        print("⚠️ Test 5: Risk Alert Notifications...")
        
        risk_scenarios = [
            {
                "symbol": "BTCUSD", "alert_type": "High Portfolio Risk", 
                "current_price": 65000.0, "risk_level": "HIGH"
            },
            {
                "symbol": "PORTFOLIO", "alert_type": "Margin Call Warning",
                "current_price": 0.0, "risk_level": "CRITICAL"
            },
            {
                "symbol": "ETHUSD", "alert_type": "Position Size Limit",
                "current_price": 2500.0, "risk_level": "MEDIUM"
            }
        ]
        
        for i, scenario in enumerate(risk_scenarios):
            try:
                print(f"  🔸 Test 5.{i+1}: {scenario['alert_type']} - {scenario['risk_level']}")
                
                result = await self.notification_manager.notify_risk_alert(
                    symbol=scenario['symbol'],
                    alert_type=scenario['alert_type'],
                    current_price=scenario['current_price'],
                    risk_level=scenario['risk_level']
                )
                
                await self._record_test_result(f"Risk Alert {scenario['alert_type']}", result,
                                             f"{scenario['risk_level']} risk alert sent")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                await self._record_test_result(f"Risk Alert {scenario['alert_type']}", False, str(e))
    
    async def _test_system_errors(self):
        """Test system error notifications"""
        print("❌ Test 6: System Error Notifications...")
        
        error_scenarios = [
            {"component": "WebSocket Server", "error": "Connection timeout after 30 seconds"},
            {"component": "Risk Manager", "error": "Portfolio risk calculation failed"},
            {"component": "Database", "error": "MongoDB connection lost - reconnecting"}
        ]
        
        for i, scenario in enumerate(error_scenarios):
            try:
                print(f"  🔸 Test 6.{i+1}: {scenario['component']} Error")
                
                result = await self.notification_manager.notify_system_error(
                    error_message=scenario['error'],
                    component=scenario['component']
                )
                
                await self._record_test_result(f"System Error {scenario['component']}", result,
                                             f"Error notification sent for {scenario['component']}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                await self._record_test_result(f"System Error {scenario['component']}", False, str(e))
    
    async def _test_multiple_positions(self):
        """Test multiple position management"""
        print("📊 Test 7: Multiple Position Management...")
        
        try:
            # Create multiple positions simultaneously
            positions = []
            for symbol in ["BTCUSD", "ETHUSD", "ADAUSD"]:
                trade_id = str(uuid.uuid4())
                position_id = str(uuid.uuid4())
                
                result = await self.notification_manager.notify_trade_execution(
                    symbol=symbol,
                    signal="BUY",
                    price=self.test_prices[symbol],
                    trade_id=trade_id,
                    position_id=position_id,
                    quantity=0.1,
                    leverage=1.0,
                    margin_used=self.test_prices[symbol] * 0.1,
                    capital_remaining=8500.0,
                    investment_amount=self.test_prices[symbol] * 0.1,
                    leveraged_amount=self.test_prices[symbol] * 0.1,
                    trading_fee=self.test_prices[symbol] * 0.1 * 0.001,
                    strategy_name="MultiStrategy",
                    confidence=80.0,
                    account_balance_before=10000.0,
                    account_balance_after=9500.0
                )
                
                positions.append({"symbol": symbol, "success": result})
            
            all_success = all(pos["success"] for pos in positions)
            await self._record_test_result("Multiple Positions", all_success,
                                         f"Created {len(positions)} positions simultaneously")
            
        except Exception as e:
            await self._record_test_result("Multiple Positions", False, str(e))
    
    async def _test_liquidation_exit(self):
        """Test liquidation (high risk) exit notifications"""
        print("💥 Test 8: Liquidation Exit Notifications...")
        
        try:
            print("  🔸 Test 8.1: High Risk Liquidation - BTCUSD")
            
            # Simulate high-risk liquidation scenario
            result = await self.notification_manager.notify_position_close(
                symbol="BTCUSD",
                position_id=str(uuid.uuid4()),
                exit_price=62000.0,  # Significant loss
                pnl=-850.0,  # Large loss
                reason="Liquidation - High Risk Portfolio Protection",
                position_type="LONG",
                entry_price=67000.0,
                quantity=0.2,
                leverage=3.0,  # High leverage
                pnl_percentage=-25.5,  # High percentage loss
                investment_amount=13400.0,
                leveraged_amount=40200.0,
                margin_used=4466.67,
                trading_fee=4.47,
                exit_fee=2.23,
                total_fees=6.70,
                trade_duration="15m",
                account_balance_before=10000.0,
                account_balance_after=9150.0,
                account_growth=-850.0,
                account_growth_percentage=-8.5,
                total_portfolio_pnl=-850.0,
                win_rate=68.5
            )
            
            await self._record_test_result("Liquidation Exit", result,
                                         "High-risk liquidation notification sent")
            
        except Exception as e:
            await self._record_test_result("Liquidation Exit", False, str(e))
    
    async def _test_email_deduplication(self):
        """Test email deduplication system"""
        print("🔒 Test 9: Email Deduplication...")
        
        try:
            trade_id = str(uuid.uuid4())
            
            # Send same notification twice quickly
            print("  🔸 Test 9.1: Sending duplicate trade execution notifications...")
            
            notification_data = {
                "symbol": "BTCUSD",
                "signal": "BUY",
                "price": 67500.0,
                "trade_id": trade_id,  # Same trade_id
                "position_id": str(uuid.uuid4()),
                "quantity": 0.1,
                "leverage": 1.0,
                "margin_used": 6750.0,
                "capital_remaining": 8500.0,
                "investment_amount": 6750.0,
                "leveraged_amount": 6750.0,
                "trading_fee": 6.75,
                "strategy_name": "DeduplicationTest",
                "confidence": 90.0,
                "account_balance_before": 10000.0,
                "account_balance_after": 9250.0
            }
            
            # First notification should succeed
            result1 = await self.notification_manager.notify_trade_execution(**notification_data)
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Second notification with same trade_id should be deduplicated
            result2 = await self.notification_manager.notify_trade_execution(**notification_data)
            
            # Test success if first succeeds and second is handled (deduplicated)
            success = result1 and not result2  # Second should be blocked by deduplication
            
            await self._record_test_result("Email Deduplication", success,
                                         f"First email sent: {result1}, Duplicate blocked: {not result2}")
            
        except Exception as e:
            await self._record_test_result("Email Deduplication", False, str(e))
    
    async def _test_system_shutdown(self):
        """Test system shutdown notification"""
        print("🛑 Test 10: System Shutdown Notification...")
        
        try:
            # Calculate uptime
            uptime_seconds = 3665  # ~1 hour for testing
            
            # Mock final statistics
            statistics = {
                "trades_executed": "25",
                "successful_trades": "20",
                "failed_trades": "5",
                "signals_generated": "45",
                "websocket_updates": "1250",
                "strategy_executions": "6",
                "total_errors": "2"
            }
            
            # Mock final account summary
            account_summary = {
                "current_balance": "$10,450.75",
                "total_pnl": "$450.75",
                "open_positions": "2",
                "win_rate": "80.0%",
                "daily_trades": "25"
            }
            
            # Mock final positions
            final_positions = [
                {"symbol": "BTCUSD", "position_type": "LONG"},
                {"symbol": "ETHUSD", "position_type": "LONG"}
            ]
            
            result = await self.notification_manager.notify_system_shutdown(
                uptime_seconds=uptime_seconds,
                statistics=statistics,
                account_summary=account_summary,
                final_positions=final_positions
            )
            
            await self._record_test_result("System Shutdown Notification", result,
                                         "System shutdown email sent with final statistics")
            
        except Exception as e:
            await self._record_test_result("System Shutdown Notification", False, str(e))
    
    async def _calculate_safe_quantity(self, symbol: str, price: float, leverage: float) -> float:
        """Calculate safe quantity for testing"""
        try:
            account_balance = self.broker.account.current_balance if self.broker.account else 10000.0
            risk_amount = account_balance * self.trading_config["balance_per_trade_pct"]
            position_value = risk_amount * leverage
            quantity = position_value / price
            return round(quantity, 6)
        except:
            return 0.1  # Default safe quantity
    
    async def _record_test_result(self, test_name: str, success: bool, details: str):
        """Record test result"""
        self.test_results["total_tests"] += 1
        
        if success:
            self.test_results["passed_tests"] += 1
            status = "✅ PASSED"
            print(f"    {status}: {details}")
        else:
            self.test_results["failed_tests"] += 1
            status = "❌ FAILED"
            print(f"    {status}: {details}")
        
        self.test_results["test_details"].append({
            "test_name": test_name,
            "status": status,
            "success": success,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    
    async def _show_test_results(self):
        """Show comprehensive test results"""
        print("\n" + "=" * 60)
        print("🧪 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)
        
        total = self.test_results["total_tests"]
        passed = self.test_results["passed_tests"]
        failed = self.test_results["failed_tests"]
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📊 Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print()
        
        if failed > 0:
            print("❌ FAILED TESTS:")
            for test in self.test_results["test_details"]:
                if not test["success"]:
                    print(f"  • {test['test_name']}: {test['details']}")
            print()
        
        print("✅ ALL NOTIFICATIONS TESTED:")
        print("  • Trade Execution Emails (BUY/SELL with detailed metrics)")
        print("  • Target Hit Notifications (Profit scenarios)")
        print("  • Stop Loss Hit Notifications (Loss protection)")
        print("  • Risk Alert Notifications (Portfolio warnings)")
        print("  • System Error Notifications (Component failures)")
        print("  • Multiple Position Management")
        print("  • Liquidation Exit Notifications (High-risk scenarios)")
        print("  • Email Deduplication System")
        print("  • System Startup Notifications")
        print("  • System Shutdown Notifications")
        print()
        
        if success_rate >= 90:
            print("🎉 EXCELLENT: System is working perfectly!")
        elif success_rate >= 80:
            print("✅ GOOD: System is working well with minor issues")
        elif success_rate >= 70:
            print("⚠️ MODERATE: System needs some improvements")
        else:
            print("❌ POOR: System requires significant fixes")
        
        print("\n📧 Check your email inbox for all notification types!")
        print("📝 All notifications are also logged to MongoDB database")
        print("=" * 60)
    
    async def _cleanup_components(self):
        """Cleanup all components"""
        print("\n🧹 Cleaning up components...")
        
        try:
            if hasattr(self.notification_manager, 'stop'):
                await self.notification_manager.stop()
            
            if hasattr(self.broker, 'stop'):
                await self.broker.stop()
            
            if hasattr(self.risk_manager, 'stop'):
                await self.risk_manager.stop()
            
            print("✅ Cleanup completed")
            
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")


async def main():
    """Main test runner"""
    print("🚀 Trading System Comprehensive Test Suite")
    print("=" * 60)
    print("This will test ALL notification types:")
    print("• Trade Execution Emails")
    print("• Stop Loss & Target Hit Notifications") 
    print("• Risk Alert Emails")
    print("• System Error Notifications")
    print("• Liquidation Warnings")
    print("• Email Deduplication")
    print("• System Startup/Shutdown Emails")
    print("=" * 60)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run tester
    tester = TradingSystemTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("🧪 Starting Comprehensive Trading System Tests...")
    print("📧 Make sure your email settings are configured in .env file")
    print("⏱️ This test will take approximately 2-3 minutes to complete")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
    finally:
        print("\n🏁 Test suite completed!")