import pandas as pd
from typing import List, Optional, Dict, Any
from .base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

class StrategyManager:
    """Manager class for all trading strategies"""
    
    def __init__(self):
        """Initialize with empty strategies list"""
        self.strategies: List[BaseStrategy] = []
        self._load_default_strategies()
    
    def _load_default_strategies(self):
        """Load default strategies"""
        try:
            from .trend_strategy import TrendFollowingStrategy
            from .macd_strategy import MACDCrossoverStrategy
            from .rsi_strategy import RSIStrategy
            from .stochastic_strategy import StochasticStrategy
            from .vwap_strategy import VWAPStrategy
            from .advanced_strategy import AdvancedTrendStrategy
            
            self.strategies = [
                TrendFollowingStrategy(),
                MACDCrossoverStrategy(),
                RSIStrategy(),
                StochasticStrategy(),
                VWAPStrategy(),
                AdvancedTrendStrategy()
            ]
        except ImportError as e:
            print(f"Warning: Could not load some strategies: {e}")
    
    def add_strategy(self, strategy: BaseStrategy) -> bool:
        """Add a new strategy"""
        if any(s.name == strategy.name for s in self.strategies):
            return False
        self.strategies.append(strategy)
        return True
    
    def analyze_all(self, df: pd.DataFrame) -> List[StrategyResult]:
        """Run all strategies and return results"""
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
                    result = StrategyResult(
                        name=strategy.name,
                        signal=SignalType.NEUTRAL,
                        confidence=ConfidenceLevel.VERY_LOW,
                        strength=0,
                        interpretation="Missing required indicators",
                        conditions_met=[],
                        conditions_failed=["Missing indicators"]
                    )
                    results.append(result)
            except Exception as e:
                result = StrategyResult(
                    name=strategy.name,
                    signal=SignalType.NEUTRAL,
                    confidence=ConfidenceLevel.VERY_LOW,
                    strength=0,
                    interpretation=f"Error: {str(e)}",
                    conditions_met=[],
                    conditions_failed=[f"Strategy failed: {str(e)}"]
                )
                results.append(result)
        
        return results
    
    def get_consensus_signal(self, results: List[StrategyResult]) -> Dict[str, Any]:
        """Calculate consensus signal from strategy results"""
        if not results:
            return {
                'signal': 'NEUTRAL',
                'confidence': 'VERY_LOW',
                'strength': 0,
                'interpretation': 'No strategy results'
            }
        
        # Count signals
        buy_count = sum(1 for r in results if r.signal == SignalType.BUY)
        sell_count = sum(1 for r in results if r.signal == SignalType.SELL)
        hold_count = sum(1 for r in results if r.signal == SignalType.HOLD)
        neutral_count = sum(1 for r in results if r.signal == SignalType.NEUTRAL)
        
        total = len(results)
        
        # Determine consensus
        if buy_count > sell_count and buy_count >= total * 0.6:
            signal = 'BUY'
            confidence = 'HIGH' if buy_count >= total * 0.8 else 'MEDIUM'
            strength = (buy_count / total) * 100
            interpretation = f"Consensus BUY ({buy_count}/{total})"
        elif sell_count > buy_count and sell_count >= total * 0.6:
            signal = 'SELL'
            confidence = 'HIGH' if sell_count >= total * 0.8 else 'MEDIUM'
            strength = (sell_count / total) * 100
            interpretation = f"Consensus SELL ({sell_count}/{total})"
        else:
            signal = 'NEUTRAL'
            confidence = 'LOW'
            strength = 50
            interpretation = f"Mixed signals (B:{buy_count}, S:{sell_count})"
        
        return {
            'signal': signal,
            'confidence': confidence,
            'strength': strength,
            'interpretation': interpretation
        } 