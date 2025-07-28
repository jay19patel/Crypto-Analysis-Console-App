# Professional Algorithmic Trading System v2.1.0 - Complete System Guide

## System Architecture Overview

This document provides a comprehensive guide to understanding the Professional Trading System architecture, components, functions, calculations, and complete workflow. The system is designed for algorithmic trading with real-time price feeds, risk management, and comprehensive email notifications.

## Core Configuration & Trading Parameters

### Financial Configuration
- **Initial Balance**: $10,000 (configurable via INITIAL_BALANCE)
- **Risk Per Trade**: 2% of balance (RISK_PER_TRADE = 0.02)
- **Stop Loss**: 5% from entry price (STOP_LOSS_PCT = 0.05)
- **Target Profit**: 10% from entry price (TARGET_PCT = 0.10)
- **Min Confidence**: 50% for trade execution (MIN_CONFIDENCE = 50.0)
- **Daily Trade Limit**: 50 trades per day (DAILY_TRADES_LIMIT = 50)

### Leverage & Margin Settings
- **Default Leverage**: 1x (DEFAULT_LEVERAGE = 1.0)
- **Maximum Leverage**: 5x (MAX_LEVERAGE = 5.0)
- **Maximum Position Size**: $1,000 (MAX_POSITION_SIZE = 1000.0)
- **Maximum Portfolio Risk**: 15% (MAX_PORTFOLIO_RISK = 0.15)

### Fee Structure
- **Trading Fee**: 0.1% of margin (TRADING_FEE_PCT = 0.001)
- **Exit Fee Multiplier**: 50% of entry fee (EXIT_FEE_MULTIPLIER = 0.5)

### System Intervals
- **Strategy Execution**: Every 10 minutes (STRATEGY_EXECUTION_INTERVAL = 600s)
- **Historical Data Update**: Every 15 minutes (HISTORICAL_DATA_UPDATE_INTERVAL = 900s)
- **Risk Check**: Every 1 minute (RISK_CHECK_INTERVAL = 60s)
- **Live Price Updates**: Real-time via WebSocket (LIVE_PRICE_UPDATE = "realtime")

### Active Configuration
- **Strategies**: EMAStrategy (STRATEGY_CLASSES = ["EMAStrategy"])
- **Trading Symbols**: BTCUSD, ETHUSD (TRADING_SYMBOLS = ["BTCUSD", "ETHUSD"])
- **WebSocket Port**: 8765 (WEBSOCKET_PORT = 8765)

## Complete File Structure & Component Functions

### 1. Entry Point & System Orchestration
**`main.py`** - Main application entry point
- **Purpose**: System startup, configuration display, graceful shutdown
- **Key Functions**:
  - `main()`: Application entry point with argument parsing
  - System banner display with all configurations
  - Graceful shutdown handling with signal management
  - Health check capabilities

**`run.py`** - Alternative entry point
- **Purpose**: Simple system launcher
- **Key Functions**:
  - Direct system startup without argument parsing
  - Quick development testing

**Key Features:**
- Professional system banner showing all configurations
- Email notification on startup with complete system status
- Signal handling for graceful shutdown (SIGINT, SIGTERM)
- Command-line arguments: `--delete-data`, `--emailoff`, `--port`

### 2. Core Trading Engine
**`src/core/trading_system.py`** - Main trading system orchestrator
- **Purpose**: Central system coordination, component management, trade execution
- **Key Functions**:
  - `__init__()`: Initialize all system components with circuit breakers
  - `start()`: Start all components, threads, and establish connections
  - `stop()`: Graceful shutdown with comprehensive statistics email
  - `_on_live_price_update()`: Process real-time price updates with error handling
  - `_strategy_execution_loop()`: Execute strategies every 10 minutes
  - `_monitoring_loop()`: System health monitoring every minute
  - `_execute_signal()`: Execute trading signals with risk validation
  - `_execute_strategies_for_symbol()`: Run parallel strategy execution per symbol
  - `get_system_stats()`: Comprehensive system performance metrics
  - `get_health_status()`: Current system health assessment

**Core Classes**:
- `TradingSystem`: Main system class with all components
- `SystemHealth`: Health status data structure
- `CircuitBreaker`: Resilience pattern for component failures

**Process Flow:**
1. **Initialization**: Initialize broker, risk manager, strategies, notification system
2. **WebSocket Setup**: Start server for real-time frontend communication
3. **Live Data Connection**: Connect to market data WebSocket feeds
4. **Background Threads**: Start strategy execution and monitoring threads
5. **Price Processing**: Real-time price updates with PnL calculations
6. **Trade Execution**: Signal validation, risk checks, and position management
7. **System Monitoring**: Health checks, statistics, and maintenance tasks

**`src/core/email_formatter.py`** - Centralized email template system
- **Purpose**: Professional email formatting for all trading notifications
- **Key Functions**:
  - `format_trade_execution_email()`: Detailed trade execution notifications
  - `format_position_exit_email()`: Comprehensive position closure emails
  - `format_risk_alert_email()`: Risk management alert formatting
  - `format_system_error_email()`: System error notifications
  - `format_system_startup_email()`: System startup with configuration
  - `format_system_shutdown_email()`: System shutdown with final statistics

**Data Classes**:
- `TradeExecutionData`: Complete trade execution information
- `PositionExitData`: Comprehensive position exit details
- `EmailTemplate`: Email template enumeration

### 3. Configuration Management
**`src/config.py`** - Centralized configuration system
- **Purpose**: Application settings, environment variables, trading parameters
- **Key Functions**:
  - `get_settings()`: Main settings singleton with all configurations
  - `get_trading_config()`: Trading parameters (balance, risk, leverage, fees)
  - `get_system_intervals()`: Timing configurations for all system processes
  - `get_fastapi_mail_config()`: Email SMTP configuration for notifications

**Settings Class** (`Settings`):
- **Database**: MongoDB URI, database name, timeout settings
- **Trading**: Initial balance, risk per trade, stop loss, target profit
- **Leverage**: Default and maximum leverage, position size limits
- **Risk Management**: Portfolio risk limits, margin requirements
- **Fees**: Trading fees, exit fee multipliers
- **System Intervals**: Strategy execution, data updates, risk checks
- **WebSocket**: Port configuration, timeout settings
- **Email**: FastAPI-Mail configuration for notifications
- **Strategies**: Active strategy classes and trading symbols
- **Logging**: Log level configuration

**Environment Integration**:
- Loads from `.env` file automatically
- Case-insensitive environment variable mapping
- Proper type validation and defaults

### 4. Trading Broker System
**`src/broker/paper_broker.py`** - Paper trading execution engine
- **Purpose**: Trade execution, position management, account tracking, risk validation
- **Key Functions**:
  - `start()`: Initialize account and load existing positions from MongoDB
  - `execute_trade_async()`: Execute trades with comprehensive validation and fees
  - `close_position_async()`: Close positions with PnL calculation and notifications
  - `get_account_summary_async()`: Real-time account status with live PnL
  - `get_positions_summary_async()`: Enhanced position data with current prices
  - `update_prices_async()`: Process live price updates and calculate PnL
  - `has_open_position_for_symbol()`: Check for existing positions (one per symbol rule)
  - `get_open_position_for_symbol()`: Retrieve specific symbol position
  - `delete_all_data()`: Complete data reset functionality
  - `_validate_trade_request()`: Trade request validation (price, quantity, confidence)
  - `_check_risk_limits()`: Risk management checks (balance, limits, existing positions)
  - `_execute_trade_simple()`: Core trade execution with margin and fee calculations

**Core Classes**:
- `AsyncBroker`: Main broker class with MongoDB persistence
- `TradeRequest`: Trade execution request with comprehensive data
- `ExecutionStatus`: Trade execution status tracking

**Trade Execution Process**:
1. **Validation**: Signal type, price, quantity, confidence level checks
2. **Risk Checks**: Daily limits, position size, existing positions, balance
3. **Quantity Calculation**: Risk manager calculates safe quantity with leverage
4. **Fee Calculation**: Entry fee based on margin used
5. **Position Creation**: Create position with stop-loss and take-profit levels
6. **Account Update**: Deduct margin and fees from balance
7. **Persistence**: Save position and account to MongoDB
8. **Notification**: Send detailed execution email with all metrics

**`src/broker/models.py`** - Data models and schemas
- **Purpose**: Define trading data structures, enums, and validation
- **Key Classes**:
  - `Account`: Trading account with balance, statistics, limits
  - `Position`: Trading position with entry/exit, PnL, leverage details
  - `PositionType`: LONG/SHORT enumeration
  - `PositionStatus`: OPEN/CLOSED/PENDING status tracking

**Position Management**:
- **One Position Per Symbol Rule**: Enforced at trade execution
- **Real-time PnL**: Continuous calculation with live prices
- **Stop-Loss & Take-Profit**: Automatic level calculation based on config
- **Leverage Support**: Full leverage calculation with margin requirements
- **Fee Tracking**: Entry and exit fees with multiplier support

### 5. Historical Data Provider
**`src/broker/historical_data.py`** - Market data collection and caching
- **Purpose**: Fetch, cache, and provide historical market data for strategy analysis
- **Key Functions**:
  - `get_historical_data()`: Fetch OHLCV data with caching and error handling
  - `start_background_updates()`: Auto-refresh data every 15 minutes
  - `stop_background_updates()`: Clean shutdown of background threads
  - `_fetch_data_from_api()`: Direct API calls to Delta Exchange
  - `_is_cache_valid()`: Cache expiry validation
  - `_start_update_thread()`: Background thread management

**Core Classes**:
- `HistoricalDataProvider`: Main data provider with httpx client
- Thread-safe caching with configurable expiry times
- Automatic retry mechanism with exponential backoff

**Data Flow Process**:
1. **Strategy Request**: Strategy requests historical data for analysis
2. **Cache Check**: Validate if cached data is still fresh (15-minute expiry)
3. **API Fetch**: If cache expired, fetch new data from Delta Exchange API
4. **Data Validation**: Verify data quality and completeness
5. **Cache Update**: Store fresh data with timestamp for future requests
6. **Background Refresh**: Automatic 15-minute refresh cycle
7. **Error Handling**: Graceful fallback to cached data on API failures

**API Integration**:
- Delta Exchange REST API for OHLCV data
- httpx async client for high-performance requests
- Rate limiting and respectful API usage
- Comprehensive error handling and logging

### 6. Strategy Management System
**`src/strategies/strategy_manager.py`** - Strategy execution and coordination
- **Purpose**: Manage multiple trading strategies, parallel execution, signal selection
- **Key Functions**:
  - `add_default_strategies()`: Initialize strategies for all trading symbols
  - `execute_strategies_parallel()`: Run all strategies concurrently with ThreadPoolExecutor
  - `get_all_symbols()`: Retrieve all configured trading symbols
  - `get_strategy_stats()`: Individual strategy performance metrics
  - `get_manager_stats()`: Overall strategy manager statistics
  - `shutdown()`: Clean shutdown of all strategy threads and resources

**Core Classes**:
- `StrategyManager`: Main coordinator with thread pool management
- `StrategyExecutionResult`: Result container with strategy performance data
- `ParallelStrategyResult`: Combined results from all strategies

**Strategy Execution Flow** (Every 10 minutes):
1. **Symbol Processing**: Iterate through all configured trading symbols
2. **Parallel Execution**: Run all strategies simultaneously using ThreadPoolExecutor
3. **Market Data**: Provide current market data and historical data to each strategy
4. **Signal Generation**: Each strategy analyzes data and generates signals
5. **Signal Selection**: Choose best signal based on confidence level and strategy performance
6. **Performance Tracking**: Record execution time, success rate, and signal quality
7. **Result Delivery**: Send selected signal to trading system for execution

**`src/strategies/base_strategy.py`** - Strategy base class and interface
- **Purpose**: Define standard interface for all trading strategies
- **Key Functions**:
  - `analyze()`: Abstract method for strategy analysis implementation
  - `get_strategy_name()`: Strategy identification
  - `get_performance_stats()`: Strategy-specific performance metrics

**`src/strategies/strategies.py`** - Individual strategy implementations
- **Purpose**: Concrete trading strategy implementations
- **EMAStrategy Functions**:
  - `analyze()`: Exponential Moving Average crossover analysis
  - `_calculate_ema()`: EMA calculation with configurable periods
  - `_generate_signal()`: Signal generation based on EMA crossover
  - `_calculate_confidence()`: Dynamic confidence scoring based on market conditions

**Strategy Performance Tracking**:
- **Success Rate**: Percentage of profitable signals
- **Average Confidence**: Mean confidence level of generated signals
- **Execution Time**: Strategy analysis performance metrics
- **Signal Distribution**: BUY/SELL/WAIT signal frequency
- **Risk-Adjusted Returns**: Performance relative to risk taken

### 7. Risk Management System
**`src/services/risk_manager.py`** - Comprehensive risk monitoring and control
- **Purpose**: Portfolio risk assessment, position monitoring, safe quantity calculation
- **Key Functions**:
  - `start()`: Initialize risk management with broker connection
  - `calculate_safe_quantity_async()`: Calculate safe trade quantity based on risk parameters
  - `monitor_positions_async()`: Monitor all positions for stop-loss and take-profit
  - `analyze_portfolio_risk_async()`: Comprehensive portfolio risk assessment
  - `check_margin_requirements()`: Validate margin availability and usage
  - `get_risk_metrics()`: Current risk exposure metrics
  - `_calculate_position_risk()`: Individual position risk assessment
  - `_check_correlation_risk()`: Asset correlation analysis for diversification

**Core Classes**:
- `AsyncRiskManager`: Main risk management coordinator
- `RiskMetrics`: Risk measurement data structure
- `PortfolioRisk`: Portfolio-level risk assessment

**Risk Control Mechanisms**:
1. **Trade-Level Risk**:
   - Maximum 2% of account balance per trade
   - Position size limits based on available capital
   - Leverage restrictions based on volatility
   - Confidence-based quantity adjustment

2. **Portfolio-Level Risk**:
   - Maximum 15% total portfolio risk exposure
   - Correlation analysis between positions
   - Diversification requirements
   - Margin usage monitoring

3. **Position Monitoring**:
   - Real-time stop-loss monitoring (5% default)
   - Take-profit level tracking (10% default)
   - Automatic position closure on risk thresholds
   - Margin call prevention

**Safe Quantity Calculation Process**:
1. **Available Capital**: Calculate free capital after existing positions
2. **Risk Allocation**: Apply 2% risk limit to available capital
3. **Price Impact**: Consider potential slippage and market impact
4. **Leverage Adjustment**: Apply leverage multiplier with safety margins
5. **Position Size Validation**: Ensure within maximum position limits
6. **Final Adjustment**: Reduce quantity if any limits are exceeded

**Risk Alerts and Actions**:
- **High Risk**: Email alerts when portfolio risk > 12%
- **Critical Risk**: Automatic position reduction when risk > 15%
- **Margin Warning**: Alerts when margin usage > 70%
- **Correlation Risk**: Warnings for over-concentrated positions

### 8. Live Market Data System
**`src/services/live_price_ws.py`** - Real-time price feed management
- **Purpose**: WebSocket connection to market data, real-time price distribution
- **Key Functions**:
  - `start()`: Establish WebSocket connection to Delta Exchange
  - `stop()`: Clean shutdown with connection termination
  - `_on_message()`: Process incoming price messages and distribute to callbacks
  - `_on_error()`: Error handling with automatic reconnection
  - `_on_close()`: Connection close handling and reconnection logic
  - `get_performance_stats()`: Connection statistics and performance metrics
  - `is_connected`: Connection status property

**Core Classes**:
- `RealTimeMarketData`: Main WebSocket manager with callback system
- Thread-safe message processing with error handling
- Automatic reconnection with exponential backoff

**Price Update Flow**:
1. **WebSocket Connection**: Connect to Delta Exchange live price feed
2. **Message Reception**: Receive JSON price updates in real-time
3. **Data Parsing**: Parse and validate price data structure
4. **Callback Distribution**: Send updates to registered callbacks (trading system)
5. **Error Handling**: Automatic reconnection on connection failures
6. **Performance Tracking**: Monitor connection stability and message rates

**Features**:
- **Auto-Reconnection**: Automatic reconnection with exponential backoff
- **Performance Monitoring**: Connection uptime, message rates, error tracking
- **Thread Safety**: Safe concurrent access to price data
- **Error Recovery**: Graceful handling of network issues and API changes

### 9. Advanced Notification System
**`src/services/notifications.py`** - Comprehensive email notification system
- **Purpose**: Professional email notifications, event tracking, async delivery
- **Key Functions**:
  - `start()`: Initialize notification system with email configuration
  - `send_notification()`: Queue notifications for async processing
  - `notify_trade_execution()`: Enhanced trade execution emails with detailed metrics
  - `notify_position_close()`: Comprehensive position exit emails with PnL analysis
  - `notify_risk_alert()`: Risk management alerts with detailed risk metrics
  - `notify_system_startup()`: System startup emails with complete configuration
  - `notify_system_shutdown()`: Shutdown emails with final statistics
  - `test_email_connection()`: Email configuration validation

**Core Classes**:
- `NotificationManager`: Main notification coordinator with async queue
- `EmailNotifier`: Email delivery system using FastAPI-Mail and EmailFormatter
- `NotificationEvent`: Structured notification data container
- `NotificationType`: Comprehensive notification type enumeration

**Email Notification Types**:
1. **Trade Execution Emails**:
   - Complete trade details (symbol, price, quantity, leverage)
   - Margin and capital information
   - Account balance before/after trade
   - Risk metrics and fee breakdown
   - Strategy and confidence information

2. **Position Exit Emails**:
   - Entry/exit price analysis
   - Comprehensive PnL breakdown (gross, net, percentage)
   - Account growth metrics
   - Portfolio performance impact
   - Fee analysis and total costs

3. **Risk Alert Emails**:
   - Risk level assessment and warnings
   - Portfolio exposure analysis
   - Recommended actions
   - Position-specific risk metrics

4. **System Emails**:
   - Startup: Complete system configuration, account status
   - Shutdown: Final statistics, session summary, performance metrics

**Notification Processing**:
- **Async Queue**: Non-blocking notification processing
- **Email Formatting**: Professional HTML emails via EmailFormatter
- **Database Logging**: All notifications logged to MongoDB
- **Error Handling**: Retry mechanism with fallback options
- **Performance Tracking**: Delivery statistics and monitoring

### 10. WebSocket Server System
**`src/api/websocket_server.py`** - Real-time frontend communication
- **Purpose**: Provide real-time data to frontend, client management, message broadcasting
- **Key Functions**:
  - `start()`: Start WebSocket server on configured port
  - `stop()`: Graceful server shutdown with client cleanup
  - `register()`: Client connection registration with subscription management
  - `unregister()`: Clean client disconnection handling
  - `broadcast_live_prices()`: Real-time price updates to all clients
  - `broadcast_account_summary()`: Account balance and status updates
  - `broadcast_positions_update()`: Position changes and PnL updates
  - `broadcast_strategy_signal()`: Strategy signals and analysis results
  - `broadcast_notification()`: System notifications and alerts
  - `get_server_stats()`: Server performance and client statistics

**Core Classes**:
- `WebSocketServer`: Main server with client management
- `MessageType`: Message type enumeration for structured communication
- Client subscription management with topic-based filtering

**Real-Time Data Broadcasting**:
1. **Live Prices**: Real-time price updates from market data WebSocket
2. **Account Updates**: Balance changes, margin usage, portfolio value
3. **Position Updates**: Open/closed positions, PnL changes, risk metrics
4. **Strategy Signals**: Strategy analysis results and trading signals
5. **System Notifications**: Alerts, warnings, and system status updates
6. **Performance Metrics**: System health, statistics, and monitoring data

**Client Management**:
- **Connection Handling**: Automatic client registration and cleanup
- **Subscription Management**: Topic-based message filtering
- **Error Handling**: Graceful handling of client disconnections
- **Performance Monitoring**: Client count, message rates, error tracking

### 11. Database System
**`src/database/mongodb_client.py`** - MongoDB integration and persistence
- **Purpose**: Data persistence, async operations, data management
- **Key Functions**:
  - `connect()`: Establish MongoDB connection with error handling
  - `disconnect()`: Clean database disconnection
  - `save_account()`: Persist account data with versioning
  - `load_account()`: Load account data with validation
  - `save_position()`: Store position data with history
  - `load_positions()`: Retrieve all positions with filtering
  - `save_trade()`: Log trade execution details
  - `save_live_price_async()`: Store live price data for analysis
  - `delete_all_data()`: Complete data reset functionality
  - `cleanup_old_data()`: Automated data archival and cleanup

**`src/database/schemas.py`** - Data models and validation
- **Purpose**: Define data structures, validation rules, schema evolution
- **Key Classes**:
  - `Account`: Trading account with balance, statistics, configuration
  - `Position`: Trading positions with entry/exit data, PnL tracking
  - `Trade`: Trade execution records with comprehensive details
  - `MarketData`: Price data structure with validation
  - `TradingSignal`: Strategy signals with metadata
  - `NotificationLog`: Notification history and delivery tracking

**Database Features**:
- **Async Operations**: Non-blocking database operations
- **Data Validation**: Pydantic schema validation for data integrity
- **Error Recovery**: Connection pooling and automatic retry
- **Performance Optimization**: Indexed queries and efficient data storage
- **Data Archival**: Automated cleanup of old data to manage storage

## Complete System Flow & Operation

### Detailed Startup Sequence
1. **Configuration Loading**:
   - Load settings from `.env` file and defaults
   - Validate trading parameters and system intervals
   - Initialize logging and error tracking systems

2. **Component Initialization**:
   - Initialize AsyncBroker with MongoDB connection
   - Setup AsyncRiskManager with portfolio limits
   - Initialize StrategyManager with parallel execution
   - Setup NotificationManager with EmailFormatter
   - Initialize WebSocket server for frontend

3. **Database Setup**:
   - Connect to MongoDB with error handling
   - Load existing account data or create new account
   - Load all open positions from database
   - Initialize data schemas and validation

4. **Market Data Connection**:
   - Establish WebSocket connection to Delta Exchange
   - Setup price update callbacks to trading system
   - Initialize historical data provider with caching
   - Start background data refresh threads

5. **Background Systems**:
   - Start strategy execution thread (10-minute intervals)
   - Start system monitoring thread (1-minute intervals)
   - Start risk monitoring thread (continuous)
   - Initialize WebSocket server for real-time frontend updates

6. **System Validation**:
   - Perform health checks on all components
   - Validate account balance and positions
   - Send comprehensive startup email with configuration
   - Begin main monitoring loop

### Runtime Operation Cycles

#### 1. Live Price Processing (Real-time)
**Flow**: Market Data → Trading System → Risk Updates → Frontend Broadcast

**Process**:
1. Receive real-time price from Delta Exchange WebSocket
2. Update broker price cache with thread safety
3. Calculate live PnL for all open positions using new prices
4. Update risk metrics and margin usage
5. Broadcast price updates to WebSocket clients
6. Trigger position monitoring for stop-loss/take-profit
7. Update account summary with unrealized PnL
8. Log performance metrics and update statistics

#### 2. Strategy Execution Cycle (Every 10 minutes)
**Flow**: Historical Data → Strategy Analysis → Signal Generation → Trade Execution

**Process**:
1. **Data Preparation**:
   - Fetch latest historical data (OHLCV) for all symbols
   - Validate data quality and completeness
   - Provide current market data and historical context

2. **Strategy Analysis**:
   - Execute all strategies in parallel using ThreadPoolExecutor
   - Each strategy analyzes market conditions independently
   - Generate trading signals (BUY/SELL/WAIT) with confidence scores
   - Track strategy execution time and performance

3. **Signal Selection**:
   - Collect all strategy results and signals
   - Select best signal based on confidence level and strategy performance
   - Log strategy performance and signal distribution

4. **Trade Validation & Execution**:
   - Check for existing positions (one position per symbol rule)
   - Validate signal meets minimum confidence threshold
   - Calculate safe quantity using risk manager
   - Execute trade if all validations pass
   - Send detailed execution email with all metrics

#### 3. Historical Data Updates (Every 15 minutes)
**Flow**: API Request → Data Validation → Cache Update → Strategy Notification

**Process**:
1. Check cache expiry for all trading symbols
2. Fetch fresh OHLCV data from Delta Exchange API
3. Validate data integrity and completeness
4. Update cache with new data and timestamp
5. Notify strategies of fresh data availability
6. Log data update statistics and performance

#### 4. Risk Monitoring (Every 1 minute)
**Flow**: Position Analysis → Risk Calculation → Alert Generation → Action Execution

**Process**:
1. **Position Risk Assessment**:
   - Calculate current PnL for all open positions
   - Assess individual position risk exposure
   - Check stop-loss and take-profit levels

2. **Portfolio Risk Analysis**:
   - Calculate total portfolio risk exposure
   - Analyze position correlation and diversification
   - Monitor margin usage and leverage

3. **Risk Actions**:
   - Generate risk alerts if thresholds exceeded
   - Automatically close positions if stop-loss triggered
   - Send risk alert emails for high-risk scenarios
   - Update risk metrics and broadcast to frontend

#### 5. System Health Monitoring (Every 1 minute)
**Flow**: Component Check → Health Assessment → Statistics Update → Frontend Broadcast

**Process**:
1. **Component Health Checks**:
   - Verify broker system functionality
   - Check WebSocket connections (market data and server)
   - Validate database connectivity
   - Monitor thread health and performance

2. **Performance Metrics**:
   - Calculate system uptime and statistics
   - Monitor memory usage and garbage collection
   - Track error rates and system reliability
   - Measure average execution times

3. **System Maintenance**:
   - Perform periodic garbage collection
   - Clean up old data and logs
   - Update performance statistics
   - Broadcast system status to connected clients

## Trade Execution & Calculation Details

### Complete Trade Execution Flow
1. **Signal Reception**: Strategy generates BUY/SELL signal with confidence
2. **Pre-Trade Validation**:
   - Verify signal type and confidence level
   - Check account balance and daily trade limits
   - Ensure no existing position for symbol (one position per symbol rule)

3. **Risk-Based Quantity Calculation**:
   ```python
   # Risk manager calculates safe quantity
   risk_amount = account_balance * 0.02  # 2% risk per trade
   position_value = risk_amount / 0.05   # Based on 5% stop-loss
   base_quantity = position_value / current_price
   leveraged_quantity = base_quantity * leverage
   margin_required = position_value / leverage
   ```

4. **Fee Calculations**:
   ```python
   trading_fee = margin_required * 0.001  # 0.1% of margin
   total_cost = margin_required + trading_fee
   ```

5. **Position Creation**:
   - Create position with entry price, quantity, leverage
   - Set stop-loss and take-profit levels
   - Calculate margin usage and risk metrics

6. **Account Updates**:
   ```python
   new_balance = old_balance - margin_required - trading_fee
   total_margin_used += margin_required
   ```

7. **Notifications & Persistence**:
   - Save position and account to MongoDB
   - Send detailed execution email via EmailFormatter
   - Broadcast updates to WebSocket clients

### Position Exit & PnL Calculation
1. **Exit Trigger**: Stop-loss, take-profit, or manual closure
2. **PnL Calculation**:
   ```python
   # For LONG positions
   price_diff = exit_price - entry_price
   gross_pnl = price_diff * quantity * leverage
   
   # For SHORT positions  
   price_diff = entry_price - exit_price
   gross_pnl = price_diff * quantity * leverage
   
   # Net PnL after fees
   exit_fee = trading_fee * 0.5  # 50% of entry fee
   net_pnl = gross_pnl - exit_fee
   ```

3. **Account Updates**:
   ```python
   # Return margin and add/subtract PnL
   new_balance = old_balance + margin_used + net_pnl - exit_fee
   realized_pnl += net_pnl
   total_margin_used -= margin_used
   ```

4. **Performance Tracking**:
   - Update win/loss statistics
   - Calculate win rate and average returns
   - Track strategy performance metrics
   - Update portfolio statistics

5. **Comprehensive Notifications**:
   - Send detailed exit email with PnL analysis
   - Include account growth metrics
   - Show portfolio impact and performance
   - Broadcast updates to all connected clients

## Email Notification System

### Enhanced Email Features
The system now includes a centralized EmailFormatter class that provides professional, detailed email notifications:

#### Trade Execution Emails Include:
- **Trade Details**: Symbol, signal, price, quantity, strategy, confidence
- **Leverage Information**: Leverage used, margin required, leveraged exposure
- **Account Impact**: Balance before/after, capital remaining, available for trading
- **Risk Metrics**: Stop-loss level, take-profit level, risk/reward ratio, maximum risk/reward
- **Fee Breakdown**: Trading fee, total cost, margin percentage of account

#### Position Exit Emails Include:
- **Position Summary**: Entry/exit prices, position type, duration, quantity, leverage
- **PnL Analysis**: Gross PnL, net PnL, PnL percentage, ROI on margin
- **Account Growth**: Balance change, growth percentage, portfolio impact
- **Fee Analysis**: Entry fee, exit fee, total fees, net PnL after fees
- **Performance Metrics**: Trade outcome, risk-reward achieved, capital efficiency
- **Portfolio Overview**: Total portfolio PnL, win rate, account growth

#### System Status Emails Include:
- **Startup**: Complete system configuration, trading parameters, active strategies, account summary
- **Shutdown**: Final statistics, session duration, trade summary, account performance

## Performance & Monitoring

### Key Performance Metrics
- **Trade Execution Speed**: Average time from signal to execution
- **Strategy Performance**: Individual strategy success rates and confidence levels
- **System Uptime**: Continuous operation monitoring with error tracking
- **WebSocket Performance**: Connection stability and message processing rates
- **Database Performance**: Query times and connection health
- **Memory Management**: Garbage collection and resource usage optimization

### Error Handling & Recovery
- **Circuit Breaker Pattern**: Prevents cascade failures in components
- **Automatic Reconnection**: WebSocket and database connection recovery
- **Data Persistence**: All critical data saved to MongoDB for recovery
- **Graceful Degradation**: System continues operating with reduced functionality
- **Comprehensive Logging**: Detailed error tracking and performance monitoring

This Professional Trading System provides a complete, robust, and scalable solution for algorithmic trading with comprehensive risk management, real-time monitoring, and professional-grade notifications.

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