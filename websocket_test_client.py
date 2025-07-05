#!/usr/bin/env python3
"""
WebSocket Test Client to verify live data from trading system
"""

import asyncio
import websockets
import json
import time
from datetime import datetime

async def test_websocket():
    uri = "ws://localhost:8765"
    
    try:
        print(f"🔗 Connecting to {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to WebSocket server!")
            print("📡 Waiting for data...")
            print("-" * 60)
            
            # Listen for messages for 60 seconds
            start_time = time.time()
            message_count = 0
            
            while time.time() - start_time < 60:  # Run for 60 seconds
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message_count += 1
                    
                    # Parse and display the message
                    try:
                        data = json.loads(message)
                        msg_type = data.get('type', 'unknown')
                        timestamp = data.get('timestamp', 'no_timestamp')
                        source = data.get('source', 'unknown')
                        
                        print(f"📨 Message #{message_count} [{timestamp}]")
                        print(f"   Type: {msg_type}")
                        print(f"   Source: {source}")
                        
                        if msg_type == 'liveprice':
                            prices = data.get('data', {}).get('prices', {})
                            print(f"   💰 Live Prices: {len(prices)} symbols")
                            for symbol, price_data in prices.items():
                                price = price_data.get('price', 0)
                                print(f"      {symbol}: ${price:.2f}")
                                
                        elif msg_type == 'positions':
                            position_data = data.get('data', {})
                            total_positions = position_data.get('total_positions', 0)
                            print(f"   📊 Positions: {total_positions} open")
                            for pos in position_data.get('positions', []):
                                symbol = pos.get('symbol', 'Unknown')
                                entry_price = pos.get('entry_price', 0)
                                current_price = pos.get('current_price', 0)
                                pnl = pos.get('unrealized_pnl', 0)
                                print(f"      {symbol}: Entry=${entry_price:.2f}, Current=${current_price:.2f}, PnL=${pnl:.2f}")
                                
                        elif msg_type == 'analysis':
                            analysis_data = data.get('data', {})
                            symbols_analyzed = analysis_data.get('symbols_analyzed', 0)
                            print(f"   📈 Analysis: {symbols_analyzed} symbols analyzed")
                            
                        elif msg_type == 'logs':
                            log_data = data.get('data', {})
                            message_text = log_data.get('message', '')
                            level = data.get('level', 'info')
                            print(f"   📝 Log [{level.upper()}]: {message_text}")
                            
                        else:
                            print(f"   📄 Data: {str(data)[:100]}...")
                        
                        print("-" * 60)
                        
                    except json.JSONDecodeError:
                        print(f"📨 Raw Message #{message_count}: {message[:100]}...")
                        print("-" * 60)
                        
                except asyncio.TimeoutError:
                    print(f"⏰ No message received in 5 seconds... (Total messages: {message_count})")
                    
                except websockets.exceptions.ConnectionClosed:
                    print("❌ Connection closed by server")
                    break
                    
            print(f"\n📊 Test Summary:")
            print(f"   Total messages received: {message_count}")
            print(f"   Test duration: {time.time() - start_time:.1f} seconds")
            
    except ConnectionRefusedError:
        print("❌ Connection refused - WebSocket server is not running on port 8765")
        print("   Make sure the trading system is running first!")
        
    except Exception as e:
        print(f"❌ Error connecting to WebSocket: {e}")

if __name__ == "__main__":
    print("🚀 WebSocket Trading System Test Client")
    print("=" * 60)
    asyncio.run(test_websocket()) 