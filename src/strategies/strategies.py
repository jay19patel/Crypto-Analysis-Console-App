import random
import time
import logging
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import statistics

from src.database.schemas import TradingSignal, MarketData, SignalType, StrategyStats, StrategyResult


class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, symbol: str, name: str):
        self.symbol = symbol
        self.name = name
        self.logger = logging.getLogger(f"strategy.{name}")
        self.price_history = []
        self.last_signal = SignalType.WAIT
        self.signal_count = {"BUY": 0, "SELL": 0, "WAIT": 0}
        self.lock = threading.Lock()
        self.execution_times = []
        
    @abstractmethod
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """Generate trading signal based on market data"""
        pass
    
    def update_price_history(self, price: float):
        """Update price history for technical analysis"""
        with self.lock:
            self.price_history.append(price)
            # Keep only last 100 prices for memory efficiency
            if len(self.price_history) > 100:
                self.price_history.pop(0)
    
    def get_stats(self) -> StrategyStats:
        """Get strategy statistics"""
        with self.lock:
            total_signals = sum(self.signal_count.values())
            avg_execution_time = statistics.mean(self.execution_times) if self.execution_times else 0.0
            
            return StrategyStats(
                name=self.name,
                symbol=self.symbol,
                total_signals=total_signals,
                signal_distribution=self.signal_count.copy(),
                last_signal=self.last_signal.value,
                price_history_length=len(self.price_history)
            )
    
    def execute_strategy(self, market_data: MarketData) -> StrategyResult:
        """Execute strategy and return result with timing"""
        start_time = time.time()
        success = True
        error_message = None
        
        try:
            signal = self.generate_signal(market_data)
            execution_time = time.time() - start_time
            
            # Update statistics
            with self.lock:
                self.signal_count[signal.signal.value] += 1
                self.last_signal = signal.signal
                self.execution_times.append(execution_time)
                # Keep only last 50 execution times
                if len(self.execution_times) > 50:
                    self.execution_times.pop(0)
            
            return StrategyResult(
                strategy_name=self.name,
                symbol=self.symbol,
                signal=signal,
                execution_time=execution_time,
                success=success,
                error_message=error_message
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            success = False
            error_message = str(e)
            self.logger.error(f"Error in strategy {self.name}: {e}")
            
            return StrategyResult(
                strategy_name=self.name,
                symbol=self.symbol,
                signal=TradingSignal(
                    signal=SignalType.WAIT,
                    symbol=self.symbol,
                    confidence=0.0,
                    strategy_name=self.name,
                    price=market_data.price
                ),
                execution_time=execution_time,
                success=success,
                error_message=error_message
            )


class RandomStrategy(BaseStrategy):
    """Random Strategy - generates random signals"""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, f"Random_{symbol}")
        self.signals = [SignalType.BUY, SignalType.SELL, SignalType.WAIT]
        
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """Generate random signal"""
        self.update_price_history(market_data.price)
        
        # Random signal selection
        signal_type = random.choice(self.signals)
        
        # Random confidence between 50-95%
        confidence = random.uniform(50.0, 95.0)
        
        return TradingSignal(
            signal=signal_type,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.01
        )


class VolatilityStrategy(BaseStrategy):
    """Volatility-based Strategy"""
    
    def __init__(self, symbol: str, lookback: int = 20, threshold: float = 0.02):
        super().__init__(symbol, f"Volatility_{lookback}_{symbol}")
        self.lookback = lookback
        self.threshold = threshold
        
    def calculate_volatility(self, prices: List[float]) -> float:
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0.0
        
        # Calculate price changes
        changes = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        # Calculate standard deviation of changes
        if len(changes) > 0:
            return statistics.stdev(changes)
        return 0.0
    
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """Generate signal based on volatility"""
        self.update_price_history(market_data.price)
        
        if len(self.price_history) < self.lookback:
            return TradingSignal(
                signal=SignalType.WAIT,
                symbol=self.symbol,
                confidence=0.0,
                strategy_name=self.name,
                price=market_data.price
            )
        
        # Calculate volatility
        recent_prices = self.price_history[-self.lookback:]
        volatility = self.calculate_volatility(recent_prices)
        
        # Calculate current price change
        if len(self.price_history) >= 2:
            current_change = (market_data.price - self.price_history[-2]) / self.price_history[-2]
        else:
            current_change = 0.0
        
        # Generate signal based on volatility and price movement
        if volatility > self.threshold:
            if current_change > 0:
                signal_type = SignalType.BUY
                confidence = min(95.0, 70.0 + abs(current_change) * 1000)
            else:
                signal_type = SignalType.SELL
                confidence = min(95.0, 70.0 + abs(current_change) * 1000)
        else:
            signal_type = SignalType.WAIT
            confidence = 50.0
        
        return TradingSignal(
            signal=signal_type,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.01
        )


class MovingAverageStrategy(BaseStrategy):
    """Moving Average Crossover Strategy"""
    
    def __init__(self, symbol: str, short_window: int = 5, long_window: int = 20):
        super().__init__(symbol, f"MA_{short_window}_{long_window}_{symbol}")
        self.short_window = short_window
        self.long_window = long_window
        
    def calculate_moving_average(self, prices: List[float], window: int) -> float:
        """Calculate moving average"""
        if len(prices) < window:
            return prices[-1] if prices else 0.0
        return sum(prices[-window:]) / window
    
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """Generate signal based on moving average crossover"""
        self.update_price_history(market_data.price)
        
        if len(self.price_history) < self.long_window:
            return TradingSignal(
                signal=SignalType.WAIT,
                symbol=self.symbol,
                confidence=0.0,
                strategy_name=self.name,
                price=market_data.price
            )
        
        # Calculate moving averages
        short_ma = self.calculate_moving_average(self.price_history, self.short_window)
        long_ma = self.calculate_moving_average(self.price_history, self.long_window)
        
        # Generate signal
        if short_ma > long_ma and self.last_signal != SignalType.BUY:
            signal_type = SignalType.BUY
            confidence = min(95.0, 70.0 + abs(short_ma - long_ma) / long_ma * 100)
        elif short_ma < long_ma and self.last_signal != SignalType.SELL:
            signal_type = SignalType.SELL
            confidence = min(95.0, 70.0 + abs(short_ma - long_ma) / long_ma * 100)
        else:
            signal_type = SignalType.WAIT
            confidence = 50.0
        
        return TradingSignal(
            signal=signal_type,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.01
        )


class RSIStrategy(BaseStrategy):
    """RSI (Relative Strength Index) Strategy"""
    
    def __init__(self, symbol: str, period: int = 14, overbought: float = 70.0, oversold: float = 30.0):
        super().__init__(symbol, f"RSI_{period}_{symbol}")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        
    def calculate_rsi(self, prices: List[float]) -> float:
        """Calculate RSI value"""
        if len(prices) < self.period + 1:
            return 50.0  # Neutral RSI
        
        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        # Separate gains and losses
        gains = [max(0, delta) for delta in deltas]
        losses = [abs(min(0, delta)) for delta in deltas]
        
        # Calculate average gain and loss
        avg_gain = sum(gains[-self.period:]) / self.period
        avg_loss = sum(losses[-self.period:]) / self.period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signal(self, market_data: MarketData) -> TradingSignal:
        """Generate signal based on RSI"""
        self.update_price_history(market_data.price)
        
        if len(self.price_history) < self.period + 1:
            return TradingSignal(
                signal=SignalType.WAIT,
                symbol=self.symbol,
                confidence=0.0,
                strategy_name=self.name,
                price=market_data.price
            )
        
        rsi = self.calculate_rsi(self.price_history)
        
        if rsi < self.oversold:
            signal_type = SignalType.BUY
            confidence = min(95.0, 70.0 + (self.oversold - rsi) / self.oversold * 25)
        elif rsi > self.overbought:
            signal_type = SignalType.SELL
            confidence = min(95.0, 70.0 + (rsi - self.overbought) / (100 - self.overbought) * 25)
        else:
            signal_type = SignalType.WAIT
            confidence = 50.0
        
        return TradingSignal(
            signal=signal_type,
            symbol=self.symbol,
            confidence=confidence,
            strategy_name=self.name,
            price=market_data.price,
            quantity=0.01
        ) 