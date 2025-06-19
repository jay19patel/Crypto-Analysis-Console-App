import pandas as pd
from .base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

class TrendFollowingStrategy(BaseStrategy):
    """Multi-timeframe trend following strategy"""
    
    def __init__(self):
        super().__init__("Trend Following")
        self.required_indicators = ['EMA_5', 'EMA_15', 'EMA_50', 'RSI_14', 'ATR_14']
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """Analyze trend following signals"""
        conditions_met = []
        conditions_failed = []
        current_price = latest_data['close']
        
        # EMA Trend Analysis
        ema_5 = latest_data['EMA_5']
        ema_15 = latest_data['EMA_15']
        ema_50 = latest_data['EMA_50']
        
        # Check EMA alignment for uptrend
        ema_aligned_up = ema_5 > ema_15 > ema_50
        ema_aligned_down = ema_5 < ema_15 < ema_50
        price_above_emas = current_price > ema_5
        price_below_emas = current_price < ema_5
        
        if ema_aligned_up:
            conditions_met.append("EMAs aligned for uptrend (5>15>50)")
        elif ema_aligned_down:
            conditions_met.append("EMAs aligned for downtrend (5<15<50)")
        else:
            conditions_failed.append("EMAs not properly aligned")
        
        if price_above_emas:
            conditions_met.append("Price above short-term EMA")
        elif price_below_emas:
            conditions_met.append("Price below short-term EMA")
        else:
            conditions_failed.append("Price at EMA level")
        
        # RSI Filter
        rsi = latest_data['RSI_14']
        if 30 <= rsi <= 70:
            conditions_met.append("RSI in normal range (30-70)")
        elif rsi > 70:
            conditions_failed.append("RSI overbought (>70)")
        else:
            conditions_failed.append("RSI oversold (<30)")
        
        # Volume confirmation (if available)
        if 'volume' in latest_data:
            avg_volume = df['volume'].tail(20).mean()
            current_volume = latest_data['volume']
            if current_volume > avg_volume * 1.2:
                conditions_met.append("Volume above average")
            else:
                conditions_failed.append("Volume below average")
        
        # Calculate strength
        total_conditions = len(conditions_met) + len(conditions_failed)
        strength = (len(conditions_met) / total_conditions) * 100 if total_conditions > 0 else 0
        
        # Determine signal based on trend and strength
        if ema_aligned_up and price_above_emas and strength >= 75:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong uptrend with all conditions met"
        elif ema_aligned_up and price_above_emas and strength >= 60:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Moderate uptrend signal"
        elif ema_aligned_down and price_below_emas and strength >= 75:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong downtrend with all conditions met"
        elif ema_aligned_down and price_below_emas and strength >= 60:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Moderate downtrend signal"
        else:
            signal = SignalType.HOLD
            confidence = ConfidenceLevel.LOW
            interpretation = "Mixed trend signals, hold position"
        
        # Calculate risk management levels
        risk_mgmt = {}
        if 'ATR_14' in latest_data:
            atr = latest_data['ATR_14']
            risk_mgmt = self.calculate_risk_management(current_price, atr, signal)
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
            **risk_mgmt
        ) 