import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
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
    
    def calculate_risk_management(self, current_price: float, atr: float, signal: SignalType) -> Dict[str, float]:
        """
        Calculate risk management levels
        
        Args:
            current_price: Current market price
            atr: Average True Range value
            signal: Trading signal
            
        Returns:
            Dictionary with risk management levels
        """
        if signal == SignalType.BUY:
            stop_loss = current_price - (2 * atr)
            take_profit = current_price + (3 * atr)
        elif signal == SignalType.SELL:
            stop_loss = current_price + (2 * atr)
            take_profit = current_price - (3 * atr)
        else:
            return {}
        
        risk_amount = abs(current_price - stop_loss)
        reward_amount = abs(take_profit - current_price)
        risk_reward_ratio = reward_amount / risk_amount if risk_amount > 0 else 0
        
        return {
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward_ratio': risk_reward_ratio
        } 