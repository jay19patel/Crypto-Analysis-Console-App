import pandas as pd
from src.strategies.base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

class RSIStrategy(BaseStrategy):
    """RSI overbought/oversold strategy with divergence detection"""
    
    def __init__(self):
        super().__init__("RSI Strategy")
        self.required_indicators = ['RSI_14']
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """Analyze RSI signals"""
        conditions_met = []
        conditions_failed = []
        
        rsi = latest_data['RSI_14']
        current_price = latest_data['close']
        
        # RSI levels analysis
        if rsi < 30:
            conditions_met.append("RSI oversold (<30)")
            base_signal = SignalType.BUY
            base_confidence = ConfidenceLevel.HIGH
            base_interpretation = "RSI oversold - potential buy signal"
        elif rsi > 70:
            conditions_met.append("RSI overbought (>70)")
            base_signal = SignalType.SELL
            base_confidence = ConfidenceLevel.HIGH
            base_interpretation = "RSI overbought - potential sell signal"
        elif 40 <= rsi <= 60:
            conditions_met.append("RSI in neutral zone (40-60)")
            base_signal = SignalType.HOLD
            base_confidence = ConfidenceLevel.MEDIUM
            base_interpretation = "RSI neutral - hold position"
        else:
            conditions_failed.append("RSI in uncertain range (30-40 or 60-70)")
            base_signal = SignalType.NEUTRAL
            base_confidence = ConfidenceLevel.LOW
            base_interpretation = "RSI signals unclear"
        
        # RSI momentum analysis
        if len(df) >= 5:
            rsi_5_periods_ago = df.iloc[-5]['RSI_14']
            if rsi > rsi_5_periods_ago + 5:
                conditions_met.append("RSI momentum increasing")
            elif rsi < rsi_5_periods_ago - 5:
                conditions_met.append("RSI momentum decreasing")
            else:
                conditions_failed.append("RSI momentum flat")
        
        # Check for divergence (basic implementation)
        divergence_detected = False
        if len(df) >= 20:
            # Look for price and RSI divergence over last 20 periods
            recent_df = df.tail(20)
            
            # Find recent highs and lows
            price_high_idx = recent_df['high'].idxmax()
            price_low_idx = recent_df['low'].idxmin()
            rsi_high_idx = recent_df['RSI_14'].idxmax()
            rsi_low_idx = recent_df['RSI_14'].idxmin()
            
            # Bullish divergence: price makes lower low, RSI makes higher low
            if (price_low_idx > rsi_low_idx and 
                recent_df.loc[price_low_idx, 'low'] < recent_df.loc[rsi_low_idx, 'low'] and
                recent_df.loc[price_low_idx, 'RSI_14'] > recent_df.loc[rsi_low_idx, 'RSI_14']):
                conditions_met.append("Bullish RSI divergence detected")
                divergence_detected = True
            
            # Bearish divergence: price makes higher high, RSI makes lower high
            elif (price_high_idx > rsi_high_idx and 
                  recent_df.loc[price_high_idx, 'high'] > recent_df.loc[rsi_high_idx, 'high'] and
                  recent_df.loc[price_high_idx, 'RSI_14'] < recent_df.loc[rsi_high_idx, 'RSI_14']):
                conditions_met.append("Bearish RSI divergence detected")
                divergence_detected = True
            else:
                conditions_failed.append("No RSI divergence detected")
        
        # RSI trend analysis
        if len(df) >= 10:
            rsi_trend = df['RSI_14'].tail(10).mean()
            if rsi > rsi_trend + 5:
                conditions_met.append("RSI above recent average")
            elif rsi < rsi_trend - 5:
                conditions_met.append("RSI below recent average")
            else:
                conditions_failed.append("RSI near recent average")
        
        # Calculate strength
        total_conditions = len(conditions_met) + len(conditions_failed)
        strength = (len(conditions_met) / total_conditions) * 100 if total_conditions > 0 else 0
        
        # Adjust signal based on additional conditions
        if divergence_detected:
            # Divergence can strengthen or reverse base signal
            if base_signal == SignalType.BUY and "Bullish RSI divergence" in conditions_met:
                signal = SignalType.BUY
                confidence = ConfidenceLevel.VERY_HIGH
                interpretation = "Strong buy signal: RSI oversold with bullish divergence"
            elif base_signal == SignalType.SELL and "Bearish RSI divergence" in conditions_met:
                signal = SignalType.SELL
                confidence = ConfidenceLevel.VERY_HIGH
                interpretation = "Strong sell signal: RSI overbought with bearish divergence"
            else:
                signal = base_signal
                confidence = base_confidence
                interpretation = base_interpretation
        else:
            signal = base_signal
            confidence = base_confidence
            interpretation = base_interpretation
        
        # Adjust confidence based on strength
        if strength >= 80:
            confidence = ConfidenceLevel.VERY_HIGH
        elif strength >= 60:
            confidence = ConfidenceLevel.HIGH
        elif strength >= 40:
            confidence = ConfidenceLevel.MEDIUM
        elif strength >= 20:
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