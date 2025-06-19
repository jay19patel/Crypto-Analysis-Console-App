# Crypto Price Tracker

A production-ready cryptocurrency price tracking system with real-time WebSocket data and technical analysis capabilities.

## Features

- **Live Price Monitoring**: Real-time cryptocurrency price updates via WebSocket connection
- **Technical Analysis**: Comprehensive technical analysis with multiple indicators and strategies
- **System Health Checks**: Robust system diagnostics and dependency verification
- **Beautiful Console UI**: Rich console output with tables, progress bars, and color-coded information
- **Error Handling**: Comprehensive error handling and user feedback
- **Type Safety**: Full type hints and Pydantic-based configuration management

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/crypto-price-tracker.git
cd crypto-price-tracker
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### System Health Check
Run a comprehensive system check to verify all dependencies and connections:
```bash
python app.py --check
```

### Live Price Monitoring
Start real-time price monitoring for supported cryptocurrencies:
```bash
python app.py --liveprice
```

### Technical Analysis
Run technical analysis with various options:

```bash
# One-time analysis
python app.py --analysis

# Auto-refresh every 5 seconds
python app.py --analysis 5

# Different cryptocurrency
python app.py --analysis --symbol ETHUSD

# Custom timeframe and refresh
python app.py --analysis 10 --symbol ETHUSD --resolution 1h

# More historical data
python app.py --analysis --days 30

# Save analysis results to MongoDB
python app.py --analysis --save

# Auto-refresh with MongoDB saving
python app.py --analysis 5 --save
```

### Command Line Options
- `--check`: Run system diagnostics
- `--liveprice`: Start live price monitoring
- `--analysis [SECONDS]`: Run technical analysis with optional refresh interval
- `--symbol SYMBOL`: Trading pair (default: BTCUSD)
- `--resolution TIMEFRAME`: Time resolution (1m, 5m, 15m, 1h, 1d)
- `--days DAYS`: Historical data days (default: 10)
- `--save`: Save analysis results to MongoDB database with timestamp

## Project Structure

```
├── app.py                  # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md              # Documentation
└── src/
    ├── config.py          # Configuration management
    ├── data/
    │   ├── websocket_client.py    # WebSocket implementation
    │   └── technical_analysis.py  # Technical analysis engine
    ├── system/
    │   └── health_checker.py      # System diagnostics
    └── ui/
        └── console.py             # Console UI components
```

## Technical Indicators

The application includes the following technical indicators:
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- ATR (Average True Range)
- Stochastic Oscillator
- VWAP (Volume Weighted Average Price)

## Trading Strategies

Built-in trading strategies include:
- Trend Following
- Mean Reversion
- Volatility Breakout
- Volume Analysis

## Configuration

The application uses Pydantic-settings for configuration management. You can override default settings using environment variables prefixed with `CRYPTO_`. For example:

```bash
export CRYPTO_WEBSOCKET_URL="wss://your-custom-websocket-server"
export CRYPTO_PRICE_UPDATE_INTERVAL=10
export CRYPTO_MONGODB_URL="mongodb://localhost:27017"
export CRYPTO_MONGODB_DATABASE="crypto_analysis"
```

### MongoDB Setup

For saving analysis results to MongoDB:

1. Install MongoDB on your system
2. Start MongoDB service:
   ```bash
   # Linux/macOS
   sudo systemctl start mongod
   
   # Windows
   net start MongoDB
   ```
3. Use `--save` flag with `--analysis` to enable saving

## Development

### Code Style
The project uses:
- Black for code formatting
- Flake8 for linting
- MyPy for type checking

### Running Tests
```bash
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 