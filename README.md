# 🚀 Professional Trading System - Simple Setup

## 📁 File Structure
```
Crypto-Analysis-Console-App/
├── main.py                     # Main application (NEW - Use this instead of app.py)
├── app.py                      # Old application (Keep for reference)
├── requirements.txt            # Dependencies
├── .env.example               # Configuration template
└── src/
    ├── core/
    │   └── trading_system.py   # Enhanced trading system
    ├── api/
    │   └── websocket_server.py # WebSocket server for frontend
    ├── broker/
    │   ├── paper_broker.py     # Paper trading
    │   ├── models.py           # Trading models
    │   └── historical_data.py  # Historical data
    ├── services/
    │   ├── live_price_ws.py    # Live price WebSocket
    │   ├── risk_manager.py     # Risk management
    │   ├── notifications.py    # Email notifications
    │   └── insights.py         # Market insights
    ├── strategies/
    │   ├── base_strategy.py    # Strategy base
    │   ├── strategies.py       # Trading strategies
    │   └── strategy_manager.py # Strategy manager
    ├── database/
    │   ├── mongodb_client.py   # Database client
    │   └── schemas.py          # Data models
    ├── utils/
    │   └── performance.py      # Performance tools
    └── config.py               # Configuration
```

## ⚡ Quick Start

### 1. Setup Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure System
```bash
# Copy configuration template
cp .env.example .env

# Edit .env file with your settings
nano .env
```

### 3. Start MongoDB
```bash
# Linux (Ubuntu/Debian)
sudo systemctl start mongod

# Mac
brew services start mongodb-community

# Windows
net start MongoDB
```

### 4. Run Trading System
```bash
# Basic start
python main.py

# Start fresh (delete all data)
python main.py --new

# Enable live price saving
python main.py --liveSave

# Use different WebSocket port
python main.py --websocket-port 8080

# Debug mode
python main.py --log-level DEBUG
```

## 🔧 Configuration (.env file)

```bash
# Database
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=trading_system

# Trading Settings
BROKER_INITIAL_BALANCE=10000.0
DAILY_TRADES_LIMIT=50

# Email Notifications (Optional)
EMAIL_ENABLED=true
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=your-email@gmail.com

# WebSocket
WEBSOCKET_SERVER_PORT=8765
```

## 📡 WebSocket Channels

Connect to `ws://localhost:8765` and subscribe to:

- `live_prices` - Real-time market data
- `positions` - Position updates
- `notifications` - System alerts
- `strategy_signals` - Trading signals

## 🔗 WebSocket Client Example

```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = function() {
    // Subscribe to channels
    ws.send(JSON.stringify({
        type: 'subscribe',
        channels: ['live_prices', 'positions', 'notifications']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## 🚨 Troubleshooting

### MongoDB Issues
```bash
# Check if MongoDB is running
sudo systemctl status mongod

# Start MongoDB
sudo systemctl start mongod
```

### WebSocket Issues
```bash
# Check if port is open
netstat -tulpn | grep 8765

# Test WebSocket connection
# Install wscat: npm install -g wscat
wscat -c ws://localhost:8765
```

### Python Issues
```bash
# Check Python version (need 3.8+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📊 Key Features

✅ **Real-time Trading**: Live market data from Delta Exchange  
✅ **WebSocket Server**: Real-time data broadcasting  
✅ **Risk Management**: Position monitoring and portfolio risk  
✅ **Multiple Strategies**: Parallel strategy execution  
✅ **Paper Trading**: Safe testing environment  
✅ **Email Notifications**: Trade and system alerts  
✅ **Performance Monitoring**: System health tracking  
✅ **24/7 Operation**: Designed for continuous running  

## 🔄 System Commands

```bash
# Check system status
python main.py --health-check

# View live logs
tail -f logs/trading.log

# Stop system (Ctrl+C or)
pkill -f "python main.py"
```

---
**⚠️ Important**: This is for educational purposes only. Always test with paper trading before using real money!