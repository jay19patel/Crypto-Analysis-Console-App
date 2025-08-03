# Trading System Architecture & Flow Documentation

## Overview
This document provides a comprehensive overview of the Professional Algorithmic Trading System's architecture, components, and data flow.

## System Architecture

### Core Components

1. **Trading System Core** (`src/core/trading_system.py`)
   - Main orchestrator of all system components
   - Manages startup/shutdown sequences
   - Coordinates between all subsystems
   - Handles error management and health monitoring

2. **Broker System** (`src/broker/paper_broker.py`)
   - Simulates trading operations (paper trading)
   - Manages positions and account state
   - Calculates P&L and account metrics
   - Handles trade execution and position management

3. **Strategy Manager** (`src/strategies/strategy_manager.py`)
   - Executes trading strategies in parallel
   - Manages strategy lifecycle and signal generation
   - Coordinates multiple strategy instances
   - Handles strategy-specific configuration

4. **WebSocket Server** (`src/api/websocket_server.py`)
   - Real-time communication with frontend dashboard
   - Broadcasts live prices, positions, and notifications
   - Manages client connections and subscriptions
   - Handles real-time data streaming

5. **REST API Server** (`src/api/rest_server.py`)
   - Provides HTTP endpoints for dashboard data
   - Serves historical data, analytics, and reports
   - Handles dashboard web interface
   - Manages data filtering and pagination

6. **Notification System** (`src/services/notifications.py`)
   - Sends email notifications for trading events
   - Manages notification templates and formatting
   - Handles system startup/shutdown notifications
   - Provides real-time notification broadcasting

## System Flow

### 1. System Startup Sequence

```
1. Configuration Loading
   ├── Load .env settings
   ├── Initialize trading parameters
   └── Set up logging configuration

2. Component Initialization
   ├── MongoDB Client Setup
   ├── Broker Initialization
   ├── Strategy Manager Setup
   ├── WebSocket Server Creation
   ├── REST API Server Setup
   └── Notification Manager Initialization

3. Service Startup
   ├── Start WebSocket Server (Port 8765)
   ├── Start REST API Server (Port 8766)
   ├── Connect to Live Price WebSocket
   ├── Start async components (broker, risk manager, notifications)
   └── Start background threads (strategy execution, monitoring)

4. System Ready
   ├── Send startup notification email
   ├── Broadcast system status to WebSocket clients
   └── Begin main monitoring loop
```

### 2. Trading Loop Flow

```
Strategy Execution Loop (Every 5 minutes):
1. Get Market Data
   ├── Fetch live prices from WebSocket
   ├── Validate data availability
   └── Update current market data cache

2. Strategy Processing
   ├── Execute all strategies in parallel
   ├── Generate trading signals with confidence scores
   ├── Filter signals by confidence threshold (>= 70%)
   └── Select best signal per symbol

3. Trade Execution
   ├── Check existing positions (max 1 per symbol)
   ├── Validate account balance and limits
   ├── Execute trade through broker
   ├── Update position tracking
   └── Send trade notifications

4. Real-time Updates
   ├── Broadcast position updates to WebSocket clients
   ├── Update account summary
   ├── Send live notifications
   └── Update dashboard data
```

### 3. Data Flow Architecture

```
Live Price Data Flow:
WebSocket Price Feed → Market Data Cache → Strategy Execution → Trading Signals

Position Data Flow:
Trade Execution → Broker Position Update → MongoDB Storage → Dashboard Updates

Notification Flow:
Trading Events → Notification Manager → Email Sending + WebSocket Broadcast

Dashboard Data Flow:
REST API Requests → MongoDB Queries → Data Enhancement → JSON Response
WebSocket Subscriptions → Real-time Broadcasts → Frontend Updates
```

### 4. Component Communication

#### WebSocket Channels
- `live_prices`: Real-time price updates
- `positions`: Open position updates  
- `closed_position_update`: Closed position notifications
- `notifications`: System and trading notifications
- `strategy_signals`: Trading signal broadcasts
- `account_summary`: Account balance and metrics
- `system_status`: System health and uptime data
- `heartbeat`: Connection health monitoring

#### REST API Endpoints
- `/api/positions/open`: Get all open positions
- `/api/positions/closed`: Get closed positions with filtering
- `/api/trades`: Get trade history with pagination
- `/api/notifications`: Get notification history
- `/api/signals`: Get strategy signal history
- `/api/analytics/summary`: Get trading analytics

### 5. Database Schema

#### Collections
1. **positions**: Trading position records
   - Fields: id, symbol, position_type, entry_price, exit_price, quantity, pnl, etc.
   - Indexes: status, symbol, entry_time, exit_time

2. **notifications**: System notification logs
   - Fields: id, type, level, message, timestamp, data
   - Indexes: timestamp, level, type

3. **signals**: Strategy signal history
   - Fields: strategy_name, symbol, signal, confidence, price, timestamp
   - Indexes: timestamp, symbol, strategy_name

4. **websocket_clients**: Connected client tracking
   - Fields: client_id, ip_address, connected_at, status
   - Indexes: client_id, connected_at

### 6. Strategy System

#### Strategy Execution Process
```
1. Market Data Input
   ├── Price: Current market price
   ├── Volume: Trading volume data
   ├── Timestamp: Data timestamp
   └── Symbol: Trading pair identifier

2. Strategy Analysis
   ├── Technical indicators calculation
   ├── Pattern recognition
   ├── Risk assessment
   └── Signal generation

3. Signal Output
   ├── Signal Type: BUY/SELL
   ├── Confidence: 0-100% confidence score
   ├── Price: Recommended execution price
   └── Metadata: Strategy-specific data
```

#### Strategy Types
- **Moving Average Strategy**: Based on MA crossovers
- **RSI Strategy**: Relative Strength Index signals
- **Bollinger Bands Strategy**: Price channel breakouts
- **MACD Strategy**: Moving Average Convergence Divergence

### 7. Risk Management

#### Position Limits
- Maximum 1 position per symbol
- Daily trade limit: 50 trades
- Stop loss: 2% of position value
- Take profit: 3% of position value

#### Account Protection
- Balance validation before trades
- Margin requirement checks
- Leverage limits (max 5x)
- Trading fee calculations

### 8. Monitoring & Health Checks

#### Health Check Components
- MongoDB connectivity
- WebSocket server status
- Live price feed connection
- Strategy execution status
- Memory usage monitoring
- Error count tracking

#### System Metrics
- Uptime tracking
- Trade execution statistics
- Win rate calculations
- Account growth monitoring
- System resource usage

### 9. Shutdown Sequence

```
1. Signal Reception (Ctrl+C)
   ├── Set shutdown event
   ├── Stop new trade executions
   └── Initiate graceful shutdown

2. Component Shutdown
   ├── Stop strategy execution loop
   ├── Stop monitoring threads
   ├── Close WebSocket connections
   ├── Stop REST API server
   └── Disconnect from live price feed

3. Data Persistence
   ├── Save final account state
   ├── Update position statuses
   ├── Store final statistics
   └── Send shutdown notification email

4. Cleanup
   ├── Cancel pending async tasks
   ├── Close database connections
   ├── Stop all background threads
   └── Exit application
```

### 10. Error Handling

#### Error Categories
- **Network Errors**: WebSocket disconnections, API failures
- **Trading Errors**: Insufficient balance, invalid symbols
- **Strategy Errors**: Calculation failures, data issues
- **System Errors**: Database failures, memory issues

#### Error Response
- Automatic retry mechanisms for transient failures
- Error logging with detailed stack traces
- Email notifications for critical errors
- Graceful degradation for non-critical failures

### 11. Configuration Management

#### Environment Variables (.env)
- Database connection settings
- Email configuration
- Trading parameters
- System intervals and timeouts

#### Trading Configuration
- Balance per trade percentage
- Leverage settings
- Stop loss and take profit levels
- Confidence thresholds

### 12. Frontend Dashboard Integration

#### Real-time Features
- Live price displays with color-coded changes
- Position tracking with P&L updates
- System status monitoring
- Notification streaming

#### Data Views
- Account summary with growth metrics
- Position history with filtering
- Trade analytics and statistics
- System health dashboard

## Performance Considerations

### Optimization Strategies
- Parallel strategy execution
- Efficient database queries with proper indexing
- WebSocket connection pooling
- Memory usage monitoring and cleanup
- Asynchronous operations for I/O bound tasks

### Scalability
- Modular component architecture
- Configurable worker thread pools
- Database sharding capability
- Load balancing for multiple instances

## Security Features

### Data Protection
- Environment variable configuration
- Secure WebSocket connections
- Input validation and sanitization
- Error message sanitization

### Access Control
- Client connection limits
- Rate limiting for API requests
- IP-based connection tracking
- Session management

## Maintenance & Operations

### Logging
- Structured logging with levels (DEBUG, INFO, WARNING, ERROR)
- Separate log files for different components
- Log rotation and retention policies
- Performance metrics logging

### Backup & Recovery
- Automated database backups
- Configuration file versioning
- Position state recovery
- Error state recovery procedures

---

This documentation provides a comprehensive overview of the trading system's architecture and operation. For specific implementation details, refer to the individual component source files.