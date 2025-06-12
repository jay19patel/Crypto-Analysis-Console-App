# Crypto Price Tracker & Technical Analysis

A comprehensive console-based cryptocurrency application featuring real-time price monitoring via WebSocket and advanced technical analysis with beautiful visualizations.

## Features

### 🔗 WebSocket Price Monitoring
- ✅ **System Health Checks**: Verify dependencies and connectivity before running
- 📊 **Real-time Price Updates**: Get BTC and ETH prices every 10 seconds
- 🎨 **Colorful Console Interface**: Beautiful, colorized output for better readability
- 📈 **Progress Bars**: Visual feedback during system initialization
- 🔧 **Dependency Management**: Automatic checking of required packages
- 🌐 **Connectivity Testing**: Verify internet and WebSocket server connectivity

### 📊 Technical Analysis Module
- 🎯 **Advanced Indicators**: EMA, RSI, MACD, Supertrend, ADX, VWAP, Z-Score, ATR
- 🎨 **Beautiful Rich Display**: Color-coded signals with emoji indicators
- 🔄 **Auto-refresh**: Continuously update analysis with customizable intervals
- 📈 **Multiple Symbols**: Support for various cryptocurrency pairs (BTCUSD, ETHUSD, etc.)
- ⏰ **Multiple Timeframes**: 1m, 5m, 15m, 1h, 1d
- 📱 **Live Analysis**: Real-time market sentiment with buy/sell signals

## Installation

1. **Clone or download this project**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### System Check
Run this first to verify everything is working properly:
```bash
python main.py --check
```

This will check:
- Python version compatibility
- Required dependencies installation
- Internet connectivity
- WebSocket server accessibility
- Pip functionality

### WebSocket Price Monitoring
Start real-time price monitoring:
```bash
python main.py --full
```

This will:
- Show initialization progress bars
- Connect to Delta Exchange WebSocket
- Display price updates every 10 seconds
- Continue until you press Ctrl+C

### Technical Analysis
Run comprehensive technical analysis:

```bash
# One-time analysis
python main.py --analysis

# Auto-refresh every 5 seconds
python main.py --analysis 5

# Different cryptocurrency
python main.py --analysis --symbol ETHUSD

# Custom timeframe and refresh
python main.py --analysis 10 --symbol ETHUSD --resolution 1h

# More historical data
python main.py --analysis --days 30
```

#### Technical Analysis Options:
- `--analysis [SECONDS]`: Run analysis (optional refresh interval)
- `--symbol SYMBOL`: Trading pair (BTCUSD, ETHUSD, ADAUSD, etc.)
- `--resolution TIMEFRAME`: 1m, 5m, 15m, 1h, 1d
- `--days DAYS`: Historical data days (default: 10)

### Help
```bash
python main.py --help
```

## Project Structure

```
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── src/
    ├── __init__.py        # Package initialization
    ├── websocket_client.py # WebSocket client implementation
    └── system_checker.py   # System diagnostics module
```

## Dependencies

### Core Dependencies
- `websocket-client`: WebSocket connectivity
- `tqdm`: Progress bars
- `colorama`: Colored console output
- `requests`: HTTP requests (for system checks)

### Technical Analysis Dependencies
- `httpx`: HTTP client for API requests
- `pandas`: Data manipulation and analysis
- `pandas-ta`: Technical analysis indicators
- `numpy`: Numerical computations
- `rich`: Beautiful console formatting

## Sample Output

### System Check (`--check`)
```
╔══════════════════════════════════════════════════════════════╗
║                    Crypto Price Tracker                     ║
║                   WebSocket-based Monitor                   ║
╚══════════════════════════════════════════════════════════════╝

Running system diagnostics...

============================================================
System Health Check
============================================================

Checking Python version...
  ✓ Python 3.9.7 - Compatible

Checking pip installation...
  ✓ pip - Working properly

Checking dependencies...
  ✓ websocket - Installed
  ✓ tqdm - Installed
  ✓ colorama - Installed
  ✓ requests - Installed

  ✓ All dependencies are installed!

Checking internet connectivity...
  ✓ Internet connection - Available

Checking WebSocket server connectivity...
  ✓ WebSocket server - Reachable

============================================================
Check Summary
============================================================
  Python Version: PASS
  Pip Installation: PASS
  Dependencies: PASS
  Internet Connectivity: PASS
  WebSocket Server: PASS

Overall: 5/5 checks passed
🎉 System is ready to run!

✅ Ready to run! Use '--full' for WebSocket or '--analysis' for technical analysis.
```

### WebSocket Price Monitoring (`--full`)
```
╔══════════════════════════════════════════════════════════════╗
║                    Crypto Price Tracker                     ║
║                   WebSocket-based Monitor                   ║
╚══════════════════════════════════════════════════════════════╝

Initializing Crypto Price Tracker...

Checking system requirements: 100%|████████████| 100/100
[System check output...]

Initializing WebSocket client: 100%|████████████| 100/100

Establishing WebSocket connection: 100%|████████████| 100/100

🚀 System setup complete! Starting price monitoring...
📊 Price updates will appear every 10 seconds
Press Ctrl+C to stop the application

Socket opened successfully!
Subscribed to BTC and ETH price feeds

==================================================
Price Update - 2024-01-15 14:30:45
==================================================
BTCUSD: $42,350.25 (updated 2s ago)
ETHUSD: $2,580.75 (updated 1s ago)
==================================================
```

### Technical Analysis (`--analysis`)
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                           📊 TECHNICAL ANALYSIS DASHBOARD                   ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

╭─────────────────────────────────────────────────────────────────────────╮
│ 📈 Market Data    │ 💰 Value                │ 📊 Status               │
├─────────────────────────────────────────────────────────────────────────┤
│ 💵 Current Price  │ 43250.5000               │ 📈 +125.50 (+0.29%)    │
│ 📅 Last Update    │ 2024-01-15 14:30:00      │ 🔄 Live                │
│ 📊 Volume         │ 1,234,567                │ 📦 Active              │
│ 🎯 High           │ 43500.0000               │ ⬆️                     │
│ 🎯 Low            │ 43000.0000               │ ⬇️                     │
╰─────────────────────────────────────────────────────────────────────────╯

╭── 🔍 Technical Indicators Analysis ──────────────────────────────────────╮
│ Indicator  │ Value    │ Signal              │ Interpretation        │
├────────────┼──────────┼─────────────────────┼──────────────────────┤
│ 📊 RSI_14  │ 45.67    │ ⚪ Normal           │ Neutral               │
│ 🎯 MACD    │ 25.34    │ 📈 Bullish         │ Uptrend               │
│ ⚡ Supertrend │ 1     │ 🟢 UPTREND         │ Buy Zone              │
│ 💎 VWAP    │ 43180.25 │ 📈 Above VWAP      │ Bullish               │
│ 🎪 ADX     │ 28.45    │ Strong 📈 Uptrend  │ Bullish               │
╰────────────┴──────────┴─────────────────────┴──────────────────────╯

⏰ Analysis generated at: 2024-01-15 14:30:00 IST
```

## Technical Analysis Features

### 📊 Supported Indicators
- **EMA (Exponential Moving Average)**: 5, 15, 50 periods
- **RSI (Relative Strength Index)**: Overbought/Oversold signals
- **MACD**: Trend direction and momentum
- **Supertrend**: Buy/Sell zone identification  
- **ADX**: Trend strength analysis
- **VWAP**: Volume-weighted price levels
- **Z-Score**: Statistical overbought/oversold conditions
- **ATR**: Volatility measurement

### 🎯 Signal Interpretation
- **🟢 Green**: Bullish signals (Buy zone)
- **🔴 Red**: Bearish signals (Sell zone)  
- **🟡 Yellow**: Neutral/Warning zones
- **⚪ White**: Normal range

### 💱 Supported Symbols
- BTCUSD, ETHUSD, ADAUSD, DOTUSD
- SOLUSD, MATICUSD, AVAXUSD
- And many more crypto pairs

## Demo & Testing

Run the interactive demo to explore features:
```bash
python demo_analysis.py
```

The demo includes:
- System check walkthrough
- Live technical analysis demo
- Command examples
- Interactive feature testing

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Python Version Issues**
   - Requires Python 3.7 or higher
   - Check with: `python --version`

3. **Technical Analysis Import Errors**
   - Install pandas-ta: `pip install pandas-ta`
   - Install rich: `pip install rich`
   - Install httpx: `pip install httpx`

4. **Connection Issues**
   - Verify internet connectivity
   - Check firewall settings
   - Ensure WebSocket ports are not blocked

5. **Windows-specific Issues**
   - Run PowerShell as Administrator if needed
   - Ensure colorama is installed for proper color output

6. **API Rate Limiting**
   - Avoid very short refresh intervals (< 3 seconds)
   - Check Delta Exchange API status

## License

This project is for educational and personal use only.

## Support

If you encounter any issues:
1. Run `python main.py --check` to diagnose problems
2. Ensure all dependencies are installed
3. Verify internet connectivity
4. Check that the WebSocket server is accessible 