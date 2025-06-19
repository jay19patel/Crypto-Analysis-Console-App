import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

class SignalType(Enum):
    """Enumeration for signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    NEUTRAL = "NEUTRAL"

class ConfidenceLevel(Enum):
    """Enumeration for confidence levels"""
    VERY_LOW = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    VERY_HIGH = 5

@dataclass
class StrategyResult:
    """Data class for trading strategy results"""
    name: str
    signal: SignalType
    confidence: ConfidenceLevel
    strength: float  # 0-100 percentage
    interpretation: str
    conditions_met: List[str]
    conditions_failed: List[str]
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.required_indicators = []
    
    @abstractmethod
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """
        Analyze market data and generate trading signal
        
        Args:
            df: Historical price data with indicators
            latest_data: Latest price and indicator data
            
        Returns:
            StrategyResult: Analysis result with signal and details
        """
        pass
    
    def validate_data(self, df: pd.DataFrame) -> bool:
        """
        Validate that required indicators are present in data
        
        Args:
            df: DataFrame to validate
            
        Returns:
            bool: True if all required indicators are present
        """
        for indicator in self.required_indicators:
            if indicator not in df.columns:
                return False
        return True

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
        price_above_emas = current_price > ema_5
        
        if ema_aligned_up:
            conditions_met.append("EMAs are aligned for uptrend (5>15>50)")
        else:
            conditions_failed.append("EMAs not aligned for uptrend")
        
        if price_above_emas:
            conditions_met.append("Price is above short-term EMA")
        else:
            conditions_failed.append("Price is below short-term EMA")
        
        # RSI Filter
        rsi = latest_data['RSI_14']
        if 30 <= rsi <= 70:
            conditions_met.append("RSI in normal range (not overbought/oversold)")
        elif rsi > 70:
            conditions_failed.append("RSI overbought (>70)")
        else:
            conditions_failed.append("RSI oversold (<30)")
        
        # Calculate strength
        strength = (len(conditions_met) / (len(conditions_met) + len(conditions_failed))) * 100
        
        # Determine signal
        if strength >= 80:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong uptrend with all conditions met"
        elif strength >= 60:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Moderate uptrend signal"
        elif strength <= 20:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong downtrend signal"
        elif strength <= 40:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Moderate downtrend signal"
        else:
            signal = SignalType.HOLD
            confidence = ConfidenceLevel.LOW
            interpretation = "Mixed signals, hold position"
        
        # Calculate risk management levels
        atr = latest_data['ATR_14']
        entry_price = current_price
        stop_loss = current_price - (2 * atr) if signal == SignalType.BUY else current_price + (2 * atr)
        take_profit = current_price + (3 * atr) if signal == SignalType.BUY else current_price - (3 * atr)
        risk_reward_ratio = 1.5  # 3:2 ratio
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward_ratio
        )

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
        
        # Check for crossover (need at least 2 periods)
        if len(df) >= 2:
            prev_macd = df.iloc[-2]['MACD_12_26_9']
            prev_signal = df.iloc[-2]['MACDs_12_26_9']
            
            # Bullish crossover
            bullish_crossover = (prev_macd <= prev_signal) and (macd_line > signal_line)
            # Bearish crossover
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
        if macd_line > 0:
            conditions_met.append("MACD above zero line")
        else:
            conditions_failed.append("MACD below zero line")
        
        # Calculate strength
        strength = (len(conditions_met) / (len(conditions_met) + len(conditions_failed))) * 100
        
        # Determine signal
        if bullish_crossover and strength >= 66:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong bullish MACD crossover"
        elif bearish_crossover and strength <= 33:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.HIGH
            interpretation = "Strong bearish MACD crossover"
        elif macd_line > signal_line:
            signal = SignalType.BUY
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "MACD above signal line"
        elif macd_line < signal_line:
            signal = SignalType.SELL
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "MACD below signal line"
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
        
        # RSI levels
        if rsi < 30:
            conditions_met.append("RSI oversold (<30)")
            signal = SignalType.BUY
            confidence = ConfidenceLevel.HIGH
            interpretation = "RSI oversold - potential buy signal"
        elif rsi > 70:
            conditions_met.append("RSI overbought (>70)")
            signal = SignalType.SELL
            confidence = ConfidenceLevel.HIGH
            interpretation = "RSI overbought - potential sell signal"
        elif 40 <= rsi <= 60:
            conditions_met.append("RSI in neutral zone")
            signal = SignalType.HOLD
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "RSI neutral - hold position"
        else:
            conditions_failed.append("RSI in uncertain range")
            signal = SignalType.NEUTRAL
            confidence = ConfidenceLevel.LOW
            interpretation = "RSI signals unclear"
        
        # Check for divergence (basic implementation)
        if len(df) >= 10:
            recent_highs = df['high'].tail(10)
            recent_rsi = df['RSI_14'].tail(10)
            
            price_trend = recent_highs.iloc[-1] > recent_highs.iloc[0]
            rsi_trend = recent_rsi.iloc[-1] > recent_rsi.iloc[0]
            
            if price_trend != rsi_trend:
                conditions_met.append("Potential RSI divergence detected")
            else:
                conditions_failed.append("No RSI divergence")
        
        strength = (len(conditions_met) / (len(conditions_met) + len(conditions_failed))) * 100
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        )

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
            signal = SignalType.BUY
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Stochastic oversold condition"
        elif stoch_k > 80 and stoch_d > 80:
            conditions_met.append("Stochastic overbought (>80)")
            signal = SignalType.SELL
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Stochastic overbought condition"
        else:
            conditions_failed.append("Stochastic in normal range")
            signal = SignalType.NEUTRAL
            confidence = ConfidenceLevel.LOW
            interpretation = "No clear stochastic signal"
        
        # Check for crossovers
        if len(df) >= 2:
            prev_k = df.iloc[-2]['STOCHk_14_3_3']
            prev_d = df.iloc[-2]['STOCHd_14_3_3']
            
            if prev_k <= prev_d and stoch_k > stoch_d:
                conditions_met.append("%K crossed above %D")
            elif prev_k >= prev_d and stoch_k < stoch_d:
                conditions_met.append("%K crossed below %D")
            else:
                conditions_failed.append("No recent crossover")
        
        strength = (len(conditions_met) / max(1, len(conditions_met) + len(conditions_failed))) * 100
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        )

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
        
        # Price vs VWAP
        if current_price > vwap:
            conditions_met.append("Price above VWAP")
            signal = SignalType.BUY
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Price trading above VWAP - bullish"
        elif current_price < vwap:
            conditions_met.append("Price below VWAP")
            signal = SignalType.SELL
            confidence = ConfidenceLevel.MEDIUM
            interpretation = "Price trading below VWAP - bearish"
        else:
            conditions_failed.append("Price at VWAP")
            signal = SignalType.NEUTRAL
            confidence = ConfidenceLevel.LOW
            interpretation = "Price at VWAP - neutral"
        
        # Distance from VWAP
        distance_pct = abs((current_price - vwap) / vwap) * 100
        
        if distance_pct > 2:
            conditions_met.append(f"Significant distance from VWAP ({distance_pct:.2f}%)")
        else:
            conditions_failed.append("Close to VWAP")
        
        strength = (len(conditions_met) / max(1, len(conditions_met) + len(conditions_failed))) * 100
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        )

class StrategyManager:
    """Manager class for all trading strategies"""
    
    def __init__(self):
        self.strategies: List[BaseStrategy] = [
            TrendFollowingStrategy(),
            MACDCrossoverStrategy(),
            RSIStrategy(),
            StochasticStrategy(),
            VWAPStrategy()
        ]
    
    def add_strategy(self, strategy: BaseStrategy):
        """Add a new strategy to the manager"""
        self.strategies.append(strategy)
    
    def remove_strategy(self, strategy_name: str):
        """Remove a strategy by name"""
        self.strategies = [s for s in self.strategies if s.name != strategy_name]
    
    def get_strategy(self, strategy_name: str) -> Optional[BaseStrategy]:
        """Get a strategy by name"""
        for strategy in self.strategies:
            if strategy.name == strategy_name:
                return strategy
        return None
    
    def analyze_all(self, df: pd.DataFrame) -> List[StrategyResult]:
        """
        Run all strategies and return results
        
        Args:
            df: DataFrame with price data and indicators
            
        Returns:
            List of StrategyResult objects
        """
        if df is None or df.empty:
            return []
        
        results = []
        latest_data = df.iloc[-1]
        
        for strategy in self.strategies:
            try:
                if strategy.validate_data(df):
                    result = strategy.analyze(df, latest_data)
                    results.append(result)
                else:
                    # Create a result indicating missing data
                    result = StrategyResult(
                        name=strategy.name,
                        signal=SignalType.NEUTRAL,
                        confidence=ConfidenceLevel.VERY_LOW,
                        strength=0,
                        interpretation="Missing required indicators",
                        conditions_met=[],
                        conditions_failed=[f"Missing indicators: {strategy.required_indicators}"]
                    )
                    results.append(result)
            except Exception as e:
                # Create error result
                result = StrategyResult(
                    name=strategy.name,
                    signal=SignalType.NEUTRAL,
                    confidence=ConfidenceLevel.VERY_LOW,
                    strength=0,
                    interpretation=f"Error: {str(e)}",
                    conditions_met=[],
                    conditions_failed=[f"Strategy execution failed: {str(e)}"]
                )
                results.append(result)
        
        return results
    
    def get_consensus_signal(self, results: List[StrategyResult]) -> Dict[str, Any]:
        """
        Calculate consensus signal from all strategy results
        
        Args:
            results: List of strategy results
            
        Returns:
            Dictionary with consensus information
        """
        if not results:
            return {
                'signal': SignalType.NEUTRAL,
                'confidence': ConfidenceLevel.VERY_LOW,
                'strength': 0,
                'interpretation': 'No strategy results available'
            }
        
        # Count signals
        buy_signals = sum(1 for r in results if r.signal == SignalType.BUY)
        sell_signals = sum(1 for r in results if r.signal == SignalType.SELL)
        hold_signals = sum(1 for r in results if r.signal == SignalType.HOLD)
        neutral_signals = sum(1 for r in results if r.signal == SignalType.NEUTRAL)
        
        total_signals = len(results)
        
        # Calculate weighted consensus
        buy_strength = sum(r.strength for r in results if r.signal == SignalType.BUY)
        sell_strength = sum(r.strength for r in results if r.signal == SignalType.SELL)
        
        # Determine consensus
        if buy_signals > sell_signals and buy_signals >= total_signals * 0.6:
            consensus_signal = SignalType.BUY
            confidence = ConfidenceLevel.HIGH if buy_signals >= total_signals * 0.8 else ConfidenceLevel.MEDIUM
            strength = buy_strength / max(1, buy_signals)
            interpretation = f"Strong consensus BUY ({buy_signals}/{total_signals} strategies)"
        elif sell_signals > buy_signals and sell_signals >= total_signals * 0.6:
            consensus_signal = SignalType.SELL
            confidence = ConfidenceLevel.HIGH if sell_signals >= total_signals * 0.8 else ConfidenceLevel.MEDIUM
            strength = sell_strength / max(1, sell_signals)
            interpretation = f"Strong consensus SELL ({sell_signals}/{total_signals} strategies)"
        else:
            consensus_signal = SignalType.NEUTRAL
            confidence = ConfidenceLevel.LOW
            strength = 50
            interpretation = f"Mixed signals (B:{buy_signals}, S:{sell_signals}, H:{hold_signals}, N:{neutral_signals})"
        
        return {
            'signal': consensus_signal,
            'confidence': confidence,
            'strength': strength,
            'interpretation': interpretation,
            'buy_count': buy_signals,
            'sell_count': sell_signals,
            'hold_count': hold_signals,
            'neutral_count': neutral_signals
        } 