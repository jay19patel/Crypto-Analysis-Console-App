"""
Optimized Strategies package for real-time trading signal generation
"""

from .simple_random_strategy import OptimizedRandomStrategy, OptimizedStrategyManager, StrategyManager

__all__ = [
    'OptimizedRandomStrategy',
    'OptimizedStrategyManager', 
    'StrategyManager'  # Alias for backward compatibility
] 