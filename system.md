# Professional Algorithmic Trading System v2.0.0

## System Architecture Overview

This document provides a comprehensive guide to understanding the trading system architecture, components, and flow.

## Core Configuration

### Trading Parameters
- **Initial Balance**: $10,000
- **Risk Per Trade**: 2% of balance
- **Stop Loss**: 5% from entry price
- **Target Profit**: 10% from entry price
- **Min Confidence**: 50% for trade execution
- **Daily Trade Limit**: 50 trades

### System Intervals
- **Strategy Execution**: Every 10 minutes (600s)
- **Historical Data Update**: Every 15 minutes (900s) via httpx
- **Risk Check**: Every 1 minute (60s)
- **Live Price Updates**: Real-time via WebSocket

## File Structure & Components

### 1. Entry Point
**`main.py`**
- Application entry point with argument parsing
- System startup with professional status display
- Shows all important configs on startup
- Graceful shutdown handling
- Health check capabilities

**Key Features:**
- Displays strategy execution intervals
- Shows active strategies and trading symbols
- Professional system banner with all configs
- Email notification on startup

### 2. Core Trading Engine
**`src/core/trading_system.py`**
- Main trading system orchestrator
- Manages all system components
- Handles WebSocket live price updates
- Coordinates strategy execution every 10 minutes
- Real-time position and account monitoring

**Process Flow:**
1. Initialize all components (broker, risk manager, strategies)
2. Start WebSocket server for frontend
3. Connect to live price feeds
4. Start background threads:
   - Strategy execution (10-minute intervals)
   - System monitoring (1-minute intervals)
5. Process live price updates and broadcast to frontend
6. Execute trades based on strategy signals

### 3. Configuration Management
**`src/config.py`**
- Simplified Pydantic settings
- Environment variable loading
- Removed unnecessary duplicate configs
- Clean separation of concerns

**Key Functions:**
- `get_settings()`: Main settings singleton
- `get_trading_config()`: Trading parameters
- `get_system_intervals()`: Timing configurations
- `get_fastapi_mail_config()`: Email settings

### 4. Trading Broker
**`src/broker/paper_broker.py`**
- Paper trading implementation
- Position management
- Account balance tracking
- Trade execution logic
- Uses simplified trading_config

**Core Functions:**
- `execute_trade_async()`: Execute trades
- `get_account_summary_async()`: Account status
- `get_positions_summary_async()`: Open positions
- `update_prices_async()`: Live price updates

### 5. Historical Data Provider
**`src/broker/historical_data.py`**
- httpx-based API calls to Delta Exchange
- Automatic 15-minute data refresh
- Thread-safe caching system
- Data quality checks and logging

**Data Flow:**
1. Fetch OHLCV data from Delta Exchange API
2. Cache data with configurable expiry
3. Auto-refresh every 15 minutes in background thread
4. Provide data to strategies for analysis

### 6. Strategy Management
**`src/strategies/strategy_manager.py`**
- Parallel strategy execution
- EMAStrategy implementation
- Performance tracking
- Signal generation and selection

**Execution Flow:**
1. Every 10 minutes, process all trading symbols
2. Execute all strategies in parallel
3. Select best signal based on confidence
4. Send signal to trading engine
5. Track strategy performance

### 7. Risk Management
**`src/services/risk_manager.py`**
- Position monitoring
- Portfolio risk analysis
- Stop loss and target management
- Uses simplified risk_per_trade config

**Risk Controls:**
- Max 2% risk per trade
- 15% max portfolio risk
- Automatic stop loss at 5%
- Target profit at 10%

### 8. Live Market Data
**`src/services/live_price_ws.py`**
- Real-time WebSocket connection to market data
- Price update callbacks
- Connection management and reconnection
- Performance statistics

### 9. Notifications
**`src/services/notifications.py`**
- Email notifications via FastAPI-Mail
- System startup/shutdown alerts
- Trade execution notifications
- Risk alerts

### 10. WebSocket Server
**`src/api/websocket_server.py`**
- Real-time frontend communication
- Account and position broadcasts
- System status updates
- Strategy signal distribution

### 11. Database
**`src/database/mongodb_client.py`** & **`src/database/schemas.py`**
- MongoDB integration
- Data persistence
- Schema definitions
- Async operations

## System Flow

### Startup Sequence
1. **Configuration Loading**: Load simplified configs
2. **Component Initialization**: Initialize broker, risk manager, strategies
3. **WebSocket Setup**: Start server for frontend communication
4. **Live Data Connection**: Connect to market data WebSocket
5. **Background Threads**: Start strategy and monitoring threads
6. **Email Notification**: Send startup confirmation
7. **Main Loop**: Begin continuous operation

### Runtime Operation
1. **Live Price Updates**: 
   - Receive real-time prices via WebSocket
   - Update broker prices
   - Broadcast to frontend
   - Check positions and risk

2. **Strategy Execution** (Every 10 minutes):
   - Process all trading symbols
   - Execute strategies in parallel
   - Generate trading signals
   - Execute trades if signals are valid

3. **Historical Data Updates** (Every 15 minutes):
   - Fetch latest OHLCV data via httpx
   - Update cached data
   - Ensure strategies have fresh data

4. **Risk Monitoring** (Every 1 minute):
   - Check all open positions
   - Monitor stop loss and targets
   - Calculate portfolio risk
   - Take corrective actions if needed

5. **System Monitoring** (Every 1 minute):
   - Check component health
   - Log system statistics
   - Broadcast status to frontend
   - Perform maintenance tasks

## Key Optimizations

1. **Simplified Configuration**: Removed duplicate and unnecessary configs
2. **Configurable Intervals**: Strategy (10min), Historical Data (15min), Risk (1min)
3. **Real-time Updates**: Live price feeds with immediate frontend broadcasts
4. **Thread Safety**: Proper locking for shared data structures
5. **Error Handling**: Circuit breakers and graceful degradation
6. **Performance Monitoring**: Detailed logging and statistics
7. **Memory Management**: Garbage collection and cache management

## Monitoring & Logs

### Startup Logs Show:
- System configuration summary
- Trading parameters
- Active strategies
- Trading symbols
- System intervals
- Component status

### Runtime Logs Include:
- Strategy execution results
- Trade executions
- Risk actions
- System performance
- Error tracking
- WebSocket activity

## Frontend Integration

The system provides real-time data to the frontend via WebSocket:
- Live price updates
- Account balance changes
- Position updates
- Strategy signals
- System status
- Notifications

This creates a professional trading environment with full visibility into system operation and performance.