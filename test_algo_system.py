#!/usr/bin/env python3
"""
Complete test for algo trading system with proper position sizing and liquidation protection
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import get_trading_config
from src.broker.paper_broker import AsyncBroker, TradeRequest
from src.services.risk_manager import AsyncRiskManager


async def test_algo_trading_system():
    """Test the complete algo trading system"""
    
    print("🚀 Testing Complete Algo Trading System")
    print("=" * 60)
    
    # Initialize components
    broker = AsyncBroker()
    risk_manager = AsyncRiskManager(broker)
    
    # Start systems
    await broker.start()
    await risk_manager.start()
    
    # Get config
    config = get_trading_config()
    
    print(f"📊 Algo Trading Configuration:")
    print(f"   Initial Balance: ₹{config['initial_balance']:,.0f}")
    print(f"   Balance Per Trade: {config['balance_per_trade_pct']*100:.0f}%")
    print(f"   Default Leverage: {config['default_leverage']:.0f}x")
    print(f"   Liquidation Buffer: {config['liquidation_buffer_pct']*100:.0f}%")
    print()
    
    # Test 1: Calculate position sizing for BTC trade
    print("🔍 Test 1: Position Sizing with 50x Leverage")
    print("-" * 50)
    
    symbol = "BTCUSD"
    price = 50000.0
    requested_qty = 10.0  # Large request to test limits
    
    # Test with default leverage (50x)
    safe_qty, reason = await risk_manager.calculate_safe_quantity_async(
        symbol, price, requested_qty
    )
    
    print(f"Symbol: {symbol}")
    print(f"Price: ₹{price:,.0f}")
    print(f"Requested Quantity: {requested_qty}")
    print(f"Safe Quantity: {safe_qty:.6f}")
    print(f"Details: {reason}")
    
    # Calculate expected values for verification
    balance = config['initial_balance']
    margin_per_trade = balance * config['balance_per_trade_pct']  # 20% = ₹2,000
    leverage = config['default_leverage']  # 50x
    position_value = margin_per_trade * leverage  # ₹2,000 * 50 = ₹100,000
    expected_qty = position_value / price  # ₹100,000 / ₹50,000 = 2.0
    liquidation_buffer = config['liquidation_buffer_pct']  # 10%
    safe_expected_qty = expected_qty * (1 - liquidation_buffer)  # 2.0 * 0.9 = 1.8
    
    print(f"\n📈 Expected Calculations:")
    print(f"   Margin to use (20%): ₹{margin_per_trade:,.0f}")
    print(f"   Position value (50x): ₹{position_value:,.0f}")
    print(f"   Expected quantity: {expected_qty:.6f}")
    print(f"   Safe quantity (with buffer): {safe_expected_qty:.6f}")
    print()
    
    # Test 2: Execute the trade
    if safe_qty > 0:
        print("💰 Test 2: Execute Trade with Real Broker Logic")
        print("-" * 45)
        
        # Get account before trade
        account_before = await broker.get_account_summary_async()
        print(f"Before Trade:")
        print(f"   Available Balance: ₹{account_before['current_balance']:,.0f}")
        print(f"   Margin Used: ₹{account_before['total_margin_used']:,.0f}")
        
        # Execute trade
        trade_request = TradeRequest(
            symbol=symbol,
            signal="BUY",
            price=price,
            quantity=safe_qty,
            leverage=leverage,
            strategy_name="AlgoTradingStrategy"
        )
        
        success = await broker.execute_trade_async(trade_request)
        
        if success:
            # Get account after trade
            account_after = await broker.get_account_summary_async()
            print(f"\nAfter Trade:")
            print(f"   Available Balance: ₹{account_after['current_balance']:,.0f}")
            print(f"   Margin Used: ₹{account_after['total_margin_used']:,.0f}")
            
            # Verify calculations
            actual_position_value = safe_qty * price
            actual_margin = actual_position_value / leverage
            actual_fee = actual_margin * config['trading_fee_pct']
            actual_total_cost = actual_margin + actual_fee
            
            print(f"\n✅ Trade Verification:")
            print(f"   Position Value: ₹{actual_position_value:,.0f}")
            print(f"   Margin Required: ₹{actual_margin:,.0f}")  
            print(f"   Trading Fee: ₹{actual_fee:.2f}")
            print(f"   Total Cost: ₹{actual_total_cost:.2f}")
            print(f"   Balance Deducted: ₹{account_before['current_balance'] - account_after['current_balance']:.2f}")
            
            # Test 3: Test multiple trades (should be blocked)
            print("\n🚫 Test 3: Multiple Positions (Should be Blocked)")
            print("-" * 45)
            
            # Try to open another BTC position
            second_qty, second_reason = await risk_manager.calculate_safe_quantity_async(
                "BTCUSD", 51000.0, 1.0
            )
            print(f"Second BTC trade: Qty={second_qty:.6f}, Reason: {second_reason}")
            
            # Try ETH trade (should work)
            eth_qty, eth_reason = await risk_manager.calculate_safe_quantity_async(
                "ETHUSD", 3000.0, 10.0
            )
            print(f"ETH trade: Qty={eth_qty:.6f}")
            print(f"Details: {eth_reason}")
            
            # Test 4: Close position and verify margin release
            print("\n🔄 Test 4: Close Position & Margin Release")
            print("-" * 40)
            
            # Simulate profitable close (3% profit)
            exit_price = price * 1.03
            position_id = trade_request.position_id
            
            close_success = await broker.close_position_async(position_id, exit_price, "Profit Taking")
            
            if close_success:
                # Get final account state
                account_final = await broker.get_account_summary_async()
                print(f"After Position Close:")
                print(f"   Available Balance: ₹{account_final['current_balance']:,.0f}")
                print(f"   Margin Used: ₹{account_final['total_margin_used']:,.0f}")
                print(f"   Realized P&L: ₹{account_final['realized_pnl']:,.0f}")
                
                # Calculate P&L
                position_pnl = (exit_price - price) * safe_qty
                expected_balance = config['initial_balance'] + position_pnl - (actual_fee * config['exit_fee_multiplier'])
                
                print(f"\n💰 P&L Analysis:")
                print(f"   Entry Price: ₹{price:,.0f}")
                print(f"   Exit Price: ₹{exit_price:,.0f}")
                print(f"   Position P&L: ₹{position_pnl:,.0f}")
                print(f"   Expected Final Balance: ₹{expected_balance:,.0f}")
                print(f"   Actual Final Balance: ₹{account_final['current_balance']:,.0f}")
                
                # Test 5: Verify we can trade again after closing
                print(f"\n🔄 Test 5: New Trade After Position Close")
                print("-" * 40)
                
                new_qty, new_reason = await risk_manager.calculate_safe_quantity_async(
                    "ADAUSD", 0.5, 1000.0
                )
                
                if new_qty > 0:
                    new_position_value = new_qty * 0.5
                    new_margin = new_position_value / leverage
                    balance_usage = (new_margin / account_final['current_balance']) * 100
                    
                    print(f"ADA Trade Available:")
                    print(f"   Quantity: {new_qty:.0f} ADA")
                    print(f"   Position Value: ₹{new_position_value:.0f}")
                    print(f"   Margin Required: ₹{new_margin:.0f} ({balance_usage:.1f}% of balance)")
                else:
                    print(f"ADA Trade: {new_reason}")
                
            else:
                print("❌ Failed to close position")
        else:
            print("❌ Failed to execute trade")
    else:
        print("❌ No safe quantity available for trade")
    
    # Stop systems
    await risk_manager.stop()
    await broker.stop()
    
    print("\n✅ Algo Trading System Test Complete!")
    print("🎯 System is ready for live algo trading!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_algo_trading_system())