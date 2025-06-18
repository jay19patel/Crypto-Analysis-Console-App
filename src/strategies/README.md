# Trading Strategies System

## Overview

This directory contains a comprehensive, modular trading strategies system that allows you to easily add, modify, and manage different trading strategies for technical analysis.

## Architecture

```
src/strategies/
├── __init__.py              # Package initialization
├── base_strategy.py         # Base classes and data structures
├── strategy_manager.py      # Main strategy manager
├── trend_strategy.py        # Trend following strategy
├── macd_strategy.py         # MACD crossover strategy
├── rsi_strategy.py          # RSI overbought/oversold strategy
├── stochastic_strategy.py   # Stochastic oscillator strategy
├── vwap_strategy.py         # VWAP strategy
├── example_new_strategy.py  # Example of how to create new strategies
└── README.md               # This file
```

## Key Components

### 1. BaseStrategy Class
All strategies inherit from `BaseStrategy` which provides:
- Abstract `analyze()` method that must be implemented
- Data validation for required indicators
- Risk management calculation helper methods

### 2. StrategyResult DataClass
Standardized output format containing:
- Signal type (BUY/SELL/HOLD/NEUTRAL)
- Confidence level (VERY_LOW to VERY_HIGH)
- Strength percentage (0-100)
- Human-readable interpretation
- Detailed conditions met/failed lists
- Optional risk management levels

### 3. StrategyManager
Central manager that:
- Loads and manages all strategies
- Runs analysis on all strategies
- Calculates consensus signals
- Handles errors gracefully

## Built-in Strategies

### 1. Trend Following Strategy
- **Indicators Required**: EMA_5, EMA_15, EMA_50, RSI_14, ATR_14
- **Logic**: Analyzes EMA alignment and price position for trend signals
- **Features**: Volume confirmation, risk management levels

### 2. MACD Crossover Strategy  
- **Indicators Required**: MACD_12_26_9, MACDs_12_26_9, MACDh_12_26_9
- **Logic**: Detects MACD line crossovers with signal line
- **Features**: Histogram momentum analysis, zero-line confirmation

### 3. RSI Strategy
- **Indicators Required**: RSI_14
- **Logic**: Overbought/oversold levels with divergence detection
- **Features**: Momentum analysis, basic divergence detection

### 4. Stochastic Strategy
- **Indicators Required**: STOCHk_14_3_3, STOCHd_14_3_3
- **Logic**: %K and %D crossovers with overbought/oversold levels
- **Features**: Crossover confirmation, momentum analysis

### 5. VWAP Strategy
- **Indicators Required**: VWAP
- **Logic**: Price position relative to Volume Weighted Average Price
- **Features**: Distance analysis, volume confirmation, trend analysis

## How to Add a New Strategy

### Step 1: Create Your Strategy Class

```python
from .base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("My Custom Strategy")
        self.required_indicators = ['EMA_20', 'RSI_14']  # Define what you need
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        conditions_met = []
        conditions_failed = []
        
        # Your strategy logic here
        ema_20 = latest_data['EMA_20']
        rsi = latest_data['RSI_14']
        current_price = latest_data['close']
        
        # Example logic
        if current_price > ema_20 and rsi < 70:
            signal = SignalType.BUY
            conditions_met.append("Price above EMA and RSI not overbought")
            interpretation = "Bullish signal"
        else:
            signal = SignalType.NEUTRAL
            conditions_failed.append("Conditions not met")
            interpretation = "No clear signal"
        
        # Calculate strength
        total_conditions = len(conditions_met) + len(conditions_failed)
        strength = (len(conditions_met) / total_conditions) * 100
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=ConfidenceLevel.MEDIUM,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        )
```

### Step 2: Add to Strategy Manager

Option A - Modify `strategy_manager.py`:
```python
# In _load_default_strategies method, add:
from .my_custom_strategy import MyCustomStrategy

# Add to strategies list:
self.strategies = [
    TrendFollowingStrategy(),
    MACDCrossoverStrategy(),
    RSIStrategy(),
    StochasticStrategy(),
    VWAPStrategy(),
    MyCustomStrategy()  # Add your strategy here
]
```

Option B - Add programmatically:
```python
# In your application code:
analysis = TechnicalAnalysis(ui, symbol, resolution, days)
custom_strategy = MyCustomStrategy()
analysis.strategy_manager.add_strategy(custom_strategy)
```

### Step 3: Ensure Required Indicators

Make sure any indicators your strategy needs are calculated in `technical_analysis.py`:

```python
# In calculate_indicators method:
self.df['EMA_20'] = ta.ema(self.df['close'], length=20)
```

## Signal Types and Confidence Levels

### Signal Types
- `BUY`: Strong buy signal
- `SELL`: Strong sell signal  
- `HOLD`: Hold current position
- `NEUTRAL`: No clear signal

### Confidence Levels
- `VERY_HIGH` (5): Extremely confident in signal
- `HIGH` (4): High confidence
- `MEDIUM` (3): Moderate confidence
- `LOW` (2): Low confidence
- `VERY_LOW` (1): Very uncertain

## Best Practices

### 1. Strategy Design
- Keep strategies focused on one concept
- Make logic clear and well-documented
- Handle edge cases (insufficient data, missing indicators)
- Use meaningful condition descriptions

### 2. Error Handling
- Always validate input data
- Handle missing indicators gracefully
- Provide clear error messages
- Never crash the system

### 3. Testing
- Test with different market conditions
- Verify required indicators are available
- Check edge cases (first few periods, missing data)
- Validate signal logic

### 4. Performance
- Avoid complex calculations in hot paths
- Cache expensive computations when possible
- Use vectorized pandas operations
- Limit lookback periods reasonably

## Usage Examples

### Basic Usage
```python
from src.data.technical_analysis import TechnicalAnalysis
from src.ui.console import ConsoleUI

ui = ConsoleUI()
analysis = TechnicalAnalysis(ui, 'BTCUSD', '5m', 10)

if analysis.refresh():
    results = analysis.get_analysis_results()
    ui.print_analysis_results(results, 'BTCUSD')
```

### Adding Custom Strategy
```python
from src.strategies.example_new_strategy import MovingAverageCrossStrategy

# Add to existing analysis
custom_strategy = MovingAverageCrossStrategy()
analysis.strategy_manager.add_strategy(custom_strategy)

# Refresh analysis to include new strategy
analysis.refresh()
```

### Accessing Individual Results
```python
strategy_results = analysis.strategy_manager.analyze_all(analysis.df)
for result in strategy_results:
    print(f"{result.name}: {result.signal.value} ({result.confidence.name})")
    print(f"  Strength: {result.strength:.1f}%")
    print(f"  {result.interpretation}")
```

### Getting Consensus
```python
consensus = analysis.strategy_manager.get_consensus_signal(strategy_results)
print(f"Consensus: {consensus['signal']} ({consensus['confidence']})")
print(f"Interpretation: {consensus['interpretation']}")
```

## Troubleshooting

### Common Issues

1. **Missing Indicators Error**
   - Check that required indicators are calculated in `technical_analysis.py`
   - Verify indicator names match exactly

2. **Strategy Not Running**
   - Ensure strategy is added to StrategyManager
   - Check for import errors
   - Verify strategy inherits from BaseStrategy

3. **Poor Signal Quality**
   - Review strategy logic
   - Check confidence level calculations
   - Validate with historical data

4. **Performance Issues**
   - Limit complex calculations
   - Use appropriate lookback periods
   - Consider caching expensive operations

### Debug Mode
Enable debug output by adding print statements in your strategy:

```python
def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
    print(f"Analyzing {self.name} with {len(df)} periods")
    # Your strategy logic
```

## Contributing

When adding new strategies:
1. Follow the existing code style
2. Add comprehensive documentation
3. Include example usage
4. Test thoroughly
5. Update this README if needed

## Future Enhancements

Potential improvements:
- Backtesting framework
- Parameter optimization
- Machine learning strategies
- Multi-timeframe analysis
- Portfolio management integration
- Advanced risk management
- Strategy performance metrics 