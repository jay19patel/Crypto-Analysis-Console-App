# Trading System Calculations & Workflow Notes

## Overview
This document provides comprehensive information about trade calculations, system workflow, warning systems, quantity calculations, and all core trading logic used in the Professional Trading System.

## Table of Contents
1. [Trade Execution Workflow](#trade-execution-workflow)
2. [Quantity Calculations](#quantity-calculations)
3. [Leverage & Margin Calculations](#leverage--margin-calculations)
4. [Risk Management Calculations](#risk-management-calculations)
5. [PnL Calculations](#pnl-calculations)
6. [Warning Systems](#warning-systems)
7. [Fee Calculations](#fee-calculations)
8. [Position Management](#position-management)
9. [Email Notification Details](#email-notification-details)
10. [System Configuration](#system-configuration)

---

## Trade Execution Workflow

### 1. Signal Generation
- **Location**: `src/strategies/strategy_manager.py`
- **Process**: Strategies analyze market data and generate trading signals
- **Signal Types**: BUY, SELL, WAIT
- **Confidence Threshold**: Minimum 50% confidence required (configurable)

```python
# Signal validation process:
if signal.confidence < MIN_CONFIDENCE:
    signal = WAIT  # Signal rejected due to low confidence
```

### 2. Pre-Trade Validation
- **Location**: `src/broker/paper_broker.py` - `_validate_trade_request()`
- **Checks**:
  - Signal type (must be BUY or SELL)
  - Price > 0
  - Quantity > 0
  - Confidence >= minimum threshold
  - Symbol validation

### 3. Risk Management Validation
- **Location**: `src/broker/paper_broker.py` - `_check_risk_limits()`
- **Checks**:
  - Daily trade limit not exceeded
  - Position size within limits
  - No existing position for symbol (ONE POSITION PER SYMBOL RULE)
  - Sufficient account balance

### 4. Quantity Calculation (Risk Manager)
- **Location**: `src/services/risk_manager.py` - `calculate_safe_quantity_async()`
- **Process**: Calculates safe quantity based on risk parameters
- **Factors Considered**:
  - Available balance
  - Risk per trade percentage
  - Leverage multiplier
  - Position size limits

---

## Quantity Calculations

### Base Quantity Formula
```python
# Risk-based quantity calculation
risk_amount = account_balance * risk_per_trade_percentage
position_value = risk_amount / stop_loss_percentage
base_quantity = position_value / current_price

# With leverage
leveraged_quantity = base_quantity * leverage
```

### Safe Quantity Calculation Process
1. **Calculate Risk Amount**:
   ```python
   max_risk = account_balance * 0.02  # 2% risk per trade
   ```

2. **Calculate Position Value**:
   ```python
   position_value = max_risk / stop_loss_pct  # e.g., max_risk / 0.05
   ```

3. **Calculate Base Quantity**:
   ```python
   quantity = position_value / current_price
   ```

4. **Apply Leverage**:
   ```python
   leveraged_quantity = quantity * leverage
   margin_required = position_value / leverage
   ```

5. **Validate Against Limits**:
   ```python
   if margin_required > available_balance:
       quantity = (available_balance * leverage) / current_price
   ```

### Quantity Warnings
- **Insufficient Balance**: Quantity reduced to maximum affordable
- **Position Size Limit**: Quantity capped at maximum position size
- **Leverage Limit**: Leverage reduced if exceeds maximum allowed

---

## Leverage & Margin Calculations

### Margin Calculation
```python
position_value = price * quantity
margin_required = position_value / leverage

# Example:
# Price: $50,000, Quantity: 0.1, Leverage: 5x
# Position Value: $5,000
# Margin Required: $1,000
```

### Leverage Limits
- **Default Leverage**: 1x (configurable)
- **Maximum Leverage**: 5x (configurable)
- **Dynamic Adjustment**: System reduces leverage if risk is too high

### Margin Usage Percentage
```python
margin_usage_pct = (total_margin_used / account_balance) * 100

# Warning levels:
# 50-70%: Medium risk
# 70-85%: High risk
# 85%+: Critical risk (margin call warning)
```

---

## Risk Management Calculations

### Portfolio Risk Assessment
1. **Individual Position Risk**:
   ```python
   position_risk = (margin_used * stop_loss_pct) / account_balance
   ```

2. **Total Portfolio Risk**:
   ```python
   total_risk = sum(position_risk for all open positions)
   max_portfolio_risk = 15%  # Configurable limit
   ```

3. **Risk Score Calculation**:
   ```python
   risk_score = (total_risk / max_portfolio_risk) * 100
   # 0-50%: Low risk
   # 50-75%: Medium risk
   # 75-90%: High risk
   # 90%+: Critical risk
   ```

### Safe Quantity Reduction Scenarios
1. **Account Balance Check**:
   - If `margin_required + trading_fee > available_balance`
   - Reduce quantity to fit available balance

2. **Position Size Limit**:
   - If `position_value > max_position_size`
   - Reduce quantity proportionally

3. **Daily Trade Limit**:
   - If daily trades >= limit, reject trade
   - Reset counter at midnight UTC

---

## PnL Calculations

### Unrealized PnL (Open Positions)
```python
# For LONG positions
unrealized_pnl = (current_price - entry_price) * quantity * leverage

# For SHORT positions  
unrealized_pnl = (entry_price - current_price) * quantity * leverage

# PnL Percentage
pnl_percentage = (unrealized_pnl / margin_used) * 100
```

### Realized PnL (Closed Positions)
```python
# Calculate at position close
realized_pnl = unrealized_pnl_at_close - total_fees

# Update account balance
new_balance = old_balance + margin_used + realized_pnl - exit_fees
```

### Account Growth Calculation
```python
# After position close
account_growth = new_balance - old_balance
growth_percentage = (account_growth / old_balance) * 100

# Total portfolio PnL
total_pnl = realized_pnl + sum(unrealized_pnl for open positions)
```

---

## Warning Systems

### Trade Warnings (When Generated)

#### 1. Buy Signal Warnings
- **Insufficient Balance**: When margin + fees > available balance
- **Position Exists**: When trying to open second position for same symbol
- **Low Confidence**: When signal confidence < minimum threshold
- **Risk Limit**: When position would exceed portfolio risk limits

#### 2. Sell Signal Warnings
- **No Position**: When trying to sell without open position
- **Insufficient Quantity**: When trying to sell more than owned
- **Market Closed**: During non-trading hours (if applicable)

#### 3. Risk Management Warnings
- **High Margin Usage**: When margin usage > 70%
- **Portfolio Risk**: When total risk > 12%
- **Daily Limit**: When approaching daily trade limit
- **Leverage Warning**: When leverage > 3x for volatile assets

### Warning Delivery Methods
1. **Email Notifications**: High priority warnings
2. **WebSocket Broadcasts**: Real-time warnings to frontend
3. **Log Entries**: All warnings logged with severity levels
4. **Database Records**: Warning history maintained

---

## Fee Calculations

### Trading Fees Structure
```python
# Entry fee (paid when opening position)
entry_fee = margin_used * trading_fee_pct  # Default: 0.1% of margin

# Exit fee (paid when closing position)
exit_fee = entry_fee * exit_fee_multiplier  # Default: 50% of entry fee

# Total fees per trade
total_fees = entry_fee + exit_fee
```

### Fee Impact on PnL
```python
# Net PnL calculation
gross_pnl = (exit_price - entry_price) * quantity * leverage
net_pnl = gross_pnl - total_fees

# Account balance update
final_balance = initial_balance + margin_used + net_pnl
```

---

## Position Management

### Position Lifecycle
1. **Creation**: When trade is executed
2. **Monitoring**: Continuous PnL updates with live prices
3. **Risk Checks**: Automatic stop-loss and take-profit monitoring
4. **Closure**: Manual or automatic position closure

### Position Status Types
- **OPEN**: Active position with live PnL tracking
- **CLOSED**: Completed position with realized PnL
- **PENDING**: Position being processed
- **FAILED**: Position creation failed

### Stop-Loss & Take-Profit Levels
```python
# For LONG positions
stop_loss = entry_price * (1 - stop_loss_pct)  # Default: 5% below entry
take_profit = entry_price * (1 + target_pct)   # Default: 10% above entry

# For SHORT positions
stop_loss = entry_price * (1 + stop_loss_pct)  # Default: 5% above entry
take_profit = entry_price * (1 - target_pct)   # Default: 10% below entry
```

### ONE POSITION PER SYMBOL RULE
- **Enforcement**: Before every trade execution
- **Check Location**: `src/broker/paper_broker.py` - `has_open_position_for_symbol()`
- **Reason**: Risk management and position clarity
- **Override**: Not available (hard rule)

---

## Email Notification Details

### Trade Execution Email Content
- **Basic Info**: Symbol, signal, price, quantity
- **Leverage Details**: Leverage used, margin required, exposure
- **Account Impact**: Balance before/after, capital remaining
- **Risk Info**: Stop-loss, take-profit, risk/reward ratio
- **Fees**: Trading fees, total cost

### Position Exit Email Content
- **Position Summary**: Entry/exit prices, duration, type
- **PnL Analysis**: Gross/net PnL, percentage return, ROI
- **Account Growth**: Balance change, growth percentage
- **Performance**: Win rate, total portfolio PnL
- **Fees**: Entry fee, exit fee, total fees paid

### Risk Alert Email Content
- **Alert Details**: Risk type, severity level, affected positions
- **Current Status**: Account balance, margin usage, open positions
- **Recommendations**: Suggested actions to reduce risk
- **Portfolio Overview**: Total risk, diversification status

---

## System Configuration

### Key Configuration Parameters (Updated for Small Balance Trading)
```python
# Trading Configuration (src/config.py)
INITIAL_BALANCE = 100.0                 # Starting account balance (Small balance)
BALANCE_PER_TRADE_PCT = 0.20           # 20% per trade (Normal mode)
SAFE_BALANCE_PER_TRADE_PCT = 0.05      # 5% per trade (Safe mode - auto for ≤₹1000)
STOP_LOSS_PCT = 0.05                   # 5% stop loss
TARGET_PCT = 0.10                      # 10% take profit
DAILY_TRADES_LIMIT = 50                # Max trades per day
MIN_CONFIDENCE = 50.0                  # Minimum signal confidence
DEFAULT_LEVERAGE = 50.0                # 50x leverage for crypto futures
MAX_LEVERAGE = 50.0                    # Maximum leverage allowed
LIQUIDATION_BUFFER_PCT = 0.30          # 30% buffer from liquidation
MAX_POSITIONS_OPEN = 3                 # Max 3 positions simultaneously
TRADING_FEE_PCT = 0.001                # 0.1% trading fee

# EMERGENCY CLOSE THRESHOLDS (Configurable via .env)
EMERGENCY_CLOSE_MARGIN_PCT = 95.0      # Emergency close at 95% margin usage
EMERGENCY_CLOSE_LOSS_PCT = 15.0        # Emergency close at 15% loss
EMERGENCY_CLOSE_TIME_HOURS = 48.0      # Emergency close after 48 hours

# RISK LEVEL THRESHOLDS (All Configurable)
# Critical Risk
CRITICAL_RISK_MARGIN_PCT = 90.0        # Critical at 90% margin
CRITICAL_RISK_LOSS_PCT = 12.0          # Critical at 12% loss
CRITICAL_RISK_TIME_HOURS = 36.0        # Critical after 36 hours

# High Risk  
HIGH_RISK_MARGIN_PCT = 80.0            # High risk at 80% margin
HIGH_RISK_LOSS_PCT = 8.0               # High risk at 8% loss
HIGH_RISK_TIME_HOURS = 24.0            # High risk after 24 hours

# Medium Risk
MEDIUM_RISK_MARGIN_PCT = 70.0          # Medium risk at 70% margin
MEDIUM_RISK_LOSS_PCT = 5.0             # Medium risk at 5% loss
MEDIUM_RISK_TIME_HOURS = 12.0          # Medium risk after 12 hours
```

### System Intervals
```python
STRATEGY_EXECUTION_INTERVAL = 600    # 10 minutes between strategy runs
HISTORICAL_DATA_UPDATE = 900         # 15 minutes data refresh
RISK_CHECK_INTERVAL = 60            # 1 minute risk checks
LIVE_PRICE_UPDATE = "realtime"      # Real-time price updates
```

### Email Configuration
```python
EMAIL_NOTIFICATIONS_ENABLED = True
FASTAPI_MAIL_SERVER = "smtp.gmail.com"
FASTAPI_MAIL_PORT = 587
FASTAPI_MAIL_STARTTLS = True
# Credentials loaded from environment variables
```

---

## Calculation Examples

### Example 1: BTC Long Position (Small Balance - Safe Mode)
```
Signal: BUY BTCUSD
Price: $50,000 (₹42,00,000)
Account Balance: ₹100
Risk per Trade: 5% (Safe Mode) = ₹5
Leverage: 50x
SAFE MODE ACTIVATED: Balance ≤ ₹1000

Calculations:
1. Balance per Trade: ₹100 * 0.05 = ₹5 (Safe Mode)
2. Position Value: ₹5 * 50 = ₹250
3. Quantity: ₹250 / ₹42,00,000 = 0.0000595 BTC
4. Margin Required: ₹5
5. Trading Fee: ₹5 * 0.001 = ₹0.005
6. Total Cost: ₹5 + ₹0.005 = ₹5.005

Position Details:
- Leveraged Exposure: ₹250
- Margin Used: ₹5
- Remaining Balance: ₹94.995
- Stop Loss Level: ₹39,90,000 (5% below entry)
- Take Profit Level: ₹46,20,000 (10% above entry)
- Emergency Close: Will trigger at 95% margin usage
- Risk Management: Conservative thresholds applied
```

### Example 2: BTC Long Position (Large Balance - Normal Mode)
```
Signal: BUY BTCUSD
Price: $50,000 (₹42,00,000)
Account Balance: ₹10,000
Risk per Trade: 20% (Normal Mode) = ₹2,000
Leverage: 50x

Calculations:
1. Balance per Trade: ₹10,000 * 0.20 = ₹2,000 (Normal Mode)
2. Position Value: ₹2,000 * 50 = ₹1,00,000
3. Quantity: ₹1,00,000 / ₹42,00,000 = 0.00238 BTC
4. Margin Required: ₹2,000
5. Trading Fee: ₹2,000 * 0.001 = ₹2
6. Total Cost: ₹2,000 + ₹2 = ₹2,002

Position Details:
- Leveraged Exposure: ₹1,00,000
- Margin Used: ₹2,000
- Remaining Balance: ₹7,998
- Stop Loss Level: ₹39,90,000 (5% below entry)
- Take Profit Level: ₹46,20,000 (10% above entry)
```

### Example 3: Emergency Close Scenarios (Configurable)

#### Scenario A: Margin Usage Emergency Close
```
Account Balance: ₹100
Position: LONG BTC (₹5 margin, 50x leverage)
Current Position Value: ₹250
Emergency Close Threshold: 95% margin usage (configurable)

Trigger Condition:
- Margin Usage = (₹5 / ₹100) * 100 = 5%
- If BTC drops significantly and margin usage reaches 95%
- System automatically closes position to prevent liquidation

Configuration (in .env):
EMERGENCY_CLOSE_MARGIN_PCT=95.0  # Can be adjusted
```

#### Scenario B: Loss Percentage Emergency Close
```
Account Balance: ₹100
Position: LONG BTC (₹5 margin)
Entry Price: ₹42,00,000
Emergency Close Loss: 15% (configurable)

Trigger Condition:
- Current Loss = 15% of position value
- If BTC drops to ₹35,70,000 (15% drop)
- Position automatically closed

Configuration (in .env):
EMERGENCY_CLOSE_LOSS_PCT=15.0  # Can be adjusted
```

#### Scenario C: Time-Based Emergency Close
```
Position held for: 48 hours (configurable)
Maximum holding time: 48 hours

Trigger Condition:
- Position held longer than configured time limit
- Automatic closure regardless of PnL

Configuration (in .env):
EMERGENCY_CLOSE_TIME_HOURS=48.0  # Can be adjusted
```

### Example 4: Risk Level Thresholds (All Configurable)

#### Low Risk (Green Zone)
```
Margin Usage: <70%
Loss: <5%
Holding Time: <12 hours
Action: Monitor only
```

#### Medium Risk (Yellow Zone)
```
Margin Usage: 70-80%
Loss: 5-8%
Holding Time: 12-24 hours
Action: Close monitoring, consider profit taking
```

#### High Risk (Orange Zone)
```
Margin Usage: 80-90%
Loss: 8-12%
Holding Time: 24-36 hours
Action: Tighten stop-loss, consider position reduction
```

#### Critical Risk (Red Zone)
```
Margin Usage: 90-95%
Loss: 12-15%
Holding Time: 36-48 hours
Action: Close position or reduce size
```

#### Emergency Close (Black Zone)
```
Margin Usage: >95%
Loss: >15%
Holding Time: >48 hours
Action: Immediate position closure
```

### Example 5: Position Exit with Profit
```
Entry: $50,000 (LONG 0.08 BTC)
Exit: $52,000 (4% price increase)
Leverage: 3x

Calculations:
1. Price Change: $52,000 - $50,000 = $2,000
2. Gross PnL: $2,000 * 0.08 * 3 = $480
3. Exit Fee: $1.33 * 0.5 = $0.67
4. Net PnL: $480 - $0.67 = $479.33
5. New Balance: $8,665.34 + $1,333.33 + $479.33 = $10,479.33
6. Account Growth: $479.33 (4.79%)
7. ROI on Margin: $479.33 / $1,333.33 = 35.95%
```

---

## Error Handling & Recovery

### Common Error Scenarios
1. **Insufficient Balance**: Automatic quantity reduction
2. **API Failures**: Retry mechanism with exponential backoff
3. **Price Data Issues**: Fallback to cached prices
4. **Database Errors**: Graceful degradation to in-memory storage
5. **Email Failures**: Queue notifications for retry

### Recovery Mechanisms
- **Circuit Breaker Pattern**: Prevents cascade failures
- **Data Persistence**: All critical data saved to MongoDB
- **State Recovery**: System can restart and restore positions
- **Backup Systems**: Multiple fallback mechanisms

---

## Performance Monitoring

### Key Metrics Tracked
- **Trade Execution Time**: Average time to execute trades
- **Price Update Frequency**: Real-time price processing speed
- **Strategy Performance**: Individual strategy success rates
- **System Uptime**: Continuous operation monitoring
- **Memory Usage**: Resource consumption tracking
- **Error Rates**: System reliability metrics

### Performance Optimization
- **Caching**: Price and position data caching
- **Async Processing**: Non-blocking operations
- **Connection Pooling**: Efficient database connections
- **Memory Management**: Garbage collection optimization
- **Threading**: Parallel processing where beneficial

---

## Security Considerations

### Data Protection
- **Environment Variables**: Sensitive data in .env files
- **Database Security**: MongoDB connection encryption
- **Email Security**: SMTP authentication and encryption
- **API Security**: Rate limiting and authentication
- **Input Validation**: All user inputs sanitized

### Risk Controls
- **Position Limits**: Hard limits on position sizes
- **Daily Limits**: Maximum trades per day
- **Leverage Limits**: Maximum leverage restrictions
- **Balance Checks**: Continuous balance validation
- **Emergency Stops**: Manual system shutdown capability

---

## Troubleshooting Guide

### Common Issues & Solutions

#### 1. Trade Rejections
- **Check**: Account balance, existing positions, risk limits
- **Solution**: Increase balance or reduce position size

#### 2. Email Not Sending
- **Check**: SMTP settings, email credentials, network connectivity
- **Solution**: Update email configuration in .env file

#### 3. Price Data Issues
- **Check**: WebSocket connection, API endpoints
- **Solution**: Restart live price system or check network

#### 4. Position Calculation Errors
- **Check**: Leverage settings, margin calculations
- **Solution**: Verify configuration parameters

#### 5. Database Connection Issues
- **Check**: MongoDB service, connection string
- **Solution**: Restart MongoDB or update connection settings

---

## Conclusion

This comprehensive guide covers all aspects of the trading system's calculations and workflows. The system is designed with multiple safety mechanisms, comprehensive logging, and detailed email notifications to ensure transparency and control over all trading activities.

For additional support or clarification on any calculation or workflow, refer to the specific source code files mentioned throughout this document or contact the system administrator.

**Last Updated**: 2025-01-28
**Version**: 2.1
**Author**: Professional Trading System Team