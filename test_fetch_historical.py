import time
from datetime import datetime
from src.broker.historical_data import HistoricalDataProvider

SYMBOL = "BTCUSD"  # Change as needed
timeframe = "15m"

provider = HistoricalDataProvider()

print(f"Starting historical data fetch test for {SYMBOL} ({timeframe})...")

# For demonstration, we'll print the DataFrame every 30 seconds.
# In production, the provider auto-refreshes every 10 minutes + buffer.
while True:
    try:
        df = provider.get_historical_data(SYMBOL, timeframe)
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DataFrame head:")
        print(df.head())
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] DataFrame tail:")
        print(df.tail())
    except Exception as e:
        print(f"Error fetching data: {e}")
    time.sleep(30)  # Sleep 30s for demo; in real use, refresh is every 10m+buffer 