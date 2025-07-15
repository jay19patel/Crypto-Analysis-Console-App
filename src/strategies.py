import random

class RandomStrategy:
    def __init__(self, symbol):
        self.symbol = symbol
        self.signals = ["BUY", "SELL", "WAIT"]

    def generate_signal(self):
        return random.choice(self.signals) 