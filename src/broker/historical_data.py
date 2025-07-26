import threading
import time
import pandas as pd
import os
from typing import Dict, Tuple, Optional
import httpx
import pandas as pd
from datetime import datetime, timedelta, timezone
from src.config import get_settings

class HistoricalDataProvider:
    def __init__(self, refresh_buffer_seconds: int = 5, cache_dir: str = "./cache"):
        self.cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        self.cache_expiry: Dict[Tuple[str, str], float] = {}
        self.lock = threading.Lock()
        self.settings = get_settings()
        self.refresh_buffer_seconds = refresh_buffer_seconds
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.refresh_threads: Dict[Tuple[str, str], threading.Thread] = {}

    def get_historical_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        key = (symbol, timeframe)
        now = time.time()
        with self.lock:
            expiry = self.cache_expiry.get(key, 0)
            if key in self.cache and now < expiry:
                return self.cache[key]
            # If not in cache or expired, fetch and start refresh thread
            df = self._fetch_and_cache(symbol, timeframe)
            if key not in self.refresh_threads or not self.refresh_threads[key].is_alive():
                t = threading.Thread(target=self._auto_refresh, args=(symbol, timeframe), daemon=True)
                t.start()
                self.refresh_threads[key] = t
            return df

    def _fetch_and_cache(self, symbol: str, timeframe: str) -> pd.DataFrame:
        key = (symbol, timeframe)
        df = self.fetch_historical_data_from_api(symbol, timeframe)
        self.cache[key] = df
        next_expiry = self._get_next_candle_expiry(df, timeframe)
        self.cache_expiry[key] = next_expiry
        # Optionally persist to disk
        self._save_to_disk(symbol, timeframe, df)
        return df

    def _auto_refresh(self, symbol: str, timeframe: str):
        key = (symbol, timeframe)
        while True:
            now = time.time()
            with self.lock:
                expiry = self.cache_expiry.get(key, 0)
            sleep_time = max(0, expiry - now + self.refresh_buffer_seconds)
            time.sleep(sleep_time)
            with self.lock:
                self._fetch_and_cache(symbol, timeframe)

    def fetch_historical_data_from_api(self, symbol: str, timeframe: str) -> pd.DataFrame:
        url = "https://api.india.delta.exchange/v2/history/candles"
        days = 7  # Default: fetch last 7 days, can be made configurable
        end_time = int(datetime.now(timezone.utc).timestamp())
        start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())

        params = {
            'symbol': symbol,
            'resolution': timeframe,
            'start': start_time,
            'end': end_time
        }

        with httpx.Client() as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            result = response.json()
            candles = result.get('result', [])

        if not candles:
            raise ValueError(f"No data found for {symbol}")

        # Create DataFrame
        df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])

        # Convert to IST timezone
        df['datetime'] = pd.to_datetime(df['time'], unit='s') + timedelta(hours=5, minutes=30)

        # Set proper data types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # Reverse DataFrame so oldest candle is first (index 0)
        df = df.iloc[::-1].reset_index(drop=True)

        # Set datetime as index
        df.set_index('datetime', inplace=True)

        return df

    def _get_next_candle_expiry(self, df: pd.DataFrame, timeframe: str) -> float:
        # Find the last candle's close time and add timeframe + buffer
        if df.empty:
            return time.time() + 60  # fallback: 1 min
        last_time = df.index[-1].to_pydatetime()
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            next_time = last_time + pd.Timedelta(minutes=minutes)
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            next_time = last_time + pd.Timedelta(hours=hours)
        else:
            next_time = last_time + pd.Timedelta(minutes=15)
        return next_time.timestamp() + self.refresh_buffer_seconds

    def _save_to_disk(self, symbol: str, timeframe: str, df: pd.DataFrame):
        filename = os.path.join(self.cache_dir, f"{symbol}_{timeframe}.csv")
        df.to_csv(filename)

    def load_from_disk(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        filename = os.path.join(self.cache_dir, f"{symbol}_{timeframe}.csv")
        if os.path.exists(filename):
            return pd.read_csv(filename, index_col='datetime', parse_dates=True)
        return None 