#!/usr/bin/env python3
"""
Optimized Real-time Random Strategy
Generates trading signals every 1 second with configurable probabilities
"""

import logging
import random
import time
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from src.config import get_settings

class OptimizedRandomStrategy:
    """High-performance random strategy for real-time signal generation"""
    
    def __init__(self):
        """Initialize optimized random strategy"""
        self.logger = logging.getLogger("strategy.random")
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

    def generate_signal(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """
        Generate optimized random trading signal
        
        Args:
            symbol: Trading symbol
            current_price: Current price of the symbol
            
        Returns:
            Dict containing signal information
        """
        try:
            # Check cooldown period
            current_time = time.time()
            last_signal = self.last_signal_time.get(symbol, 0)
            
            if current_time - last_signal < self.signal_cooldown:
                # Return WAIT signal during cooldown
                return self._create_wait_signal(symbol, current_price, "Cooldown period active")
            
            # Generate random number for signal determination
            rand_value = random.random()
            
            if rand_value < self.buy_probability:
                signal = "BUY"
                confidence = random.randint(65, 95)  # Higher confidence for actionable signals
                self.last_signal_time[symbol] = current_time
            elif rand_value < (self.buy_probability + self.sell_probability):
                signal = "SELL"
                confidence = random.randint(65, 95)  # Higher confidence for actionable signals
                self.last_signal_time[symbol] = current_time
            else:
                signal = "WAIT"
                confidence = random.randint(30, 60)  # Lower confidence for WAIT
            
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
                    "reason": f"Random signal: {signal} with {confidence}% confidence",
                    "market_condition": "Normal",
                    "risk_level": "Medium" if signal in ["BUY", "SELL"] else "Low"
                }
            }
            
            # Log only actionable signals to reduce noise
            if signal in ["BUY", "SELL"]:
                self.logger.info(f"🎯 Generated {signal} signal for {symbol} at ${current_price:.2f} (confidence: {confidence}%)")
            
            return signal_data
            
        except Exception as e:
            self.logger.error(f"❌ Error generating signal for {symbol}: {e}")
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
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds() if self.start_time else 0
        
        # Calculate signal distribution
        total_actionable = self.signals_by_type["BUY"] + self.signals_by_type["SELL"]
        
        return {
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


class OptimizedStrategyManager:
    """High-performance strategy manager for real-time operations"""
    
    def __init__(self):
        """Initialize optimized strategy manager"""
        self.logger = logging.getLogger("strategy.manager")
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

    def start(self) -> bool:
        """Start optimized strategy manager"""
        try:
            self.start_time = datetime.now(timezone.utc)
            self.random_strategy.start_time = self.start_time
            self.is_running = True
            
            self.logger.info("🎯 Optimized Strategy Manager started for real-time operations")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error starting strategy manager: {e}")
            return False

    def stop(self) -> None:
        """Stop strategy manager"""
        try:
            self.is_running = False
            self.logger.info("🛑 Optimized Strategy Manager stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping strategy manager: {e}")

    def analyze_and_generate_signals(self, current_prices: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Real-time analysis and signal generation
        
        Args:
            current_prices: Dict of current prices by symbol
            
        Returns:
            Analysis results with actionable signals
        """
        start_time = time.time()
        
        try:
            if not current_prices:
                return {
                    "status": "failed",
                    "reason": "No price data available",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            self.analysis_count += 1
            actionable_signals = {}
            total_signals = 0
            actionable_count = 0
            
            # Generate signals for each symbol
            for symbol, price_data in current_prices.items():
                current_price = price_data.get("price", 0)
                
                if current_price > 0:
                    signal_data = self.random_strategy.generate_signal(symbol, current_price)
                    total_signals += 1
                    
                    # Only include BUY/SELL signals as actionable
                    if signal_data["signal"] in ["BUY", "SELL"]:
                        actionable_signals[symbol] = signal_data
                        actionable_count += 1
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000  # in milliseconds
            
            # Log analysis summary (only for actionable signals to reduce noise)
            if actionable_count > 0:
                self.logger.info(f"🎯 [Strategy] Analysis #{self.analysis_count}: "
                               f"{actionable_count} actionable signals from {total_signals} symbols "
                               f"(executed in {execution_time:.2f}ms)")
            
            results = {
                "status": "completed",
                "analysis_id": f"optimized_analysis_{self.analysis_count}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "execution_time_ms": round(execution_time, 2),
                "performance": {
                    "total_symbols_analyzed": len(current_prices),
                    "signals_generated": total_signals,
                    "actionable_signals_count": actionable_count,
                    "actionable_percentage": round((actionable_count / total_signals) * 100, 2) if total_signals > 0 else 0
                },
                "actionable_signals": actionable_signals,
                "strategy_performance": self.random_strategy.get_strategy_performance()
            }
            
            # Cache recent results for optimization
            self.analysis_cache[self.analysis_count] = results
            self.last_analysis_time = time.time()
            
            # Clean old cache entries (keep last 10)
            if len(self.analysis_cache) > 10:
                oldest_key = min(self.analysis_cache.keys())
                del self.analysis_cache[oldest_key]
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error in signal analysis: {e}")
            
            return {
                "status": "error",
                "reason": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis_id": f"error_analysis_{self.analysis_count}",
                "actionable_signals": {}
            }

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