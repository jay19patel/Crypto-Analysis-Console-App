# 🚨 Trading System Warning Guide

## Risk Warning Scenarios & Calculations

### **Warning Levels & When They Should Trigger**

## 1. **LOW RISK** ✅ (No Warning)
```
Margin Usage: < 70%
Portfolio Loss: < 5%
Holding Time: < 12 hours
```

**Example:**
```
Account Balance: ₹10,000
Trade 1: ₹2,000 margin (20% usage)
Trade 2: ₹1,500 margin (15% usage)
Total Portfolio Margin: 35% ✅ HEALTHY
```

---

## 2. **MEDIUM RISK** ⚠️ (Monitor Warning)
```
Margin Usage: 70% - 80%
Portfolio Loss: 5% - 8%
Holding Time: 12 - 24 hours
```

**Example:**
```
Account Balance: ₹10,000
Trade 1: ₹4,000 margin (40% usage)
Trade 2: ₹3,500 margin (35% usage)
Total Portfolio Margin: 75% ⚠️ MONITOR CLOSELY
```

---

## 3. **HIGH RISK** 🔴 (Action Needed)
```
Margin Usage: 80% - 90%
Portfolio Loss: 8% - 12%
Holding Time: 24 - 36 hours
```

**Example Scenarios:**

### **Scenario A: High Margin Usage**
```
Account Balance: ₹10,000
Trade 1: ₹4,500 margin (45% usage)
Trade 2: ₹4,000 margin (40% usage)
Total Portfolio Margin: 85% 🔴 HIGH RISK
Warning: "Reduce position sizes"
```

### **Scenario B: High Loss Percentage**
```
Account Balance: ₹10,000
Total Positions Value: ₹50,000 (5x leveraged)
Current Loss: -₹1,000 (10% portfolio loss)
Warning: "Portfolio declining - review stop losses"
```

### **Scenario C: Multiple High-Risk Positions**
```
Position 1: 85% individual margin usage
Position 2: 82% individual margin usage
Warning: "Multiple positions need attention"
```

---

## 4. **CRITICAL RISK** 🚨 (Emergency Action)
```
Margin Usage: > 90%
Portfolio Loss: > 12%
Holding Time: > 36 hours
```

**Example Scenarios:**

### **Scenario A: Near Liquidation**
```
Account Balance: ₹10,000
Total Margin Used: ₹9,200 (92% usage)
Available Balance: ₹800
Warning: "CRITICAL - Close positions immediately"
Action: Auto-close positions
```

### **Scenario B: Critical Portfolio Loss**
```
Account Balance: ₹10,000
Portfolio Loss: -₹1,500 (15% loss)
Warning: "Portfolio loss critical - emergency close"
Action: Emergency position closure
```

---

## **Correct Calculation Formulas**

### **1. Individual Position Margin Usage**
```python
# CORRECT FORMULA
position_margin_usage = (margin_used_for_position / account_balance) * 100

# Example:
# Account: ₹10,000
# Position margin: ₹2,000
# Result: (2000 / 10000) * 100 = 20%
```

### **2. Portfolio Margin Usage**
```python
# CORRECT FORMULA
total_margin_used = sum(position.margin_used for all open positions)
portfolio_margin_usage = (total_margin_used / account_balance) * 100

# Example:
# Account: ₹10,000
# Position 1 margin: ₹2,000
# Position 2 margin: ₹1,500
# Total margin: ₹3,500
# Result: (3500 / 10000) * 100 = 35%
```

### **3. Portfolio Loss Percentage**
```python
# CORRECT FORMULA - SEPARATE FROM MARGIN
total_unrealized_pnl = sum(position.pnl for all open positions)
portfolio_loss_pct = (total_unrealized_pnl / account_balance) * 100

# Example:
# Account: ₹10,000
# Position 1 PnL: -₹300
# Position 2 PnL: +₹100
# Total PnL: -₹200
# Result: (-200 / 10000) * 100 = -2%
```

### **4. Risk Score Calculation**
```python
# WEIGHTED RISK FACTORS (0-100 scale)
risk_score = (
    margin_usage * 0.4 +        # 40% weight
    abs(loss_percentage) * 0.3 + # 30% weight
    time_factor * 0.2 +          # 20% weight
    volatility_factor * 0.1      # 10% weight
)
```

---

## **When Warnings Should NOT Trigger**

### **Normal Trading Scenarios (No Warning Expected)**

#### **Scenario 1: Your Current Trade**
```
Account Balance: ₹10,000
Position: 50x leverage, ₹2,000 capital (20% of balance)
Actual Margin Used: ₹2,000 ÷ 50 = ₹40 (0.4% margin usage)
Result: NO WARNING ✅ - Very safe
```

#### **Scenario 2: Two Normal Positions**
```
Account Balance: ₹10,000
Position 1: 50x leverage, ₹2,000 capital = ₹40 margin
Position 2: 30x leverage, ₹1,500 capital = ₹50 margin
Total Margin: ₹90 (0.9% usage)
Result: NO WARNING ✅ - Extremely safe
```

#### **Scenario 3: High Profit (No Warning)**
```
Account Balance: ₹10,000
Margin Usage: 20%
Current PnL: +₹2,000 (20% profit)
Result: PROFIT ALERT (Good news, not warning)
```

---

## **Bug That Was Causing False Warnings**

### **WRONG Calculation (Before Fix):**
```python
# BUG: Adding PnL loss to margin usage
if unrealized_pnl < 0:
    loss_impact = abs(unrealized_pnl) / account_balance * 100
    return base_margin_pct + loss_impact  # ❌ WRONG!

# Example of bug:
# Margin: 20% + Loss Impact: 65% = 85% (FALSE HIGH RISK)
```

### **CORRECT Calculation (After Fix):**
```python
# FIX: Keep margin and PnL separate
margin_usage = (margin_used / account_balance) * 100  # Pure margin only
pnl_risk = (unrealized_pnl / account_balance) * 100   # Separate PnL risk

# Example after fix:
# Margin: 20% (actual margin usage)
# PnL Risk: -5% (handled separately)
# Result: NO FALSE WARNING ✅
```

---

## **Real Warning Triggers (After Fix)**

### **When You SHOULD Get HIGH RISK Warning:**

#### **Scenario 1: Too Many Large Positions**
```
Account Balance: ₹10,000
Position 1: ₹4,000 margin (40% usage)
Position 2: ₹4,500 margin (45% usage)
Total Portfolio Margin: 85%
Result: HIGH RISK WARNING ✅ (Correct)
```

#### **Scenario 2: Large Portfolio Loss**
```
Account Balance: ₹10,000
Total Portfolio Loss: -₹1,000 (10% loss)
Result: HIGH RISK WARNING ✅ (Correct)
```

#### **Scenario 3: Positions Held Too Long**
```
Position Age: 30 hours (>24 hours limit)
Result: HIGH RISK WARNING ✅ (Correct)
```

---

## **Summary: When Warnings Are Valid**

| Risk Level | Margin Usage | Portfolio Loss | Time | Action |
|------------|--------------|----------------|------|--------|
| **LOW** | < 70% | < 5% | < 12h | Continue trading |
| **MEDIUM** | 70-80% | 5-8% | 12-24h | Monitor closely |
| **HIGH** | 80-90% | 8-12% | 24-36h | Reduce exposure |
| **CRITICAL** | > 90% | > 12% | > 36h | Emergency close |

### **Your Trade Analysis:**
```
✅ Margin Usage: 0.4% (Safe)
✅ Leverage: 50x (Within limits)
✅ Capital Used: 20% (Optimal)
✅ Expected Result: NO WARNINGS

❌ Bug Result: HIGH RISK (False alarm)
✅ After Fix: NO WARNINGS (Correct)
```

The system should only warn you when you're actually at risk, not when you're trading safely!