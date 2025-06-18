import pandas as pd
from .base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

class AdvancedTrendStrategy(BaseStrategy):
    """
    Advanced trend strategy using Supertrend, ADX, and Z-Score
    
    This strategy combines multiple advanced indicators for high-quality signals:
    - Supertrend for trend direction
    - ADX for trend strength
    - Z-Score for entry/exit timing
    """
    
    def __init__(self):
        super().__init__("Advanced Trend")
        self.required_indicators = [
            'SUPERT_10_3.0', 'SUPERTd_10_3.0',
            'ADX_14', 'DMP_14', 'DMN_14',
            'ZSCORE_20'
        ]
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """Analyze advanced trend signals"""
        conditions_met = []
        conditions_failed = []
        
        # Get values
        supert_direction = latest_data.get('SUPERTd_10_3.0')
        adx_value = latest_data.get('ADX_14')
        dmp_value = latest_data.get('DMP_14')
        dmn_value = latest_data.get('DMN_14')
        zscore_value = latest_data.get('ZSCORE_20')
        
        # Supertrend Analysis
        if pd.notna(supert_direction):
            if supert_direction == 1:
                conditions_met.append("Supertrend bullish")
            else:
                conditions_met.append("Supertrend bearish")
        else:
            conditions_failed.append("No Supertrend data")
        
        # ADX Analysis
        if pd.notna(adx_value):
            if adx_value > 25:
                conditions_met.append(f"Strong trend (ADX: {adx_value:.1f})")
            else:
                conditions_failed.append(f"Weak trend (ADX: {adx_value:.1f})")
        else:
            conditions_failed.append("No ADX data")
        
        # Z-Score Analysis
        if pd.notna(zscore_value):
            if abs(zscore_value) > 1:
                conditions_met.append(f"Z-Score extreme: {zscore_value:.2f}")
            else:
                conditions_failed.append("Z-Score normal range")
        else:
            conditions_failed.append("No Z-Score data")
        
        # Simple signal logic
        total_conditions = len(conditions_met) + len(conditions_failed)
        strength = (len(conditions_met) / total_conditions) * 100 if total_conditions > 0 else 0
        
        if strength >= 70:
            signal = SignalType.BUY if supert_direction == 1 else SignalType.SELL
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong advanced signal"
        elif strength >= 50:
            signal = SignalType.HOLD
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Moderate signal"
        else:
            signal = SignalType.NEUTRAL
            confidence = ConfidenceLevel.LOW
            interpretation = "Weak signal"
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        ) 