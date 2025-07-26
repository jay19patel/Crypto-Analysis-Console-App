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

class EMAStrategy(BaseStrategy):
    """EMA Crossover Strategy using 9EMA and 15EMA"""
    def __init__(self, symbol: str, historical_data_provider):
        super().__init__(symbol, name=f"EMA_{symbol}")
        self.historical_data_provider = historical_data_provider

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
        return TradingSignal(
            # signal=signal,
            signal=SignalType.BUY,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price
        ) 