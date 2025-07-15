# MongoDB Integration and Configuration System Guide

## Overview

This guide explains the new MongoDB integration and configuration system that has been implemented to replace static values with a proper Pydantic-based configuration system and async MongoDB persistence using motor.

## Key Features

### 1. Configuration System (`src/config.py`)

The new configuration system uses Pydantic settings to manage all application parameters:

#### Database Settings
- `MONGODB_URI`: MongoDB connection string (default: `mongodb://localhost:27017`)
- `DATABASE_NAME`: Database name (default: `trading_system`)
- `MONGODB_TIMEOUT`: Connection timeout in seconds (default: 5)

#### Broker Settings
- `BROKER_INITIAL_BALANCE`: Initial account balance (default: $10,000)
- `BROKER_MAX_LEVERAGE`: Maximum leverage allowed (default: 5.0)
- `BROKER_TRADING_FEE_PCT`: Trading fee percentage (default: 0.1%)
- `BROKER_MIN_CONFIDENCE`: Minimum confidence for trade execution (default: 50%)
- `BROKER_STOP_LOSS_PCT`: Default stop loss percentage (default: 5%)
- `BROKER_TARGET_PCT`: Default target percentage (default: 10%)
- `BROKER_MAX_HOLDING_HOURS`: Maximum position holding time (default: 48 hours)

#### Risk Management Settings
- `RISK_MAX_PORTFOLIO_RISK`: Maximum portfolio risk (default: 15%)
- `RISK_MAX_POSITION_RISK`: Maximum position risk (default: 5%)
- `RISK_CORRELATION_THRESHOLD`: Correlation threshold (default: 0.7)
- `RISK_CHECK_INTERVAL`: Risk check interval in seconds (default: 5)

#### Trading Settings
- `DAILY_TRADES_LIMIT`: Daily trade limit (default: 50)
- `MAX_POSITION_SIZE`: Maximum position size (default: $1,000)
- `RISK_PER_TRADE`: Risk per trade (default: 2%)

#### Dummy Data Settings
- `DUMMY_SYMBOLS`: List of trading symbols for dummy data
- `DUMMY_PRICE_CHANGE_RANGE`: Price change range for dummy data (default: ±2%)
- `TRADING_LOOP_INTERVAL`: Trading loop interval in seconds (default: 5)

### 2. Async MongoDB Client (`src/mongodb_client.py`)

The new async MongoDB client uses motor for non-blocking database operations:

#### Key Features
- **Async Operations**: All database operations are async/await
- **Connection Management**: Automatic connection handling with retry logic
- **Index Creation**: Automatic index creation for performance
- **Data Persistence**: Account and position data stored in MongoDB
- **Error Handling**: Comprehensive error handling and logging

#### Collections
- `accounts`: Single account document (singleton pattern)
- `positions`: All trading positions
- `trades`: Trade execution history
- `analysis`: Analysis results and reports

#### Key Methods
```python
# Account Management
await mongodb_client.save_account(account_data)
await mongodb_client.load_account(account_id)

# Position Management
await mongodb_client.save_position(position_data)
await mongodb_client.load_positions(status)
await mongodb_client.delete_position(position_id)

# Data Deletion
await mongodb_client.delete_all_data()
await mongodb_client.delete_collection(collection_name)
```

### 3. Updated Broker System (`src/async_broker.py`)

The broker now integrates with MongoDB for data persistence:

#### Key Changes
- **MongoDB Integration**: All account and position data persisted to MongoDB
- **Config-Based Settings**: Uses configuration values instead of hardcoded values
- **Async Operations**: All operations are async/await
- **Data Recovery**: Loads existing data on startup
- **Data Deletion**: Supports complete data cleanup

#### Account Management
- Account is created as singleton in MongoDB
- Account data loaded on startup
- Account statistics updated after each trade
- Account data persisted after every change

#### Position Management
- Positions stored in MongoDB with full history
- Position PnL calculated and updated in real-time
- Position status tracking (OPEN/CLOSED)
- Position risk metrics stored

### 4. Updated Risk Manager (`src/async_risk_manager.py`)

The risk manager now uses configuration-based thresholds:

#### Key Changes
- **Config-Based Thresholds**: All risk thresholds from configuration
- **Async Operations**: All risk analysis is async
- **MongoDB Integration**: Risk metrics stored in database
- **Real-Time Monitoring**: Continuous position monitoring

#### Risk Analysis
- Portfolio risk analysis with configurable thresholds
- Position-level risk analysis
- Real-time risk monitoring
- Automated risk management actions

### 5. Updated Main System (`run_high_speed_trading.py`)

The main system now supports:

#### New Features
- **--delete Flag**: Delete all trading data from database
- **Config Integration**: Uses configuration for all settings
- **MongoDB Status**: Shows MongoDB connection status
- **Data Persistence**: All data automatically persisted

#### Usage Examples
```bash
# Run normal trading system
python run_high_speed_trading.py

# Delete all data and exit
python run_high_speed_trading.py --delete
```

## Configuration Management

### Environment Variables

You can override any configuration value using environment variables:

```bash
# Database settings
export MONGODB_URI="mongodb://localhost:27017"
export DATABASE_NAME="my_trading_system"

# Broker settings
export BROKER_INITIAL_BALANCE="20000.0"
export BROKER_MAX_LEVERAGE="3.0"
export BROKER_TRADING_FEE_PCT="0.002"

# Risk settings
export RISK_MAX_PORTFOLIO_RISK="0.10"
export RISK_MAX_POSITION_RISK="0.03"
```

### .env File

Create a `.env` file in the project root to set configuration values:

```env
# Database Configuration
MONGODB_URI=mongodb://localhost:27017
DATABASE_NAME=trading_system
MONGODB_TIMEOUT=5

# Broker Configuration
BROKER_INITIAL_BALANCE=15000.0
BROKER_MAX_LEVERAGE=4.0
BROKER_TRADING_FEE_PCT=0.0015
BROKER_MIN_CONFIDENCE=60.0
BROKER_STOP_LOSS_PCT=0.04
BROKER_TARGET_PCT=0.12
BROKER_MAX_HOLDING_HOURS=36

# Risk Management
RISK_MAX_PORTFOLIO_RISK=0.12
RISK_MAX_POSITION_RISK=0.04
RISK_CORRELATION_THRESHOLD=0.75
RISK_CHECK_INTERVAL=3

# Trading Limits
DAILY_TRADES_LIMIT=30
MAX_POSITION_SIZE=800.0
RISK_PER_TRADE=0.015

# Dummy Data
DUMMY_SYMBOLS=["BTC-USD", "ETH-USD", "AAPL", "GOOGL", "TSLA", "MSFT"]
DUMMY_PRICE_CHANGE_RANGE=0.015
TRADING_LOOP_INTERVAL=3
```

## MongoDB Setup

### Local MongoDB Installation

1. **Install MongoDB Community Edition**:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install mongodb

   # macOS
   brew install mongodb-community

   # Windows
   # Download from https://www.mongodb.com/try/download/community
   ```

2. **Start MongoDB Service**:
   ```bash
   # Ubuntu/Debian
   sudo systemctl start mongodb

   # macOS
   brew services start mongodb-community

   # Windows
   # Start MongoDB service from Services
   ```

3. **Verify Connection**:
   ```bash
   # Test connection
   mongo --eval "db.runCommand('ping')"
   ```

### MongoDB Atlas (Cloud)

For cloud-based MongoDB:

1. **Create Atlas Account**: Sign up at https://www.mongodb.com/atlas
2. **Create Cluster**: Set up a free cluster
3. **Get Connection String**: Copy the connection string
4. **Update Configuration**:
   ```env
   MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/trading_system
   ```

## Testing the System

### Run Integration Tests

```bash
# Test MongoDB integration and config system
python test_mongodb_integration.py
```

### Test Individual Components

```bash
# Test config system
python -c "from src.config import get_settings; print(get_settings())"

# Test MongoDB connection
python -c "import asyncio; from src.mongodb_client import AsyncMongoDBClient; asyncio.run(AsyncMongoDBClient().connect())"
```

### Manual Testing

1. **Start Trading System**:
   ```bash
   python run_high_speed_trading.py
   ```

2. **Check MongoDB Data**:
   ```bash
   # Connect to MongoDB
   mongo trading_system

   # View collections
   show collections

   # View account data
   db.accounts.find()

   # View positions
   db.positions.find()

   # View trades
   db.trades.find()
   ```

3. **Delete All Data**:
   ```bash
   python run_high_speed_trading.py --delete
   ```

## Data Structure

### Account Document
```json
{
  "_id": "ObjectId",
  "id": "main",
  "name": "Trading Account Main",
  "initial_balance": 10000.0,
  "current_balance": 9850.0,
  "total_trades": 15,
  "profitable_trades": 10,
  "losing_trades": 5,
  "win_rate": 66.67,
  "total_profit": 500.0,
  "total_loss": 200.0,
  "daily_trades_count": 3,
  "daily_trades_limit": 50,
  "total_margin_used": 2000.0,
  "brokerage_charges": 15.0,
  "last_trade_date": "2024-01-15",
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### Position Document
```json
{
  "_id": "ObjectId",
  "id": "uuid-string",
  "symbol": "BTC-USD",
  "position_type": "LONG",
  "status": "OPEN",
  "entry_price": 50000.0,
  "exit_price": null,
  "quantity": 0.1,
  "invested_amount": 5000.0,
  "strategy_name": "Demo Strategy",
  "leverage": 1.0,
  "margin_used": 5000.0,
  "trading_fee": 5.0,
  "stop_loss": 47500.0,
  "target": 55000.0,
  "pnl": 200.0,
  "pnl_percentage": 4.0,
  "entry_time": "2024-01-15T09:00:00Z",
  "exit_time": null,
  "notes": null,
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### Trade Document
```json
{
  "_id": "ObjectId",
  "id": "uuid-string",
  "symbol": "BTC-USD",
  "signal": "BUY",
  "price": 50000.0,
  "quantity": 0.1,
  "leverage": 1.0,
  "strategy_name": "Demo Strategy",
  "confidence": 85.0,
  "timestamp": "2024-01-15T09:00:00Z",
  "status": "completed",
  "error_message": null,
  "position_id": "uuid-string"
}
```

## Performance Considerations

### MongoDB Optimization

1. **Indexes**: Automatic index creation for performance
2. **Connection Pooling**: Motor handles connection pooling
3. **Async Operations**: Non-blocking database operations
4. **Batch Operations**: Efficient bulk operations

### Memory Management

1. **Data Loading**: Only load necessary data on startup
2. **Cache Management**: In-memory cache for frequently accessed data
3. **Cleanup**: Automatic cleanup of old data
4. **Connection Management**: Proper connection lifecycle management

## Error Handling

### MongoDB Connection Errors

The system handles MongoDB connection failures gracefully:

1. **Fallback Mode**: Uses in-memory storage if MongoDB unavailable
2. **Retry Logic**: Automatic retry for connection issues
3. **Error Logging**: Comprehensive error logging
4. **Graceful Degradation**: System continues with reduced functionality

### Data Validation

1. **Pydantic Validation**: All data validated using Pydantic models
2. **Type Safety**: Strong typing throughout the system
3. **Error Recovery**: Automatic error recovery mechanisms
4. **Data Integrity**: Checksums and validation for data integrity

## Security Considerations

### MongoDB Security

1. **Authentication**: Use MongoDB authentication
2. **Network Security**: Restrict network access
3. **Data Encryption**: Enable data encryption at rest
4. **Access Control**: Implement proper access controls

### Application Security

1. **Input Validation**: All inputs validated
2. **Error Handling**: Secure error handling
3. **Logging**: Secure logging practices
4. **Configuration**: Secure configuration management

## Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**:
   - Check MongoDB service is running
   - Verify connection string
   - Check network connectivity

2. **Configuration Errors**:
   - Verify .env file format
   - Check environment variables
   - Validate configuration values

3. **Data Persistence Issues**:
   - Check MongoDB permissions
   - Verify database exists
   - Check disk space

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Health Checks

Run health checks:

```bash
# Test MongoDB connection
python test_mongodb_integration.py

# Check system status
python run_high_speed_trading.py --status
```

## Migration Guide

### From Previous Version

1. **Backup Data**: Backup any existing data
2. **Install Dependencies**: Install motor and pydantic-settings
3. **Update Configuration**: Create .env file with settings
4. **Test System**: Run integration tests
5. **Migrate Data**: Import existing data if needed

### Dependencies

Add to requirements.txt:
```
motor>=3.0.0
pydantic-settings>=2.0.0
```

## Conclusion

The new MongoDB integration and configuration system provides:

1. **Flexibility**: Easy configuration management
2. **Scalability**: Async operations for better performance
3. **Reliability**: Robust error handling and recovery
4. **Maintainability**: Clean separation of concerns
5. **Testability**: Comprehensive testing framework

This system is production-ready and can handle real trading scenarios with proper data persistence and configuration management. 