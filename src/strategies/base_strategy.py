import logging
import threading
import time
import statistics
from abc import ABC, abstractmethod
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