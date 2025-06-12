"""
Trading Strategies Module
Implements various trading strategies combining multiple technical indicators
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class StrategySignal:
    """Data class to hold strategy signals"""
    strategy_name: str
    signal: str  # "BUY", "SELL", or "NEUTRAL"
    strength: float  # 0 to 100
    conditions_met: List[str]
    conditions_failed: List[str]
    interpretation: str


class TradingStrategies:
    """
    Trading Strategies implementation combining multiple technical indicators
    
    Usage:
        strategies = TradingStrategies(historical_data)
        signals = strategies.analyze_all()
        
        # Or individual strategies
        trend_signal = strategies.trend_following_strategy()
        mean_rev_signal = strategies.mean_reversion_strategy()
        volatility_signal = strategies.volatility_breakout_strategy()
        volume_signal = strategies.volume_analysis_strategy()
    """
    
    def __init__(self, data):
        """
        Initialize with HistoricalData instance
        
        Args:
            data: HistoricalData instance with required indicators
        """
        self.data = data
        self.df = data.df
        self.latest = data.df.iloc[-1] if not data.df.empty else None
        
    def trend_following_strategy(self) -> StrategySignal:
        """
        Trend Following Strategy using EMA, Supertrend, and ADX
        
        Requirements:
        - Price > EMA20
        - Supertrend is Bullish
        - ADX > 25 (strong trend)
        
        Returns:
            StrategySignal: Signal details and analysis
        """
        if self.latest is None:
            return StrategySignal(
                strategy_name="Trend Following",
                signal="NEUTRAL",
                strength=0,
                conditions_met=[],
                conditions_failed=["No data available"],
                interpretation="Insufficient data"
            )
            
        conditions_met = []
        conditions_failed = []
        current_price = self.latest['close']
        
        # Check EMA condition
        ema_20 = self.latest.get('EMA_20', None)
        if ema_20 is not None:
            if current_price > ema_20:
                conditions_met.append("Price above EMA20")
            else:
                conditions_failed.append("Price below EMA20")
        
        # Check Supertrend condition
        supertrend_signal = self.latest.get('Supertrend_Signal', None)
        if supertrend_signal is not None:
            if supertrend_signal == 1:  # 1 indicates bullish
                conditions_met.append("Supertrend is Bullish")
            else:
                conditions_failed.append("Supertrend is Bearish")
                
        # Check ADX condition
        adx = self.latest.get('ADX_14', None)
        if adx is not None:
            if adx > 25:
                conditions_met.append("Strong trend (ADX > 25)")
            else:
                conditions_failed.append("Weak trend (ADX < 25)")
        
        # Calculate signal
        total_conditions = 3
        met_count = len(conditions_met)
        strength = (met_count / total_conditions) * 100
        
        if met_count == total_conditions:
            signal = "BUY"
            interpretation = "Strong trend following buy signal"
        elif met_count == 0:
            signal = "SELL"
            interpretation = "All trend conditions failed"
        else:
            signal = "NEUTRAL"
            interpretation = f"Mixed signals ({met_count}/{total_conditions} conditions met)"
        
        return StrategySignal(
            strategy_name="Trend Following",
            signal=signal,
            strength=strength,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
            interpretation=interpretation
        )
    
    def mean_reversion_strategy(self) -> StrategySignal:
        """
        Mean Reversion Strategy using RSI, Z-Score, and Stochastic
        
        Buy Conditions:
        - RSI < 30 (oversold)
        - Z-Score < -2 (significantly below mean)
        - Stochastic < 20 (oversold)
        
        Returns:
            StrategySignal: Signal details and analysis
        """
        if self.latest is None:
            return StrategySignal(
                strategy_name="Mean Reversion",
                signal="NEUTRAL",
                strength=0,
                conditions_met=[],
                conditions_failed=["No data available"],
                interpretation="Insufficient data"
            )
            
        conditions_met = []
        conditions_failed = []
        
        # Check RSI condition
        rsi = self.latest.get('RSI_14', None)
        if rsi is not None:
            if rsi < 30:  # Oversold
                conditions_met.append("RSI oversold (< 30)")
            elif rsi > 70:  # Overbought
                conditions_failed.append("RSI overbought (> 70)")
            else:
                conditions_failed.append("RSI neutral zone")
        
        # Check Z-Score condition
        zscore = self.latest.get('ZSCORE_20', None)
        if zscore is not None:
            if zscore < -2:
                conditions_met.append("Z-Score below -2")
            elif zscore > 2:
                conditions_failed.append("Z-Score above +2")
            else:
                conditions_failed.append("Z-Score in normal range")
        
        # Calculate Stochastic (if not already available)
        if 'Stoch_14' not in self.df.columns:
            stoch = pd.Series(dtype=float)  # Placeholder for actual implementation
        else:
            stoch = self.latest['Stoch_14']
            
        if stoch is not None:
            if stoch < 20:
                conditions_met.append("Stochastic oversold (< 20)")
            elif stoch > 80:
                conditions_failed.append("Stochastic overbought (> 80)")
            else:
                conditions_failed.append("Stochastic neutral zone")
        
        # Calculate signal
        total_conditions = 3
        met_count = len(conditions_met)
        strength = (met_count / total_conditions) * 100
        
        if met_count == total_conditions:
            signal = "BUY"
            interpretation = "Strong mean reversion buy signal"
        elif len([c for c in conditions_failed if "overbought" in c.lower()]) >= 2:
            signal = "SELL"
            interpretation = "Multiple overbought conditions detected"
        else:
            signal = "NEUTRAL"
            interpretation = f"Mixed signals ({met_count}/{total_conditions} conditions met)"
        
        return StrategySignal(
            strategy_name="Mean Reversion",
            signal=signal,
            strength=strength,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
            interpretation=interpretation
        )
    
    def volatility_breakout_strategy(self) -> StrategySignal:
        """
        Volatility Breakout Strategy using Donchian Channel, MACD, and ATR
        
        Buy Conditions:
        - Price breaks above Donchian Upper Band
        - MACD line crosses above Signal line
        - ATR rising (volatility expansion)
        
        Returns:
            StrategySignal: Signal details and analysis
        """
        if self.latest is None:
            return StrategySignal(
                strategy_name="Volatility Breakout",
                signal="NEUTRAL",
                strength=0,
                conditions_met=[],
                conditions_failed=["No data available"],
                interpretation="Insufficient data"
            )
            
        conditions_met = []
        conditions_failed = []
        
        # Check MACD condition
        macd = self.latest.get('MACD_12_26', None)
        macd_signal = self.latest.get('MACD_Signal_9', None)
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                conditions_met.append("MACD above Signal line")
            else:
                conditions_failed.append("MACD below Signal line")
        
        # Check ATR condition
        atr = self.latest.get('ATR_14', None)
        if atr is not None:
            # Compare current ATR with previous periods
            atr_prev = self.df['ATR_14'].iloc[-5:-1].mean()  # Average of last 4 periods
            if atr > atr_prev:
                conditions_met.append("ATR rising (volatility expansion)")
            else:
                conditions_failed.append("ATR falling or stable")
        
        # Calculate signal
        total_conditions = 2  # Excluding Donchian for now
        met_count = len(conditions_met)
        strength = (met_count / total_conditions) * 100
        
        if met_count == total_conditions:
            signal = "BUY"
            interpretation = "Strong volatility breakout signal"
        elif met_count == 0:
            signal = "SELL"
            interpretation = "No breakout conditions met"
        else:
            signal = "NEUTRAL"
            interpretation = f"Mixed signals ({met_count}/{total_conditions} conditions met)"
        
        return StrategySignal(
            strategy_name="Volatility Breakout",
            signal=signal,
            strength=strength,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
            interpretation=interpretation
        )
    
    def volume_analysis_strategy(self) -> StrategySignal:
        """
        Volume Analysis Strategy using OBV and VWAP
        
        Buy Conditions:
        - OBV is rising
        - Price > VWAP
        
        Returns:
            StrategySignal: Signal details and analysis
        """
        if self.latest is None:
            return StrategySignal(
                strategy_name="Volume Analysis",
                signal="NEUTRAL",
                strength=0,
                conditions_met=[],
                conditions_failed=["No data available"],
                interpretation="Insufficient data"
            )
            
        conditions_met = []
        conditions_failed = []
        current_price = self.latest['close']
        
        # Check VWAP condition
        vwap = self.latest.get('VWAP', None)
        if vwap is not None:
            if current_price > vwap:
                conditions_met.append("Price above VWAP")
            else:
                conditions_failed.append("Price below VWAP")
        
        # Check OBV trend (simplified)
        if 'volume' in self.df.columns:
            obv = (self.df['volume'] * np.where(self.df['close'] > self.df['close'].shift(1), 1, -1)).cumsum()
            obv_trend = obv.iloc[-1] > obv.iloc[-5:].mean()  # Compare current to 5-period average
            if obv_trend:
                conditions_met.append("OBV rising")
            else:
                conditions_failed.append("OBV falling")
        
        # Calculate signal
        total_conditions = 2
        met_count = len(conditions_met)
        strength = (met_count / total_conditions) * 100
        
        if met_count == total_conditions:
            signal = "BUY"
            interpretation = "Strong volume confirmation"
        elif met_count == 0:
            signal = "SELL"
            interpretation = "Weak volume conditions"
        else:
            signal = "NEUTRAL"
            interpretation = f"Mixed volume signals ({met_count}/{total_conditions} conditions met)"
        
        return StrategySignal(
            strategy_name="Volume Analysis",
            signal=signal,
            strength=strength,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
            interpretation=interpretation
        )
    
    def analyze_all(self) -> List[StrategySignal]:
        """
        Run all trading strategies and return their signals
        
        Returns:
            List[StrategySignal]: List of signals from all strategies
        """
        return [
            self.trend_following_strategy(),
            self.mean_reversion_strategy(),
            self.volatility_breakout_strategy(),
            self.volume_analysis_strategy()
        ] 