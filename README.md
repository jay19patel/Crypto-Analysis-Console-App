# Crypto Price Tracker

A console-based cryptocurrency price tracking application that monitors BTC and ETH prices in real-time using WebSocket connections to Delta Exchange.

## Features

- ✅ **System Health Checks**: Verify dependencies and connectivity before running
- 📊 **Real-time Price Updates**: Get BTC and ETH prices every 10 seconds
- 🎨 **Colorful Console Interface**: Beautiful, colorized output for better readability
- 📈 **Progress Bars**: Visual feedback during system initialization
- 🔧 **Dependency Management**: Automatic checking of required packages
- 🌐 **Connectivity Testing**: Verify internet and WebSocket server connectivity

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

### Start Price Monitoring
Once system check passes, start the full application:
```bash
python main.py --full
```

This will:
- Show initialization progress bars
- Connect to Delta Exchange WebSocket
- Display price updates every 10 seconds
- Continue until you press Ctrl+C

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

- `websocket-client`: WebSocket connectivity
- `tqdm`: Progress bars
- `colorama`: Colored console output
- `requests`: HTTP requests (for system checks)

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

✅ Ready to run! Use '--full' to start the application.
```

### Full Application (`--full`)
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

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Python Version Issues**
   - Requires Python 3.7 or higher
   - Check with: `python --version`

3. **Connection Issues**
   - Verify internet connectivity
   - Check firewall settings
   - Ensure WebSocket ports are not blocked

4. **Windows-specific Issues**
   - Run PowerShell as Administrator if needed
   - Ensure colorama is installed for proper color output

## License

This project is for educational and personal use only.

## Support

If you encounter any issues:
1. Run `python main.py --check` to diagnose problems
2. Ensure all dependencies are installed
3. Verify internet connectivity
4. Check that the WebSocket server is accessible 