# Advanced Trading System with WebSocket Live Price Integration

## Overview
This is a comprehensive high-speed trading system that integrates real-time WebSocket market data with advanced trading strategies, risk management, and automated execution. The system now uses live price feeds from Delta Exchange WebSocket API instead of dummy data.

## 🚀 Key Features

### ✅ Real-Time WebSocket Integration
- **Live Price Feeds**: Direct connection to Delta Exchange WebSocket API
- **Callback System**: Automatic price updates trigger trading decisions
- **Thread-Safe**: Concurrent price updates with proper locking
- **Auto-Reconnection**: Robust connection management with retry logic

### ✅ Advanced Trading Strategies
- **Multiple Strategy Support**: Random, Volatility, Moving Average, RSI strategies
- **Parallel Execution**: Strategies run concurrently for optimal performance
- **Confidence-Based Selection**: Best signal selection based on confidence levels
- **Symbol-Specific**: Different strategies for different trading pairs

### ✅ Risk Management
- **Position Monitoring**: Real-time position risk analysis
- **Portfolio Risk**: Overall portfolio risk assessment
- **Stop Loss Management**: Automatic stop loss and take profit handling
- **Margin Management**: Leverage and margin usage monitoring

### ✅ System Architecture
- **Async/Await**: Modern Python async programming
- **Threading**: Separate threads for WebSocket and strategy execution
- **Event-Driven**: Callback-based price update handling
- **Modular Design**: Clean separation of concerns

## 📁 Project Structure

```
ConsoleApp/
├── app.py                          # Main trading system
├── test_ws.py                      # WebSocket test script
├── logs/                           # System logs
├── src/
│   ├── broker/
│   │   ├── models.py              # Trading models
│   │   └── paper_broker.py        # Async broker implementation
│   ├── config.py                  # Configuration settings
│   ├── database/
│   │   ├── mongodb_client.py      # Database client
│   │   └── schemas.py             # Data schemas
│   ├── services/
│   │   ├── live_price_ws.py       # WebSocket live price system ⭐
│   │   ├── live_price.py          # Dummy price fetcher
│   │   ├── notifications.py       # Notification system
│   │   └── risk_manager.py        # Risk management
│   └── strategies/
│       ├── strategies.py          # Trading strategies
│       └── strategy_manager.py    # Strategy management
└── venv/                          # Virtual environment
```

## 🔧 System Components

### 1. WebSocket Live Price System (`src/services/live_price_ws.py`)
**Real-time market data integration with Delta Exchange**

**Key Features:**
- ✅ WebSocket connection to Delta Exchange
- ✅ Automatic subscription to BTC-USD and ETH-USD
- ✅ Callback-based price updates
- ✅ Thread-safe price storage
- ✅ Auto-reconnection with retry logic
- ✅ Performance monitoring and statistics

**Usage:**
```python
from src.services.live_price_ws import RealTimeMarketData

def price_callback(live_prices):
    print(f"Live prices: {live_prices}")

# Initialize with callback
live_data = RealTimeMarketData(price_callback=price_callback)
live_data.start()  # Start WebSocket connection
```

### 2. Main Trading System (`app.py`)
**Core trading system with WebSocket integration**

**Key Features:**
- ✅ WebSocket callback integration
- ✅ Strategy execution every 30 seconds
- ✅ Real-time price processing
- ✅ Risk management updates
- ✅ System health monitoring

**Usage:**
```bash
python app.py                    # Start trading system
python app.py --new             # Start with fresh data
```

### 3. Strategy Manager (`src/strategies/strategy_manager.py`)
**Manages multiple trading strategies**

**Strategies Available:**
- **Random Strategy**: Random buy/sell signals
- **Volatility Strategy**: Based on price volatility
- **Moving Average Strategy**: Trend-following
- **RSI Strategy**: Momentum-based trading

### 4. Risk Manager (`src/services/risk_manager.py`)
**Comprehensive risk management**

**Features:**
- Position risk analysis
- Portfolio risk assessment
- Stop loss management
- Margin monitoring

### 5. Async Broker (`src/broker/paper_broker.py`)
**Paper trading implementation**

**Features:**
- Trade execution
- Position management
- PnL calculation
- Account summaries

## 🎯 WebSocket Integration Details

### Callback System
The system uses a callback function that gets triggered whenever new price data arrives from the WebSocket:

```python
def _on_live_price_update(self, live_prices: Dict[str, Dict]):
    """Callback function called when WebSocket receives new price data"""
    for symbol, price_data in live_prices.items():
        # Process each price update
        market_data = MarketData(...)
        # Update trading system
```

### Thread Safety
- **Price Lock**: Thread-safe price storage with `threading.Lock()`
- **Market Data Lock**: Safe concurrent access to market data
- **Async Integration**: Proper async/await integration with main event loop

### Connection Management
- **Auto-Reconnection**: Automatic retry on connection loss
- **Heartbeat Monitoring**: Connection health monitoring
- **Error Handling**: Robust error handling and logging

## 📊 Performance Monitoring

### WebSocket Statistics
```python
stats = live_data.get_performance_stats()
print(f"Status: {stats['status']}")
print(f"Uptime: {stats['uptime_seconds']}s")
print(f"Updates: {stats['update_count']}")
print(f"Updates/Second: {stats['updates_per_second']}")
```

### System Statistics
```python
system_stats = trading_system.get_system_stats()
print(f"Trades Executed: {system_stats['trades_executed']}")
print(f"WebSocket Updates: {system_stats['websocket_updates']}")
print(f"Signals Generated: {system_stats['signals_generated']}")
```

## 🧪 Testing

### WebSocket Test
Test the WebSocket connection independently:

```bash
python test_ws.py
```

**Output:**
```
🚀 Starting WebSocket Test
🔌 Connecting to WebSocket...
✅ WebSocket connected successfully!
📡 Waiting for live price updates...

============================================================
📈 LIVE PRICE UPDATE RECEIVED
============================================================
🔸 BTC-USD:
   💰 Price: $50123.45
   📊 Volume: 1234.56
   📈 High 24h: $50200.00
   📉 Low 24h: $49900.00
   ⏰ Timestamp: 2024-01-15T10:30:45.123456+00:00
   🎯 Mark Price: $50123.45
============================================================
```

### System Test
Test the complete trading system:

```bash
python app.py
```

## ⚙️ Configuration

### WebSocket Settings (`src/config.py`)
```python
WEBSOCKET_MAX_RETRIES = 5
WEBSOCKET_RECONNECT_DELAY = 5
WEBSOCKET_TIMEOUT = 30
```

### Trading Settings
```python
BROKER_INITIAL_BALANCE = 10000.0
BROKER_MAX_LEVERAGE = 5.0
DAILY_TRADES_LIMIT = 50
MAX_POSITION_SIZE = 1000.0
```

### Risk Management Settings
```python
RISK_MAX_PORTFOLIO_RISK = 15.0
RISK_MAX_POSITION_RISK = 5.0
RISK_CHECK_INTERVAL = 5
```

## 🔄 System Flow

1. **Startup**: Initialize WebSocket connection
2. **Price Updates**: WebSocket receives live prices
3. **Callback Trigger**: Price callback processes updates
4. **Strategy Execution**: Strategies analyze market data
5. **Signal Generation**: Best signals selected
6. **Trade Execution**: Execute trades if conditions met
7. **Risk Management**: Monitor positions and portfolio
8. **Repeat**: Continuous cycle

## 📈 Key Benefits

### ✅ Real-Time Performance
- Live price feeds from actual exchange
- Sub-second price update processing
- Minimal latency in trade execution

### ✅ Robust Architecture
- Thread-safe operations
- Proper error handling
- Auto-reconnection capabilities
- Comprehensive logging

### ✅ Scalable Design
- Modular component architecture
- Easy to add new strategies
- Configurable risk parameters
- Extensible notification system

### ✅ Professional Features
- Comprehensive monitoring
- Performance statistics
- Health checks
- Graceful shutdown

## 🚀 Quick Start

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Test WebSocket**:
```bash
python test_ws.py
```

3. **Run Trading System**:
```bash
python app.py
```

4. **Monitor Logs**:
```bash
tail -f logs/trading.log
```

## 📝 Logging

The system provides comprehensive logging:

- **File Logging**: `logs/trading.log`
- **Console Output**: Real-time system status
- **WebSocket Logs**: Connection and data flow
- **Trade Logs**: All trading activities
- **Error Logs**: Exception handling

## 🔧 Troubleshooting

### WebSocket Connection Issues
1. Check internet connection
2. Verify Delta Exchange API status
3. Check firewall settings
4. Review connection logs

### Trading System Issues
1. Check MongoDB connection
2. Verify configuration settings
3. Review error logs
4. Test individual components

## 📚 Advanced Usage

### Custom Strategies
Add new trading strategies in `src/strategies/strategies.py`:

```python
class CustomStrategy(BaseStrategy):
    def signal(self, market_data: MarketData) -> TradingSignal:
        # Your custom logic here
        return TradingSignal(...)
```

### Custom Price Callbacks
Extend the price callback for custom processing:

```python
def custom_price_callback(live_prices):
    # Custom price processing
    for symbol, data in live_prices.items():
        # Your custom logic
        pass
```

## 🎯 Performance Optimization

### Best Practices
1. **Use Async/Await**: For I/O operations
2. **Thread Safety**: Always use locks for shared data
3. **Error Handling**: Comprehensive exception handling
4. **Resource Management**: Proper cleanup and shutdown
5. **Monitoring**: Regular health checks and statistics

### Memory Management
- Thread-safe data structures
- Proper cleanup on shutdown
- Efficient data structures
- Regular garbage collection

## 🔒 Security Considerations

1. **API Keys**: Secure storage of exchange credentials
2. **Network Security**: Encrypted WebSocket connections
3. **Data Validation**: Input validation for all data
4. **Error Handling**: Secure error messages
5. **Logging**: Sensitive data filtering

## 📊 Monitoring and Alerts

### System Health Checks
- WebSocket connection status
- Strategy execution monitoring
- Risk management alerts
- Performance metrics

### Notification System
- Trade execution alerts
- Risk management warnings
- System status updates
- Error notifications

---

**🎉 The system is now fully integrated with live WebSocket price feeds and ready for real-time trading!** 