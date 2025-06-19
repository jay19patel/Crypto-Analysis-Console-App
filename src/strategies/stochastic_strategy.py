import pandas as pd
from .base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

class StochasticStrategy(BaseStrategy):
    """Stochastic oscillator strategy"""
    
    def __init__(self):
        super().__init__("Stochastic Strategy")
        self.required_indicators = ['STOCHk_14_3_3', 'STOCHd_14_3_3']
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """Analyze Stochastic signals"""
        conditions_met = []
        conditions_failed = []
        
        stoch_k = latest_data['STOCHk_14_3_3']
        stoch_d = latest_data['STOCHd_14_3_3']
        
        # Overbought/Oversold levels
        if stoch_k < 20 and stoch_d < 20:
            conditions_met.append("Stochastic oversold (<20)")
            base_signal = SignalType.BUY
            base_confidence = ConfidenceLevel.MEDIUM
            base_interpretation = "Stochastic oversold condition"
        elif stoch_k > 80 and stoch_d > 80:
            conditions_met.append("Stochastic overbought (>80)")
            base_signal = SignalType.SELL
            base_confidence = ConfidenceLevel.MEDIUM
            base_interpretation = "Stochastic overbought condition"
        else:
            conditions_failed.append("Stochastic in normal range (20-80)")
            base_signal = SignalType.NEUTRAL
            base_confidence = ConfidenceLevel.LOW
            base_interpretation = "No clear stochastic signal"
        
        # Check for crossovers
        crossover_signal = None
        if len(df) >= 2:
            prev_k = df.iloc[-2]['STOCHk_14_3_3']
            prev_d = df.iloc[-2]['STOCHd_14_3_3']
            
            # Bullish crossover: %K crosses above %D
            if prev_k <= prev_d and stoch_k > stoch_d:
                conditions_met.append("%K crossed above %D (bullish)")
                crossover_signal = SignalType.BUY
            # Bearish crossover: %K crosses below %D
            elif prev_k >= prev_d and stoch_k < stoch_d:
                conditions_met.append("%K crossed below %D (bearish)")
                crossover_signal = SignalType.SELL
            else:
                conditions_failed.append("No recent crossover")
        
        # Check line positions relative to each other
        if stoch_k > stoch_d:
            conditions_met.append("%K above %D")
        else:
            conditions_met.append("%K below %D")
        
        # Check momentum
        if len(df) >= 3:
            prev_k_2 = df.iloc[-3]['STOCHk_14_3_3']
            if stoch_k > prev_k_2:
                conditions_met.append("Stochastic momentum increasing")
            else:
                conditions_failed.append("Stochastic momentum decreasing")
        
        # Calculate strength
        total_conditions = len(conditions_met) + len(conditions_failed)
        strength = (len(conditions_met) / total_conditions) * 100 if total_conditions > 0 else 0
        
        # Determine final signal combining base signal and crossover
        if crossover_signal and base_signal != SignalType.NEUTRAL:
            if crossover_signal == base_signal:
                # Crossover confirms base signal
                signal = base_signal
                confidence = ConfidenceLevel.HIGH
                interpretation = f"Strong {base_signal.value.lower()} signal: crossover confirms overbought/oversold"
            else:
                # Crossover contradicts base signal - prioritize crossover
                signal = crossover_signal
                confidence = ConfidenceLevel.MEDIUM
                interpretation = f"Crossover signal {crossover_signal.value.lower()}"
        elif crossover_signal:
            signal = crossover_signal
            confidence = ConfidenceLevel.MEDIUM
            interpretation = f"Crossover signal {crossover_signal.value.lower()}"
        else:
            signal = base_signal
            confidence = base_confidence
            interpretation = base_interpretation
        
        # Adjust confidence based on strength
        if strength >= 80:
            confidence = ConfidenceLevel.HIGH
        elif strength >= 60:
            confidence = ConfidenceLevel.MEDIUM
        elif strength >= 40:
            confidence = ConfidenceLevel.LOW
        else:
            confidence = ConfidenceLevel.VERY_LOW
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        ) 