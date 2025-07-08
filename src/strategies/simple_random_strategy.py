#!/usr/bin/env python3
"""
Simple Random Trading Strategy
Generates trading signals with fixed probabilities: 10% BUY, 10% SELL, 80% WAIT
"""

import random
from datetime import datetime, timezone
from typing import Dict, Any

class SimpleRandomStrategy:
    """Simple random strategy that generates trading signals"""
    
    def __init__(self):
        """Initialize strategy with fixed probabilities"""
        self.buy_probability = 0.10  # 10% chance for BUY
        self.sell_probability = 0.10  # 10% chance for SELL
        # 80% chance for WAIT (remaining probability)

    def generate_signal(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Generate random trading signal based on fixed probabilities"""
        # Generate random number between 0 and 1
        rand_value = random.random()
        
        # Determine signal based on probabilities
        if rand_value < self.buy_probability:
            signal = "BUY"
        elif rand_value < (self.buy_probability + self.sell_probability):
            signal = "SELL"
        else:
            signal = "WAIT"
        
        # Create and return signal data
        return {
            "symbol": symbol,
            "signal": signal,
            "current_price": current_price,
            "timestamp": datetime.now(timezone.utc).isoformat()
        } 