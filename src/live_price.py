import random

class LivePriceFetcher:
    def __init__(self):
        self.base_prices = {
            "BTC-USD": 50000.0,
            "ETH-USD": 3000.0,
            "AAPL": 150.0,
            "GOOGL": 2800.0,
            "TSLA": 800.0
        }
        self.volatility = {
            "BTC-USD": 0.03,
            "ETH-USD": 0.04,
            "AAPL": 0.02,
            "GOOGL": 0.025,
            "TSLA": 0.05
        }
        self.current_prices = self.base_prices.copy()

    def get_price(self, symbol):
        if symbol not in self.current_prices:
            self.current_prices[symbol] = 100.0
            self.volatility[symbol] = 0.02
        change_percent = random.normalvariate(0, self.volatility[symbol])
        new_price = self.current_prices[symbol] * (1 + change_percent)
        self.current_prices[symbol] = new_price
        return new_price 