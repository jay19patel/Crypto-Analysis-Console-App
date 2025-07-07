#!/usr/bin/env python3
"""
Real-time Random Strategy with Performance Tracking
Generates trading signals with configurable probabilities and execution time monitoring
"""

import logging
import random
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import json

from src.config import get_settings

class StrategyLogger:
    """Enhanced logging system for strategy operations"""
    
    def __init__(self, module_name: str = "Strategy"):
        self.module_name = module_name
        self.logger = logging.getLogger(f"strategy.{module_name.lower()}")
    
    def log(self, level: str, category: str, message: str, data: Any = None, execution_time: float = None):
        """Enhanced logging with execution time and data"""
        # Format log message
        log_msg = f"{level.upper()} - [{self.module_name}] {category} | {message}"
        if execution_time is not None:
            log_msg += f" (Time: {execution_time:.3f}s)"
            
        # Add data if provided
        if data:
            try:
                data_str = json.dumps(data, default=str)
                log_msg += f" | Data: {data_str}"
            except:
                pass
        
        # Log using appropriate level
        getattr(self.logger, level.lower())(log_msg)

class OptimizedRandomStrategy:
    """High-performance random strategy for real-time signal generation"""
    
    def __init__(self):
        """Initialize optimized random strategy"""
        self.logger = StrategyLogger("RandomStrategy")
        self.settings = get_settings()
        
        # Strategy parameters from config
        self.buy_probability = self.settings.STRATEGY_BUY_PROBABILITY
        self.sell_probability = self.settings.STRATEGY_SELL_PROBABILITY
        self.wait_probability = 1.0 - (self.buy_probability + self.sell_probability)
        
        # Performance tracking
        self.signals_generated = 0
        self.signals_by_type = {"BUY": 0, "SELL": 0, "WAIT": 0}
        self.start_time = None
        
        # Real-time optimization
        self.last_signal_time = {}  # Symbol -> last signal time
        self.signal_cooldown = 30  # Minimum seconds between signals for same symbol
        
        # Operation timing
        self._operation_times = {}

    def _time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        class OperationTimer:
            def __init__(self, strategy, name):
                self.strategy = strategy
                self.name = name
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                execution_time = time.time() - self.start_time
                self.strategy._operation_times[self.name] = execution_time
                return execution_time
        
        return OperationTimer(self, operation_name)

    def generate_signal(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Generate optimized random trading signal"""
        with self._time_operation("signal_generation") as timer:
            try:
                # Check cooldown period
                current_time = time.time()
                last_signal = self.last_signal_time.get(symbol, 0)
                
                if current_time - last_signal < self.signal_cooldown:
                    signal_data = self._create_wait_signal(symbol, current_price, "Cooldown period active")
                    self.logger.log(
                        "debug", "Signal", f"Cooldown active for {symbol}",
                        {"symbol": symbol, "cooldown_remaining": round(self.signal_cooldown - (current_time - last_signal), 1)},
                        timer.__exit__(None, None, None)
                    )
                    return signal_data
                
                # Generate random number for signal determination
                rand_value = random.random()
                
                if rand_value < self.buy_probability:
                    signal = "BUY"
                    confidence = random.randint(65, 95)
                    self.last_signal_time[symbol] = current_time
                elif rand_value < (self.buy_probability + self.sell_probability):
                    signal = "SELL"
                    confidence = random.randint(65, 95)
                    self.last_signal_time[symbol] = current_time
                else:
                    signal = "WAIT"
                    confidence = random.randint(30, 60)
                
                # Update counters
                self.signals_generated += 1
                self.signals_by_type[signal] += 1
                
                signal_data = {
                    "symbol": symbol,
                    "signal": signal,
                    "confidence": confidence,
                    "current_price": current_price,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "strategy_name": "Optimized Random Strategy",
                    "analysis": {
                        "signal_id": f"random_{self.signals_generated}",
                        "reason": f"Random signal generation with {confidence}% confidence",
                        "market_condition": "Normal",
                        "risk_level": "Medium" if signal in ["BUY", "SELL"] else "Low"
                    }
                }
                
                # Log actionable signals
                if signal in ["BUY", "SELL"]:
                    self.logger.log(
                        "info", "Signal", f"Generated {signal} signal for {symbol}",
                        {"symbol": symbol, "price": current_price, "confidence": confidence},
                        timer.__exit__(None, None, None)
                    )
                
                return signal_data
                
            except Exception as e:
                self.logger.log(
                    "error", "Signal", f"Signal generation failed for {symbol}",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return self._create_wait_signal(symbol, current_price, f"Error: {str(e)}")
    
    def _create_wait_signal(self, symbol: str, current_price: float, reason: str) -> Dict[str, Any]:
        """Create a WAIT signal"""
        return {
            "symbol": symbol,
            "signal": "WAIT",
            "confidence": 0,
            "current_price": current_price,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy_name": "Optimized Random Strategy",
            "analysis": {
                "signal_id": "wait",
                "reason": reason,
                "market_condition": "Neutral",
                "risk_level": "Low"
            }
        }

    def get_strategy_performance(self) -> Dict[str, Any]:
        """Get detailed strategy performance metrics"""
        with self._time_operation("performance_stats") as timer:
            try:
                uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
                total_actionable = self.signals_by_type["BUY"] + self.signals_by_type["SELL"]
                
                stats = {
                    "strategy_name": "Optimized Random Strategy",
                    "status": "active",
                    "uptime_seconds": round(uptime, 2),
                    "signals_generated": self.signals_generated,
                    "signals_per_second": round(self.signals_generated / uptime, 3) if uptime > 0 else 0,
                    "signals_by_type": self.signals_by_type.copy(),
                    "actionable_signals": total_actionable,
                    "actionable_percentage": round((total_actionable / self.signals_generated) * 100, 2) if self.signals_generated > 0 else 0,
                    "configuration": {
                        "buy_probability": self.buy_probability,
                        "sell_probability": self.sell_probability,
                        "wait_probability": self.wait_probability,
                        "signal_cooldown": self.signal_cooldown
                    }
                }
                
                self.logger.log(
                    "info", "Performance", "Strategy performance metrics calculated",
                    stats,
                    timer.__exit__(None, None, None)
                )
                
                return stats
                
            except Exception as e:
                self.logger.log(
                    "error", "Performance", "Failed to calculate performance metrics",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return {}


class OptimizedStrategyManager:
    """High-performance strategy manager for real-time operations"""
    
    def __init__(self):
        """Initialize optimized strategy manager"""
        self.logger = StrategyLogger("StrategyManager")
        self.settings = get_settings()
        
        # Initialize optimized random strategy
        self.random_strategy = OptimizedRandomStrategy()
        
        # Performance tracking
        self.analysis_count = 0
        self.start_time = None
        self.is_running = False
        
        # Real-time optimization
        self.last_analysis_time = 0
        self.analysis_cache = {}  # Cache recent analysis results
        self.cache_ttl = 5  # Cache time-to-live in seconds
        
        # Operation timing
        self._operation_times = {}

    def _time_operation(self, operation_name: str):
        """Context manager for timing operations"""
        class OperationTimer:
            def __init__(self, manager, name):
                self.manager = manager
                self.name = name
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                execution_time = time.time() - self.start_time
                self.manager._operation_times[self.name] = execution_time
                return execution_time
        
        return OperationTimer(self, operation_name)

    def start(self) -> bool:
        """Start optimized strategy manager"""
        with self._time_operation("manager_start") as timer:
            try:
                self.start_time = datetime.now(timezone.utc)
                self.random_strategy.start_time = self.start_time
                self.is_running = True
                
                self.logger.log(
                    "info", "System", "Strategy Manager started successfully",
                    {"start_time": self.start_time.isoformat()},
                    timer.__exit__(None, None, None)
                )
                return True
                
            except Exception as e:
                self.logger.log(
                    "error", "System", "Failed to start Strategy Manager",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return False

    def stop(self) -> None:
        """Stop strategy manager"""
        with self._time_operation("manager_stop") as timer:
            try:
                self.is_running = False
                self.logger.log(
                    "info", "System", "Strategy Manager stopped successfully",
                    {"uptime": (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0},
                    timer.__exit__(None, None, None)
                )
                
            except Exception as e:
                self.logger.log(
                    "error", "System", "Failed to stop Strategy Manager",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )

    def analyze_and_generate_signals(self, current_prices: Dict[str, Dict]) -> Dict[str, Any]:
        """Real-time analysis and signal generation"""
        with self._time_operation("signal_analysis") as timer:
            try:
                if not self.is_running:
                    self.logger.log(
                        "warning", "Analysis", "Strategy Manager is not running",
                        None,
                        timer.__exit__(None, None, None)
                    )
                    return {}
                
                signals = {}
                for symbol, price_data in current_prices.items():
                    signal = self.random_strategy.generate_signal(symbol, price_data["price"])
                    signals[symbol] = signal
                
                self.analysis_count += 1
                
                # Log analysis summary
                actionable_count = sum(1 for s in signals.values() if s["signal"] in ["BUY", "SELL"])
                self.logger.log(
                    "info", "Analysis", f"Analysis #{self.analysis_count} completed",
                    {
                        "total_signals": len(signals),
                        "actionable_signals": actionable_count,
                        "symbols_analyzed": list(signals.keys())
                    },
                    timer.__exit__(None, None, None)
                )
                
                return signals
                
            except Exception as e:
                self.logger.log(
                    "error", "Analysis", "Signal analysis failed",
                    {"error": str(e)},
                    timer.__exit__(None, None, None)
                )
                return {}

    def get_strategy_status(self) -> Dict[str, Any]:
        """Get comprehensive strategy manager status"""
        try:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
            
            # Get strategy performance
            strategy_perf = self.random_strategy.get_strategy_performance()
            
            # Calculate analysis performance
            analysis_per_second = self.analysis_count / uptime if uptime > 0 else 0
            
            return {
                "manager_status": {
                    "is_running": self.is_running,
                    "uptime_seconds": round(uptime, 2),
                    "analysis_count": self.analysis_count,
                    "analysis_per_second": round(analysis_per_second, 3),
                    "cache_size": len(self.analysis_cache),
                    "last_analysis": round(time.time() - self.last_analysis_time, 2) if self.last_analysis_time > 0 else None
                },
                "strategy_performance": strategy_perf,
                "system_info": {
                    "strategy_type": "Optimized Random Strategy",
                    "real_time_enabled": True,
                    "cache_ttl": self.cache_ttl,
                    "signal_cooldown": self.random_strategy.signal_cooldown
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting strategy status: {e}")
            return {"error": str(e)}

    def get_recent_analysis(self, count: int = 5) -> List[Dict[str, Any]]:
        """Get recent analysis results"""
        try:
            recent_keys = sorted(self.analysis_cache.keys())[-count:]
            return [self.analysis_cache[key] for key in recent_keys]
            
        except Exception as e:
            self.logger.error(f"❌ Error getting recent analysis: {e}")
            return []

    def clear_cache(self) -> None:
        """Clear analysis cache"""
        self.analysis_cache.clear()
        self.logger.info("🧹 Strategy analysis cache cleared")

    def update_probabilities(self, buy_prob: float, sell_prob: float) -> bool:
        """Update strategy probabilities in real-time"""
        try:
            if buy_prob + sell_prob > 1.0:
                self.logger.error("❌ Invalid probabilities: sum exceeds 1.0")
                return False
            
            self.random_strategy.buy_probability = buy_prob
            self.random_strategy.sell_probability = sell_prob
            self.random_strategy.wait_probability = 1.0 - (buy_prob + sell_prob)
            
            self.logger.info(f"✅ Updated probabilities: BUY={buy_prob}, SELL={sell_prob}, WAIT={self.random_strategy.wait_probability}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error updating probabilities: {e}")
            return False


# Alias for backward compatibility
StrategyManager = OptimizedStrategyManager 