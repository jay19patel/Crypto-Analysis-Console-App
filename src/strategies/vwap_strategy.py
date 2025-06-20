import pandas as pd
from src.strategies.base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

class VWAPStrategy(BaseStrategy):
    """Volume Weighted Average Price strategy"""
    
    def __init__(self):
        super().__init__("VWAP Strategy")
        self.required_indicators = ['VWAP']
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """Analyze VWAP signals"""
        conditions_met = []
        conditions_failed = []
        
        current_price = latest_data['close']
        vwap = latest_data['VWAP']
        
        # Price vs VWAP position
        price_vwap_diff = ((current_price - vwap) / vwap) * 100
        
        if current_price > vwap:
            conditions_met.append(f"Price above VWAP (+{price_vwap_diff:.2f}%)")
            base_signal = SignalType.BUY
            base_interpretation = "Price trading above VWAP - bullish"
        elif current_price < vwap:
            conditions_met.append(f"Price below VWAP ({price_vwap_diff:.2f}%)")
            base_signal = SignalType.SELL
            base_interpretation = "Price trading below VWAP - bearish"
        else:
            conditions_failed.append("Price exactly at VWAP")
            base_signal = SignalType.NEUTRAL
            base_interpretation = "Price at VWAP - neutral"
        
        # Distance significance
        abs_distance = abs(price_vwap_diff)
        if abs_distance > 3:
            conditions_met.append(f"Significant distance from VWAP ({abs_distance:.2f}%)")
        elif abs_distance > 1:
            conditions_met.append(f"Moderate distance from VWAP ({abs_distance:.2f}%)")
        else:
            conditions_failed.append(f"Close to VWAP ({abs_distance:.2f}%)")
        
        # VWAP trend analysis
        if len(df) >= 10:
            vwap_10_ago = df.iloc[-10]['VWAP']
            vwap_trend = ((vwap - vwap_10_ago) / vwap_10_ago) * 100
            
            if vwap_trend > 1:
                conditions_met.append(f"VWAP trending up ({vwap_trend:.2f}%)")
            elif vwap_trend < -1:
                conditions_met.append(f"VWAP trending down ({vwap_trend:.2f}%)")
            else:
                conditions_failed.append("VWAP trend flat")
        
        # Volume analysis (if available)
        if 'volume' in latest_data and len(df) >= 20:
            current_volume = latest_data['volume']
            avg_volume = df['volume'].tail(20).mean()
            volume_ratio = current_volume / avg_volume
            
            if volume_ratio > 1.5:
                conditions_met.append(f"High volume confirmation ({volume_ratio:.1f}x avg)")
            elif volume_ratio > 1.0:
                conditions_met.append(f"Above average volume ({volume_ratio:.1f}x avg)")
            else:
                conditions_failed.append(f"Below average volume ({volume_ratio:.1f}x avg)")
        
        # Price action relative to VWAP over time
        if len(df) >= 5:
            recent_prices = df['close'].tail(5)
            recent_vwaps = df['VWAP'].tail(5)
            
            above_count = sum(recent_prices > recent_vwaps)
            if above_count >= 4:
                conditions_met.append("Consistently above VWAP (4/5 periods)")
            elif above_count <= 1:
                conditions_met.append("Consistently below VWAP (1/5 periods)")
            else:
                conditions_failed.append("Mixed position relative to VWAP")
        
        # Calculate strength
        total_conditions = len(conditions_met) + len(conditions_failed)
        strength = (len(conditions_met) / total_conditions) * 100 if total_conditions > 0 else 0
        
        # Determine confidence based on distance and conditions
        if abs_distance > 3 and strength >= 75:
            confidence = ConfidenceLevel.HIGH
        elif abs_distance > 2 and strength >= 60:
            confidence = ConfidenceLevel.MEDIUM
        elif abs_distance > 1 and strength >= 50:
            confidence = ConfidenceLevel.LOW
        else:
            confidence = ConfidenceLevel.VERY_LOW
        
        # Adjust signal and interpretation based on analysis
        if base_signal == SignalType.BUY and strength >= 70:
            signal = SignalType.BUY
            interpretation = f"Strong bullish signal: {base_interpretation}"
        elif base_signal == SignalType.SELL and strength >= 70:
            signal = SignalType.SELL
            interpretation = f"Strong bearish signal: {base_interpretation}"
        elif abs_distance < 0.5:
            signal = SignalType.NEUTRAL
            interpretation = "Price very close to VWAP - wait for clearer signal"
        else:
            signal = base_signal
            interpretation = base_interpretation
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        ) 