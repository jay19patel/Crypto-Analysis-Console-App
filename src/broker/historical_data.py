import threading
import time
import pandas as pd
import os
import logging
from typing import Dict, Tuple, Optional
import httpx
import pandas as pd
from datetime import datetime, timedelta, timezone
from src.config import get_settings, get_system_intervals

class HistoricalDataProvider:
    def __init__(self, refresh_buffer_seconds: int = 5, cache_dir: str = "./cache"):
        self.cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        self.cache_expiry: Dict[Tuple[str, str], float] = {}
        self.lock = threading.Lock()
        self.settings = get_settings()
        self.intervals = get_system_intervals()
        self.refresh_buffer_seconds = refresh_buffer_seconds
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.refresh_threads: Dict[Tuple[str, str], threading.Thread] = {}
        self.logger = logging.getLogger("historical_data")
        
        update_interval_minutes = self.intervals['historical_data_update'] // 60
        self.logger.info("📈 Historical Data Provider initialized")
        self.logger.info(f"   📁 Cache directory: {cache_dir}")
        self.logger.info(f"   ⏱️ Refresh buffer: {refresh_buffer_seconds}s")
        self.logger.info(f"   🔄 Auto-update interval: {update_interval_minutes} minutes")

    def get_historical_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Get historical data with comprehensive logging and error handling"""
        key = (symbol, timeframe)
        now = time.time()
        
        try:
            self.logger.debug(f"📊 Requesting historical data for {symbol} ({timeframe})")
            
            with self.lock:
                expiry = self.cache_expiry.get(key, 0)
                if key in self.cache and now < expiry:
                    cache_age = now - (expiry - self._get_cache_duration(timeframe))
                    self.logger.debug(f"✅ Cache hit for {symbol} ({timeframe}) - Age: {cache_age:.1f}s")
                    return self.cache[key]
                
                self.logger.info(f"🔄 Cache miss/expired for {symbol} ({timeframe}) - Fetching fresh data")
                
                # If not in cache or expired, fetch and start refresh thread
                df = self._fetch_and_cache(symbol, timeframe)
                
                if key not in self.refresh_threads or not self.refresh_threads[key].is_alive():
                    self.logger.debug(f"🔄 Starting auto-refresh thread for {symbol} ({timeframe})")
                    t = threading.Thread(target=self._auto_refresh, args=(symbol, timeframe), daemon=True)
                    t.start()
                    self.refresh_threads[key] = t
                
                self.logger.info(f"✅ Historical data loaded for {symbol} ({timeframe}) - {len(df)} candles")
                return df
                
        except Exception as e:
            self.logger.error(f"❌ Failed to get historical data for {symbol} ({timeframe}): {e}")
            # Try to return stale cache if available
            if key in self.cache:
                self.logger.warning(f"⚠️ Returning stale cache for {symbol} ({timeframe})")
                return self.cache[key]
            # Return empty DataFrame as fallback
            self.logger.error(f"❌ No fallback data available for {symbol} ({timeframe})")
            return pd.DataFrame()

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
        """Auto-refresh historical data based on configured interval"""
        key = (symbol, timeframe)
        refresh_interval = self.intervals['historical_data_update']
        
        self.logger.debug(f"🔄 Auto-refresh thread started for {symbol} ({timeframe}) - {refresh_interval}s interval")
        
        while True:
            time.sleep(refresh_interval)
            try:
                self.logger.info(f"🔄 Auto-refreshing historical data for {symbol} ({timeframe})")
                with self.lock:
                    self._fetch_and_cache(symbol, timeframe)
                self.logger.debug(f"✅ Auto-refresh completed for {symbol} ({timeframe})")
            except Exception as e:
                self.logger.error(f"❌ Auto-refresh failed for {symbol} ({timeframe}): {e}")
                # Continue the loop even if refresh fails

    def fetch_historical_data_from_api(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """Fetch historical data from Delta Exchange API with detailed logging"""
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

        try:
            self.logger.info(f"🌐 Fetching historical data from API for {symbol} ({timeframe})")
            self.logger.debug(f"   📅 Date range: {datetime.fromtimestamp(start_time)} to {datetime.fromtimestamp(end_time)}")
            self.logger.debug(f"   🔗 URL: {url}")
            self.logger.debug(f"   📋 Params: {params}")

            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                candles = result.get('result', [])

            if not candles:
                self.logger.error(f"❌ No candle data found for {symbol} ({timeframe})")
                self.logger.debug(f"   📄 API Response: {result}")
                raise ValueError(f"No data found for {symbol}")

            self.logger.info(f"✅ API returned {len(candles)} candles for {symbol} ({timeframe})")

            # Create DataFrame
            df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            self.logger.debug(f"   📊 DataFrame created with {len(df)} rows")

            # Convert to IST timezone
            df['datetime'] = pd.to_datetime(df['time'], unit='s') + timedelta(hours=5, minutes=30)

            # Set proper data types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Check for data quality issues
            null_counts = df.isnull().sum()
            if null_counts.any():
                self.logger.warning(f"⚠️ Data quality issues for {symbol}: {null_counts.to_dict()}")

            # Reverse DataFrame so oldest candle is first (index 0)
            df = df.iloc[::-1].reset_index(drop=True)

            # Set datetime as index
            df.set_index('datetime', inplace=True)

            # Log data summary
            if not df.empty:
                self.logger.info(f"✅ Historical data processed for {symbol} ({timeframe}):")
                self.logger.info(f"   📊 Candles: {len(df)}")
                self.logger.info(f"   📅 Range: {df.index[0]} to {df.index[-1]}")
                self.logger.info(f"   💰 Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
                self.logger.info(f"   📈 Last price: ${df['close'].iloc[-1]:.2f}")

            return df

        except httpx.RequestError as e:
            self.logger.error(f"❌ Network error fetching data for {symbol}: {e}")
            raise
        except httpx.HTTPStatusError as e:
            self.logger.error(f"❌ HTTP error {e.response.status_code} for {symbol}: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"❌ Data processing error for {symbol}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Unexpected error fetching data for {symbol}: {e}")
            raise

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

    def _get_cache_duration(self, timeframe: str) -> float:
        """Get cache duration in seconds based on timeframe"""
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
            return minutes * 60  # minutes to seconds
        elif timeframe.endswith('h'):
            hours = int(timeframe[:-1])
            return hours * 3600  # hours to seconds
        elif timeframe.endswith('d'):
            days = int(timeframe[:-1])
            return days * 86400  # days to seconds
        else:
            # Default to 15 minutes for unknown timeframes
            return 15 * 60

    def load_from_disk(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        filename = os.path.join(self.cache_dir, f"{symbol}_{timeframe}.csv")
        if os.path.exists(filename):
            return pd.read_csv(filename, index_col='datetime', parse_dates=True)
        return None 