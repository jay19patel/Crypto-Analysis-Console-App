#!/usr/bin/env python3
"""
Simple WebSocket Test Script
Tests the RealTimeMarketData WebSocket connection and displays live price updates with insights
"""

import time
import logging
import json
import os
from datetime import datetime
from src.services.live_price_ws import RealTimeMarketData
from src.services.insights import MarketDataAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see more details
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)

# Create organized data storage structure
def create_data_directories():
    """Create organized directory structure for data storage"""
    base_dir = "market_data"
    directories = {
        "base": base_dir,
        "daily": os.path.join(base_dir, "daily"),
        "hourly": os.path.join(base_dir, "hourly"),
        "raw": os.path.join(base_dir, "raw"),
        "insights": os.path.join(base_dir, "insights"),
        "logs": os.path.join(base_dir, "logs")
    }
    
    for dir_path in directories.values():
        os.makedirs(dir_path, exist_ok=True)
    
    return directories

# Initialize directories and analyzer
data_dirs = create_data_directories()
insights_analyzer = MarketDataAnalyzer()

# Global variables for JSON storage
json_data = {}
current_date = datetime.now().strftime("%Y-%m-%d")
current_hour = datetime.now().strftime("%H")
json_filename = os.path.join(data_dirs["daily"], f"market_data_{current_date}.json")
hourly_filename = os.path.join(data_dirs["hourly"], f"market_data_{current_date}_{current_hour}.json")

def save_to_json(live_prices, insights=None):
    """Save data to JSON file with organized structure"""
    global json_data, current_date, current_hour, json_filename, hourly_filename
    
    # Check if date changed
    new_date = datetime.now().strftime("%Y-%m-%d")
    new_hour = datetime.now().strftime("%H")
    
    if new_date != current_date:
        current_date = new_date
        json_filename = os.path.join(data_dirs["daily"], f"market_data_{current_date}.json")
        json_data = {}  # Reset for new date
    
    if new_hour != current_hour:
        current_hour = new_hour
        hourly_filename = os.path.join(data_dirs["hourly"], f"market_data_{current_date}_{current_hour}.json")
    
    # Create data entry
    timestamp = datetime.now().isoformat()
    data_entry = {
        "timestamp": timestamp,
        "live_prices": live_prices,
        "insights": {}
    }
    
    # Add insights if available
    if insights:
        # Handle single insight object
        if hasattr(insights, 'symbol'):
            # Single MarketInsights object
            data_entry["insights"][insights.symbol] = {
                "price_insights": insights.price_insights,
                "volume_insights": insights.volume_insights,
                "volatility_insights": insights.volatility_insights,
                "funding_insights": insights.funding_insights,
                "order_book_insights": insights.order_book_insights,
                "risk_insights": insights.risk_insights,
                "trend_insights": insights.trend_insights
            }
        else:
            # Dictionary of insights
            for symbol, insight in insights.items():
                data_entry["insights"][symbol] = {
                    "price_insights": insight.price_insights,
                    "volume_insights": insight.volume_insights,
                    "volatility_insights": insight.volatility_insights,
                    "funding_insights": insight.funding_insights,
                    "order_book_insights": insight.order_book_insights,
                    "risk_insights": insight.risk_insights,
                    "trend_insights": insight.trend_insights
                }
    
    # Append to existing data or create new
    if timestamp not in json_data:
        json_data[timestamp] = data_entry
    
    # Save to daily file
    try:
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Daily data saved to: {json_filename}")
    except Exception as e:
        print(f"❌ Error saving daily JSON: {e}")
    
    # Save to hourly file
    try:
        hourly_data = {timestamp: data_entry}
        with open(hourly_filename, 'w', encoding='utf-8') as f:
            json.dump(hourly_data, f, indent=2, ensure_ascii=False)
        print(f"💾 Hourly data saved to: {hourly_filename}")
    except Exception as e:
        print(f"❌ Error saving hourly JSON: {e}")

def price_callback(live_prices):
    """Callback function to handle live price updates"""
    # Generate insights for each symbol
    insights = {}
    for symbol, price_data in live_prices.items():
        try:
            insight = insights_analyzer.analyze_market_data(symbol, price_data)
            insights[symbol] = insight
        except Exception as e:
            print(f"❌ Error generating insights for {symbol}: {e}")
    
    # Save data to JSON immediately
    save_to_json(live_prices, insights)
    
    # Display data immediately
    print("\n" + "="*100)
    print("📈 LIVE PRICE UPDATE RECEIVED")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*100)
    
    for symbol, price_data in live_prices.items():
        print(f"🔸 {symbol}:")
        print(f"   💰 Price: ${price_data.get('price', 0):.2f}")
        print(f"   🎯 Mark Price: ${price_data.get('mark_price', 0):.2f}")
        print(f"   💎 Spot Price: ${price_data.get('spot_price', 0):.2f}")
        
        # Volume and Turnover
        print(f"   📊 Volume: {price_data.get('volume', 0):.2f}")
        print(f"   💵 Turnover: ${price_data.get('turnover', 0):.2f}")
        print(f"   💵 Turnover USD: ${price_data.get('turnover_usd', 0):.2f}")
        
        # Price Levels
        print(f"   📈 High 24h: ${price_data.get('high', 0):.2f}")
        print(f"   📉 Low 24h: ${price_data.get('low', 0):.2f}")
        print(f"   🚪 Open: ${price_data.get('open', 0):.2f}")
        print(f"   🚪 Close: ${price_data.get('close', 0):.2f}")
        
        # Open Interest
        print(f"   📋 Open Interest: {price_data.get('open_interest', 0):.2f}")
        print(f"   📋 OI Value: {price_data.get('oi_value', 0):.2f}")
        print(f"   📋 OI Contracts: {price_data.get('oi_contracts', 0):.0f}")
        print(f"   📋 OI Value USD: ${price_data.get('oi_value_usd', 0):.2f}")
        print(f"   📋 OI Change 6h: ${price_data.get('oi_change_usd_6h', 0):.2f}")
        
        # Funding and Basis
        if price_data.get('funding_rate') is not None:
            print(f"   💸 Funding Rate: {price_data['funding_rate']:.4f}")
        if price_data.get('mark_basis') is not None:
            print(f"   📊 Mark Basis: {price_data['mark_basis']:.4f}")
        
        # Price Changes
        print(f"   📊 Mark Change 24h: {price_data.get('mark_change_24h', 0):.2f}%")
        
        # Contract Details
        print(f"   📋 Contract Type: {price_data.get('contract_type', 'N/A')}")
        print(f"   🏷️  Underlying Asset: {price_data.get('underlying_asset_symbol', 'N/A')}")
        print(f"   💰 Turnover Symbol: {price_data.get('turnover_symbol', 'N/A')}")
        print(f"   📋 OI Value Symbol: {price_data.get('oi_value_symbol', 'N/A')}")
        print(f"   📝 Description: {price_data.get('description', 'N/A')}")
        print(f"   🆔 Product ID: {price_data.get('product_id', 'N/A')}")
        
        # Margin and Tick Size
        if price_data.get('initial_margin') is not None:
            print(f"   💰 Initial Margin: {price_data['initial_margin']:.2f}")
        if price_data.get('tick_size') is not None:
            print(f"   📏 Tick Size: {price_data['tick_size']:.2f}")
        
        # Price Bands
        if price_data.get('price_band_lower') is not None:
            print(f"   📊 Price Band Lower: ${price_data['price_band_lower']:.2f}")
        if price_data.get('price_band_upper') is not None:
            print(f"   📊 Price Band Upper: ${price_data['price_band_upper']:.2f}")
        
        # Order Book Data
        if price_data.get('best_bid') is not None:
            print(f"   📈 Best Bid: ${price_data['best_bid']:.2f}")
        if price_data.get('best_ask') is not None:
            print(f"   📉 Best Ask: ${price_data['best_ask']:.2f}")
        if price_data.get('bid_size') is not None:
            print(f"   📈 Bid Size: {price_data['bid_size']:.2f}")
        if price_data.get('ask_size') is not None:
            print(f"   📉 Ask Size: {price_data['ask_size']:.2f}")
        if price_data.get('mark_iv') is not None:
            print(f"   📊 Mark IV: {price_data['mark_iv']:.4f}")
        
        # Metadata
        print(f"   📊 Size: {price_data.get('size', 0):.2f}")
        print(f"   🏷️  Tags: {price_data.get('tags', [])}")
        print(f"   ⏰ Time: {price_data.get('time', 'N/A')}")
        print(f"   ⏰ Timestamp: {price_data.get('timestamp', 'N/A')}")
        
        # Greeks (if available)
        if price_data.get('greeks') is not None:
            print(f"   📊 Greeks: {price_data['greeks']}")
        
        # Display insights if available
        insight = insights.get(symbol) if insights else None
        
        if insight:
            print(f"\n   🧠 INSIGHTS FOR {symbol}:")
            print(f"   " + "="*60)
            
            # Price Insights
            if insight.price_insights:
                print(f"   💰 PRICE INSIGHTS:")
                print(f"      📊 Daily Change: {insight.price_insights.get('daily_change_percentage', 0):.2f}%")
                print(f"      📈 Price Position: {insight.price_insights.get('price_position_in_range', 0):.1f}%")
                print(f"      📊 Volatility: {insight.price_insights.get('price_volatility', 'N/A')}")
                print(f"      💎 Spread: {insight.price_insights.get('spread_percentage', 0):.4f}%")
            
            # Volume Insights
            if insight.volume_insights:
                print(f"   📊 VOLUME INSIGHTS:")
                print(f"      📈 Volume Intensity: {insight.volume_insights.get('volume_intensity', 'N/A')}")
                print(f"      📋 OI Intensity: {insight.volume_insights.get('oi_intensity', 'N/A')}")
                print(f"      📊 V/OI Ratio: {insight.volume_insights.get('volume_oi_ratio', 0):.2f}")
            
            # Volatility Insights
            if insight.volatility_insights:
                print(f"   📊 VOLATILITY INSIGHTS:")
                print(f"      📈 IV Level: {insight.volatility_insights.get('volatility_level', 'N/A')}")
                print(f"      ⚠️  Risk Level: {insight.volatility_insights.get('volatility_risk', 'N/A')}")
                print(f"      📊 IV Value: {insight.volatility_insights.get('implied_volatility', 0):.4f}")
            
            # Funding Insights
            if insight.funding_insights:
                print(f"   💸 FUNDING INSIGHTS:")
                print(f"      📈 Direction: {insight.funding_insights.get('funding_direction', 'N/A')}")
                print(f"      📊 Intensity: {insight.funding_insights.get('funding_intensity', 'N/A')}")
                print(f"      ⚠️  Risk: {insight.funding_insights.get('funding_risk', 'N/A')}")
            
            # Order Book Insights
            if insight.order_book_insights:
                print(f"   📊 ORDER BOOK INSIGHTS:")
                print(f"      📈 Spread: {insight.order_book_insights.get('spread_percentage', 0):.4f}%")
                print(f"      ⚖️  Imbalance: {insight.order_book_insights.get('order_imbalance', 'N/A')}")
                print(f"      📊 Depth: {insight.order_book_insights.get('market_depth', 'N/A')}")
            
            # Risk Insights
            if insight.risk_insights:
                print(f"   ⚠️  RISK INSIGHTS:")
                print(f"      🛡️  Overall Risk: {insight.risk_insights.get('overall_risk_level', 'N/A')}")
                print(f"      💰 Margin Risk: {insight.risk_insights.get('margin_risk', 'N/A')}")
                print(f"      📊 Band Risk: {insight.risk_insights.get('band_risk', 'N/A')}")
            
            # Trend Insights
            if insight.trend_insights:
                print(f"   📈 TREND INSIGHTS:")
                print(f"      📊 Direction: {insight.trend_insights.get('trend_direction', 'N/A')}")
                print(f"      💪 Strength: {insight.trend_insights.get('trend_strength', 'N/A')}")
                print(f"      🎯 Confidence: {insight.trend_insights.get('trend_confidence', 'N/A')}")
                print(f"      📈 Momentum: {insight.trend_insights.get('price_momentum', 'N/A')}")
        
        print()
    
    print("="*100)

def main():
    """Main test function"""
    print("🚀 Starting WebSocket Test")
    print("This will connect to Delta Exchange WebSocket and display live price updates")
    print("Press Ctrl+C to stop the test")
    print("-" * 60)
    
    # Create WebSocket instance with callback
    live_data = RealTimeMarketData(price_callback=price_callback)
    
    try:
        # Start the WebSocket connection
        print("🔌 Connecting to WebSocket...")
        if live_data.start():
            print("✅ WebSocket connected successfully!")
            print("📡 Waiting for live price updates...")
            print("⏳ Updates will appear automatically when received")
            print("-" * 60)
            
            # Keep running and display stats every 30 seconds
            start_time = time.time()
            while True:
                time.sleep(30)
                
                # Display performance stats
                stats = live_data.get_performance_stats()
                print("\n" + "📊 PERFORMANCE STATS" + "="*50)
                print(f"🟢 Status: {stats.get('status', 'unknown')}")
                print(f"⏱️  Uptime: {stats.get('uptime_seconds', 0):.1f} seconds")
                print(f"📈 Total Updates: {stats.get('update_count', 0)}")
                print(f"⚡ Updates/Second: {stats.get('updates_per_second', 0):.2f}")
                print(f"🎯 Active Symbols: {stats.get('active_symbols', 0)}")
                print(f"🕐 Last Update: {stats.get('last_update', 'N/A')}")
                print(f"💾 Daily JSON File: {json_filename}")
                print(f"💾 Hourly JSON File: {hourly_filename}")
                print("="*60)
                
        else:
            print("❌ Failed to connect to WebSocket")
            return
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping WebSocket test...")
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        # Stop the WebSocket
        live_data.stop()
        print("✅ WebSocket test completed")

if __name__ == "__main__":
    main()