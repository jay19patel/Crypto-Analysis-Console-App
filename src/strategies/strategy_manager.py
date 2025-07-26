import logging
import threading
import time
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from src.database.schemas import (
    MarketData, TradingSignal, SignalType, StrategyManagerResult, 
    StrategyResult, StrategyStats
)
from src.strategies.base_strategy import BaseStrategy
import statistics
import pandas as pd
from src.config import get_settings
import importlib


class StrategyManager:
    """Manager for all trading strategies with parallel execution"""
    
    def __init__(self, max_workers: int = 4):
        self.strategies: Dict[str, List[BaseStrategy]] = {}
        self.logger = logging.getLogger("strategy_manager")
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.Lock()
        self.settings = get_settings()
        
        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0
        
    def add_strategy(self, strategy: BaseStrategy):
        """Add a strategy to the manager"""
        with self.lock:
            if strategy.symbol not in self.strategies:
                self.strategies[strategy.symbol] = []
            
            self.strategies[strategy.symbol].append(strategy)
            self.logger.info(f"Added strategy {strategy.name} for {strategy.symbol}")
    
    def add_default_strategies(self, symbols: List[str], historical_data_provider):
        """Add default strategies for given symbols, using STRATEGY_CLASSES from config.py"""
        for symbol in symbols:
            for class_name in self.settings.STRATEGY_CLASSES:
                module = importlib.import_module("src.strategies.strategies")
                strategy_class = getattr(module, class_name)
                strategy = strategy_class(symbol, historical_data_provider)
                self.add_strategy(strategy)
        self.logger.info(f"Added default strategies for {len(symbols)} symbols from config STRATEGY_CLASSES")
    
    def execute_strategies_parallel(self, symbol: str, market_data: MarketData) -> StrategyManagerResult:
        """Execute all strategies for a symbol in parallel and return the best signal"""
        if symbol not in self.strategies:
            self.logger.warning(f"No strategies found for symbol {symbol}")
            return StrategyManagerResult(
                selected_signal=TradingSignal(
                    signal=SignalType.WAIT,
                    symbol=symbol,
                    confidence=0.0,
                    strategy_name="NoStrategy",
                    price=market_data.price
                ),
                all_signals=[],
                strategy_results=[]
            )
        
        strategies = self.strategies[symbol]
        strategy_results = []
        
        # Execute strategies in parallel
        futures = []
        for strategy in strategies:
            future = self.executor.submit(strategy.execute_strategy, market_data)
            futures.append(future)
        
        # Collect results
        for future in as_completed(futures):
            try:
                result = future.result()
                strategy_results.append(result)
                self.total_executions += 1
                
                if result.success:
                    self.successful_executions += 1
                else:
                    self.failed_executions += 1
                    
            except Exception as e:
                self.logger.error(f"Error executing strategy: {e}")
                self.failed_executions += 1
        
        # Extract all signals
        all_signals = [result.signal for result in strategy_results if result.success]
        
        # Select the best signal based on confidence
        selected_signal = self._select_best_signal(all_signals)
        
        return StrategyManagerResult(
            selected_signal=selected_signal,
            all_signals=all_signals,
            strategy_results=strategy_results
        )
    
    def _select_best_signal(self, signals: List[TradingSignal]) -> TradingSignal:
        """Select the best signal based on confidence and signal type"""
        if not signals:
            return TradingSignal(
                signal=SignalType.WAIT,
                symbol="",
                confidence=0.0,
                strategy_name="NoSignal",
                price=0.0
            )
        
        # Filter out WAIT signals first
        actionable_signals = [s for s in signals if s.signal != SignalType.WAIT]
        
        if not actionable_signals:
            # If no actionable signals, return the highest confidence WAIT signal
            wait_signals = [s for s in signals if s.signal == SignalType.WAIT]
            if wait_signals:
                return max(wait_signals, key=lambda x: x.confidence)
            else:
                return signals[0]  # Return first signal if no WAIT signals
        
        # Select the signal with highest confidence
        best_signal = max(actionable_signals, key=lambda x: x.confidence)
        
        # Log the selection
        self.logger.info(f"Selected signal: {best_signal.signal} from {best_signal.strategy_name} "
                        f"with confidence {best_signal.confidence:.1f}%")
        
        return best_signal
    
    def get_all_symbols(self) -> List[str]:
        """Get all symbols with strategies"""
        with self.lock:
            return list(self.strategies.keys())
    
    def get_strategy_stats(self) -> Dict[str, List[StrategyStats]]:
        """Get statistics for all strategies"""
        stats = {}
        with self.lock:
            for symbol, strategies in self.strategies.items():
                stats[symbol] = [strategy.get_stats() for strategy in strategies]
        return stats
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "success_rate": (self.successful_executions / self.total_executions * 100) 
                          if self.total_executions > 0 else 0.0,
            "active_symbols": len(self.strategies),
            "total_strategies": sum(len(strategies) for strategies in self.strategies.values())
        }
    
    def shutdown(self):
        """Shutdown the strategy manager"""
        self.logger.info("Shutting down strategy manager...")
        self.executor.shutdown(wait=True)
        self.logger.info("Strategy manager shutdown complete") 