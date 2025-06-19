import pandas as pd
from .base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

class MACDCrossoverStrategy(BaseStrategy):
    """MACD signal line crossover strategy"""
    
    def __init__(self):
        super().__init__("MACD Crossover")
        self.required_indicators = ['MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9']
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """Analyze MACD crossover signals"""
        conditions_met = []
        conditions_failed = []
        
        # Get MACD data
        macd_line = latest_data['MACD_12_26_9']
        signal_line = latest_data['MACDs_12_26_9']
        histogram = latest_data['MACDh_12_26_9']
        
        # Initialize signal variables
        bullish_crossover = False
        bearish_crossover = False
        
        # Check for crossover (need at least 2 periods)
        if len(df) >= 2:
            prev_macd = df.iloc[-2]['MACD_12_26_9']
            prev_signal = df.iloc[-2]['MACDs_12_26_9']
            
            # Bullish crossover: MACD crosses above signal line
            bullish_crossover = (prev_macd <= prev_signal) and (macd_line > signal_line)
            # Bearish crossover: MACD crosses below signal line
            bearish_crossover = (prev_macd >= prev_signal) and (macd_line < signal_line)
            
            if bullish_crossover:
                conditions_met.append("MACD line crossed above signal line")
            elif bearish_crossover:
                conditions_met.append("MACD line crossed below signal line")
            else:
                conditions_failed.append("No recent MACD crossover")
        
        # Check histogram direction
        if histogram > 0:
            conditions_met.append("MACD histogram is positive")
        else:
            conditions_failed.append("MACD histogram is negative")
        
        # Check zero line position
        if macd_line > 0 and signal_line > 0:
            conditions_met.append("MACD and signal above zero line")
        elif macd_line < 0 and signal_line < 0:
            conditions_met.append("MACD and signal below zero line")
        else:
            conditions_failed.append("MACD lines around zero line")
        
        # Check histogram momentum
        if len(df) >= 3:
            prev_hist = df.iloc[-2]['MACDh_12_26_9']
            if histogram > prev_hist:
                conditions_met.append("MACD histogram increasing")
            else:
                conditions_failed.append("MACD histogram decreasing")
        
        # Calculate strength
        total_conditions = len(conditions_met) + len(conditions_failed)
        strength = (len(conditions_met) / total_conditions) * 100 if total_conditions > 0 else 0
        
        # Determine signal
        if bullish_crossover and strength >= 75:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong bullish MACD crossover"
        elif bearish_crossover and strength >= 75:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong bearish MACD crossover"
        elif macd_line > signal_line and histogram > 0:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "MACD bullish alignment"
        elif macd_line < signal_line and histogram < 0:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "MACD bearish alignment"
        else:
            signal = SignalType.NEUTRAL
            confidence = ConfidenceLevel.LOW
            interpretation = "No clear MACD signal"
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        ) 