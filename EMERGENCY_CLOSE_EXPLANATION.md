# 🚨 Emergency Close Risk Management - Complete Guide

## 🔍 Why Emergency Close Happens?

The system triggers `EMERGENCY_CLOSE` when your position reaches **CRITICAL RISK** level. Here are the exact conditions:

### CRITICAL Risk Conditions (Any one triggers emergency close):
1. **Margin Usage > 95%** - When you're using almost all available margin
2. **P&L Loss > -10%** - When position loses more than 10% 
3. **Holding Time > 48 hours** - When position is held too long
4. **System Error** - When risk calculation fails

### How Emergency Close Triggers:
```python
# CRITICAL RISK CONDITIONS
if (margin_usage > 95 or 
    pnl_percentage < -10 or 
    holding_time_hours > 48):
    # → RiskLevel.CRITICAL
    # → RiskAction.EMERGENCY_CLOSE
    # → Position automatically closed
```

## 📊 Current Risk Levels & Actions

| Risk Level | Conditions | Action Taken |
|------------|------------|--------------|
| **CRITICAL** | Margin > 95% OR Loss > -10% OR Time > 48h | `EMERGENCY_CLOSE` |
| **HIGH** | Margin > 80% OR Loss > -5% OR Time > 36h | `TIGHTEN_STOP_LOSS` |
| **MEDIUM** | Margin > 60% OR Loss > -2% OR Time > 24h | `MONITOR` |
| **LOW** | Normal conditions | `MONITOR` |

## 🛡️ How to Prevent Emergency Close

### 1. **Reduce Risk Thresholds** (Recommended)
Modify these values in risk manager to be less aggressive:

```python
# Current (Aggressive)
margin_usage > 95    # Emergency at 95% margin
pnl_percentage < -10 # Emergency at -10% loss
holding_time_hours > 48 # Emergency after 48 hours

# Suggested (Conservative)
margin_usage > 98    # Emergency at 98% margin  
pnl_percentage < -15 # Emergency at -15% loss
holding_time_hours > 72 # Emergency after 72 hours
```

### 2. **Disable Automatic Emergency Close**
Add a config setting to disable auto-close:

```python
# Add to config
ENABLE_EMERGENCY_CLOSE: bool = Field(default=False)
```

### 3. **Use Better Position Sizing**
Your 20% balance per trade system helps, but also:
- Use lower leverage to reduce margin usage
- Set proper stop losses manually  
- Don't hold positions too long

### 4. **Monitor Risk Actively**
- Check risk metrics regularly
- Close positions manually before they hit critical
- Use trailing stops for profit protection

## 🔧 Configuration Options to Prevent Unwanted Closes

### Option 1: Increase Risk Thresholds
```python
# Make the system more tolerant
CRITICAL_MARGIN_THRESHOLD: float = Field(default=98.0)  # Instead of 95%
CRITICAL_LOSS_THRESHOLD: float = Field(default=-15.0)   # Instead of -10%
CRITICAL_TIME_THRESHOLD: int = Field(default=72)        # Instead of 48 hours
```

### Option 2: Disable Auto-Close for Specific Actions
```python
# Add to config
ALLOW_EMERGENCY_CLOSE: bool = Field(default=False)
ALLOW_AUTO_RISK_CLOSE: bool = Field(default=False)
```

### Option 3: Warning-Only Mode
```python
# Just send notifications, don't close positions
RISK_ACTION_MODE: str = Field(default="warning_only")  # or "auto_close"
```

## 📈 Smart Risk Management Strategy

### Best Practices:
1. **Set Proper Stop Losses**: Always set stop loss at entry
2. **Use Appropriate Leverage**: Don't over-leverage positions
3. **Monitor P&L**: Close losing positions before -10%
4. **Time Management**: Don't hold positions beyond your strategy timeframe
5. **Portfolio Diversification**: Spread risk across multiple positions

### Position Sizing Formula (Your Current System):
```python
# Your 20% balance system already helps prevent margin issues
balance_per_trade = current_balance * 0.20  # 20%
position_value = balance_per_trade * leverage
margin_required = position_value / leverage  # = balance_per_trade
```

## 🚀 Recommended Solution

I recommend implementing a **configurable risk management system** where you can:

1. **Adjust risk thresholds** via config
2. **Enable/disable emergency close** per your preference  
3. **Set warning-only mode** for learning
4. **Customize risk actions** based on your trading style

Would you like me to implement this flexible risk management system for you?