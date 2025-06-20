# Crypto Price Tracker

A professional cryptocurrency analysis platform with real-time WebSocket monitoring, technical indicators, AI-powered strategies, and MongoDB data persistence.

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/crypto-price-tracker.git
cd crypto-price-tracker
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Run analysis
python app.py --analysis --symbol BTCUSD
```

## 📊 Features

- **Real-time WebSocket Price Monitoring** - Live cryptocurrency price feeds
- **Advanced Technical Analysis** - 11+ indicators (EMA, RSI, MACD, Supertrend, ADX, etc.)
- **AI-Powered Strategies** - Google Gemini integration for smart analysis
- **Multiple Trading Strategies** - Trend following, MACD, RSI, Stochastic, VWAP
- **MongoDB Integration** - Store analysis results with timestamps
- **Rich Console UI** - Beautiful tables, progress bars, and colored output

## 🎯 Usage

### Basic Commands
```bash
python app.py --check                    # System diagnostics
python app.py --liveprice                # Live price monitoring
python app.py --analysis                 # One-time technical analysis
python app.py --analysis 5               # Auto-refresh every 5 seconds
```

### Advanced Options
```bash
# Custom symbol and timeframe
python app.py --analysis --symbol ETHUSD --resolution 1h --days 30

# Save to MongoDB
python app.py --analysis --save
python app.py --analysis 5 --save        # Auto-refresh + save
```

### Command Options
| Option | Description | Default |
|--------|-------------|---------|
| `--check` | Run system health checks | - |
| `--liveprice` | Start live price monitoring | - |
| `--analysis [SEC]` | Technical analysis with optional refresh | - |
| `--symbol` | Trading pair (BTCUSD, ETHUSD, etc.) | BTCUSD |
| `--resolution` | Timeframe (1m, 5m, 15m, 1h, 1d) | 5m |
| `--days` | Historical data days | 10 |
| `--save` | Save results to MongoDB | false |

## 🛠️ MongoDB Setup (Optional)

For data persistence:
```bash
# Install MongoDB
# Windows: Download from mongodb.com
# Linux: sudo apt install mongodb

# Start service
net start MongoDB        # Windows
sudo systemctl start mongod  # Linux

# Configure (optional)
export CRYPTO_MONGODB_URL="mongodb://localhost:27017"
export CRYPTO_MONGODB_DATABASE="crypto_analysis"
```

## 🔧 Adding New Strategies

### 1. Create Strategy File
Create `src/strategies/your_strategy.py`:

```python
from .base_strategy import BaseStrategy, StrategySignal, StrategyResult
import pandas as pd

class YourStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("Your Strategy Name")
    
    def analyze(self, df: pd.DataFrame) -> StrategyResult:
        # Your strategy logic here
        signal = StrategySignal.BUY  # or SELL, HOLD, NEUTRAL
        confidence = 75.0  # 0-100
        interpretation = "Your analysis explanation"
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=confidence,
            interpretation=interpretation
        )
```

### 2. Register Strategy
Add to `src/strategies/strategy_manager.py`:

```python
from .your_strategy import YourStrategy

class StrategyManager:
    def __init__(self):
        self.strategies = [
            # ... existing strategies
            YourStrategy(),  # Add your strategy here
        ]
```

### 3. Test Your Strategy
```bash
python app.py --analysis --symbol BTCUSD
```

## 📁 Project Structure

```
├── app.py                      # Main application
├── requirements.txt            # Dependencies
└── src/
    ├── config.py              # Configuration settings
    ├── data/
    │   ├── websocket_client.py    # WebSocket implementation
    │   ├── technical_analysis.py  # Technical indicators
    │   └── mongodb_client.py      # Database operations
    ├── strategies/
    │   ├── base_strategy.py       # Strategy base class
    │   ├── strategy_manager.py    # Strategy orchestration
    │   ├── trend_strategy.py      # Trend following
    │   ├── macd_strategy.py       # MACD crossover
    │   ├── rsi_strategy.py        # RSI overbought/oversold
    │   ├── ai_strategy.py         # AI-powered analysis
    │   └── your_strategy.py       # Your custom strategies
    ├── system/
    │   └── health_checker.py      # System diagnostics
    └── ui/
        └── console.py             # Rich console interface
```

## ⚡ Technical Indicators

| Indicator | Purpose | Configuration |
|-----------|---------|---------------|
| EMA | Trend direction | 5, 15, 50 periods |
| RSI | Momentum oscillator | 14 period |
| MACD | Trend changes | 12, 26, 9 settings |
| Supertrend | Trend confirmation | 10 period, 3.0 multiplier |
| ADX | Trend strength | 14 period |
| Stochastic | Overbought/oversold | 14 period |
| VWAP | Volume-weighted price | Daily |
| ATR | Volatility measure | 14 period |
| Z-Score | Price deviation | 20 period |

## 🤖 AI Integration

Uses Google Gemini AI for:
- Market sentiment analysis
- Pattern recognition
- Trade recommendations
- Risk assessment

Set your API key:
```bash
export CRYPTO_GOOGLE_API_KEY="your-api-key"
```

## 🔒 Environment Variables

```bash
# WebSocket Configuration
export CRYPTO_WEBSOCKET_URL="wss://socket.india.delta.exchange"
export CRYPTO_PRICE_UPDATE_INTERVAL=5

# MongoDB Configuration  
export CRYPTO_MONGODB_URL="mongodb://localhost:27017"
export CRYPTO_MONGODB_DATABASE="crypto_analysis"

# AI Configuration
export CRYPTO_GOOGLE_API_KEY="your-api-key"
```

## 📈 Strategy Types

1. **Trend Following** - EMA crossovers and trend confirmation
2. **MACD Strategy** - Signal line crossovers and histogram analysis
3. **RSI Strategy** - Overbought/oversold conditions
4. **Stochastic Strategy** - K/D line crossovers
5. **VWAP Strategy** - Volume-weighted average price analysis
6. **Advanced Trend** - Multi-indicator trend confirmation
7. **AI Powered** - Machine learning-based analysis

## 🤝 Contributing

1. Fork the repository
2. Create your strategy: `src/strategies/your_strategy.py`
3. Add tests and documentation
4. Submit a pull request

## 📧 Developer

**Jay Patel**  
Email: developer.jay19@gmail.com

## 📄 License

MIT License - Feel free to use and modify. 