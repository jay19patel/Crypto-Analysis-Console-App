import numpy as np
import pandas as pd
import pandas_ta as ta
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics

from src.database.schemas import TradingSignal, MarketData, SignalType, StrategyStats, StrategyResult
from src.strategies.base_strategy import BaseStrategy
from src.config import get_trading_config

class EMAStrategy(BaseStrategy):
    """EMA Crossover Strategy using 9EMA and 15EMA"""
    def __init__(self, symbol: str, historical_data_provider):
        super().__init__(symbol, name=f"EMA_{symbol}")
        self.historical_data_provider = historical_data_provider
        self.trading_config = get_trading_config()

    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        df = self.historical_data_provider.get_historical_data(self.symbol, "15m")
        if df.shape[0] < 16:
            return TradingSignal(
                signal=SignalType.WAIT,
                symbol=self.symbol,
                confidence=0.0,
                strategy_name=self.name,
                price=market_data.price
            )
        # Calculate EMAs
        df['ema9'] = ta.ema(df['close'], length=9)
        df['ema15'] = ta.ema(df['close'], length=15)
        # Use last two candles for crossover
        prev = df.iloc[-2]
        last = df.iloc[-1]
        signal = SignalType.WAIT
        confidence = 50.0
        if prev['ema9'] < prev['ema15'] and last['ema9'] > last['ema15']:
            signal = SignalType.BUY
            confidence = 90.0
        elif prev['ema9'] > prev['ema15'] and last['ema9'] < last['ema15']:
            signal = SignalType.SELL
            confidence = 90.0

        # self.logger.debug(f"RSI Strategy {self.symbol}: RSI={current_rsi:.2f}, Signal={signal.value}, Confidence={confidence:.1f}%")
        
        return TradingSignal(
            signal=signal,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.0,  # Risk manager will calculate proper quantity based on balance
            leverage=self.trading_config["default_leverage"]
        )


class RSIStrategy(BaseStrategy):
    """RSI Strategy: Buy when RSI < 30, Sell when RSI > 70"""
    
    def __init__(self, symbol: str, historical_data_provider):
        super().__init__(symbol, name=f"RSI_{symbol}")
        self.historical_data_provider = historical_data_provider
        self.trading_config = get_trading_config()
        
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """
        Generate trading signal based on RSI levels:
        - RSI < 30: BUY signal (oversold)
        - RSI > 70: SELL signal (overbought)
        - 30 <= RSI <= 70: WAIT (neutral zone)
        """
        # Get historical data
        df = self.historical_data_provider.get_historical_data(self.symbol, "15m")
        
        # Need at least 14 candles for RSI calculation
        if df.shape[0] < 14:
            return TradingSignal(
                signal=SignalType.WAIT,
                symbol=self.symbol,
                confidence=0.0,
                strategy_name=self.name,
                price=market_data.price
            )
        
        # Calculate RSI using pandas_ta
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # Get the latest RSI value
        current_rsi = df['rsi'].iloc[-1]
        
        # Initialize signal variables
        signal = SignalType.WAIT
        confidence = 50.0
        
        # Generate signals based on RSI levels
        if current_rsi < 30:
            # Oversold condition - BUY signal
            signal = SignalType.BUY
            # Higher confidence for more oversold conditions
            confidence = min(95.0, 70.0 + (30 - current_rsi) * 2)
        elif current_rsi > 70:
            # Overbought condition - SELL signal
            signal = SignalType.SELL
            # Higher confidence for more overbought conditions
            confidence = min(95.0, 70.0 + (current_rsi - 70) * 2)
        else:
            # Neutral zone - WAIT
            signal = SignalType.WAIT
            confidence = 50.0
        
        # Log RSI value and signal for debugging
        self.logger.debug(f"RSI Strategy {self.symbol}: RSI={current_rsi:.2f}, Signal={signal.value}, Confidence={confidence:.1f}%")
        
        return TradingSignal(
            signal=signal,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.0,  # Risk manager will calculate proper quantity based on balance
            leverage=self.trading_config["default_leverage"]
        ) 