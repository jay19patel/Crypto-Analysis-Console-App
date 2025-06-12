import httpx
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import time
import numpy as np
from typing import List, Union, Optional


class HistoricalData:
    """
    Historical Data Technical Analysis Class using pandas-ta
    Focuses on data fetching and indicator calculations only.
    
    Usage:
        # For data and indicators only
        data = HistoricalData("ETHUSD")
        data.EMA([5, 15])  # Adds EMA_5, EMA_15 columns
        data.RSI(window=14)  # Adds RSI_14 column
        data.MACD()  # Adds MACD columns
        
        # For display and analysis management, use AnalysisManager:
        from analysis_manager import AnalysisManager
        manager = AnalysisManager()
        manager.initialize_data("ETHUSD")
        manager.show_analysis(manager.data)
        
        # Or direct access to data
        df = data.get_data()  # Get DataFrame with all indicators
        latest = data.get_latest_data()  # Get latest candle data
        data.refresh()  # Refresh all data and indicators
    """
    
    def __init__(self, symbol: str = 'BTCUSD', resolution: str = '5m', days: int = 10):
        """
        Initialize HistoricalData class
        
        Args:
            symbol (str): Trading pair symbol (default: 'BTCUSD')
            resolution (str): Timeframe - '1m', '5m', '15m', '1h', '1d' (default: '5m')
            days (int): Number of days of historical data (default: 10)
        """
        self.symbol = symbol
        self.resolution = resolution
        self.days = days
        self.df = None
        self.applied_indicators = []  # Track applied indicators for refresh
        
        # Fetch data on initialization
        self._fetch_data()
    
    def _fetch_data(self):
        """Fetches data from Delta Exchange API"""
        try:
            end_time = int(time.time())
            start_time = end_time - (self.days * 86400)
            
            url = 'https://api.india.delta.exchange/v2/history/candles'
            params = {
                'symbol': self.symbol,
                'resolution': self.resolution,
                'start': start_time,
                'end': end_time
            }
            
            with httpx.Client() as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                candles = response.json().get('result', [])
            
            if not candles:
                raise ValueError(f"No data found for {self.symbol}")
            
            # Create DataFrame
            self.df = pd.DataFrame(candles, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert to IST timezone
            self.df['datetime'] = pd.to_datetime(self.df['time'], unit='s') + timedelta(hours=5, minutes=30)
            
            # Set proper data types
            for col in ['open', 'high', 'low', 'close', 'volume']:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
            
            # Reverse DataFrame so oldest candle is first (index 0)
            self.df = self.df.iloc[::-1].reset_index(drop=True)

            # Set datetime as index
            self.df.set_index('datetime', inplace=True)
            
        except Exception as e:
            raise ValueError(f"Data fetch failed: {e}")
    
    def EMA(self, periods: Union[int, List[int]] = [5, 15]):
        """
        Calculate Exponential Moving Average
        
        Args:
            periods: Single number or list of periods [5, 15, 50]
            
        Returns:
            DataFrame: Self.df with EMA columns added (EMA_5, EMA_15, etc.)
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if isinstance(periods, int):
            periods = [periods]
        
        for period in periods:
            if period <= 0:
                raise ValueError(f"Period must be positive, got {period}")
            
            col_name = f'EMA_{period}'
            self.df[col_name] = ta.ema(self.df['close'], length=period)
            
            # Track for refresh functionality
            if ('EMA', periods) not in self.applied_indicators:
                self.applied_indicators.append(('EMA', periods))
    
    def RSI(self, window: int = 14):
        """
        Calculate Relative Strength Index
        
        Args:
            window (int): RSI period (default: 14)
            
        Returns:
            DataFrame: Self.df with RSI column added (RSI_14)
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if window <= 0:
            raise ValueError(f"Window must be positive, got {window}")
        
        col_name = f'RSI_{window}'
        self.df[col_name] = ta.rsi(self.df['close'], length=window)
        
        # Track for refresh functionality
        if ('RSI', window) not in self.applied_indicators:
            self.applied_indicators.append(('RSI', window))
    
    def MACD(self, fast: int = 12, slow: int = 26, signal: int = 9):
        """
        Calculate MACD
        
        Args:
            fast (int): Fast EMA period (default: 12)
            slow (int): Slow EMA period (default: 26)
            signal (int): Signal line EMA period (default: 9)
            
        Returns:
            DataFrame: Self.df with MACD columns added
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if fast >= slow:
            raise ValueError(f"Fast period ({fast}) must be less than slow period ({slow})")
        
        macd_data = ta.macd(self.df['close'], fast=fast, slow=slow, signal=signal)
        
        # Add MACD columns with cleaner names
        self.df[f'MACD_{fast}_{slow}'] = macd_data[f'MACD_{fast}_{slow}_{signal}']
        self.df[f'MACD_Signal_{signal}'] = macd_data[f'MACDs_{fast}_{slow}_{signal}']
        self.df[f'MACD_Histogram'] = macd_data[f'MACDh_{fast}_{slow}_{signal}']
        
        # Track for refresh functionality
        if ('MACD', (fast, slow, signal)) not in self.applied_indicators:
            self.applied_indicators.append(('MACD', (fast, slow, signal)))
    
    def ATR(self, window: int = 14):
        """
        Calculate Average True Range
        
        Args:
            window (int): ATR period (default: 14)
            
        Returns:
            DataFrame: Self.df with ATR column added
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if window <= 0:
            raise ValueError(f"Window must be positive, got {window}")
        
        col_name = f'ATR_{window}'
        self.df[col_name] = ta.atr(high=self.df['high'], low=self.df['low'], 
                                   close=self.df['close'], length=window)
        
        # Track for refresh functionality
        if ('ATR', window) not in self.applied_indicators:
            self.applied_indicators.append(('ATR', window))
    
    def Supertrend(self, period: int = 10, multiplier: float = 3.0):
        """
        Calculate Supertrend indicator
        
        Args:
            period (int): ATR period (default: 10)
            multiplier (float): ATR multiplier (default: 3.0)
            
        Returns:
            DataFrame: Self.df with Supertrend columns added
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if period <= 0 or multiplier <= 0:
            raise ValueError("Period and multiplier must be positive")
        
        st_data = ta.supertrend(high=self.df['high'], low=self.df['low'], 
                               close=self.df['close'], length=period, multiplier=multiplier)
        
        self.df[f'Supertrend_{period}_{multiplier}'] = st_data[f'SUPERT_{period}_{multiplier}']
        self.df[f'Supertrend_Signal'] = st_data[f'SUPERTd_{period}_{multiplier}']
        
        # Track for refresh functionality
        if ('Supertrend', (period, multiplier)) not in self.applied_indicators:
            self.applied_indicators.append(('Supertrend', (period, multiplier)))
    
    def ADX(self, window: int = 14):
        """
        Calculate Average Directional Index
        
        Args:
            window (int): ADX period (default: 14)
            
        Returns:
            DataFrame: Self.df with ADX columns added
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if window <= 0:
            raise ValueError(f"Window must be positive, got {window}")
        
        adx_data = ta.adx(high=self.df['high'], low=self.df['low'], 
                         close=self.df['close'], length=window)
        
        self.df[f'ADX_{window}'] = adx_data[f'ADX_{window}']
        self.df[f'DI_Plus_{window}'] = adx_data[f'DMP_{window}']
        self.df[f'DI_Minus_{window}'] = adx_data[f'DMN_{window}']
        
        # Track for refresh functionality
        if ('ADX', window) not in self.applied_indicators:
            self.applied_indicators.append(('ADX', window))
    
    def VWAP(self):
        """
        Calculate Volume Weighted Average Price
        
        Returns:
            DataFrame: Self.df with VWAP column added
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        self.df['VWAP'] = ta.vwap(high=self.df['high'], low=self.df['low'], 
                                 close=self.df['close'], volume=self.df['volume'])
        
        # Track for refresh functionality
        if ('VWAP', None) not in self.applied_indicators:
            self.applied_indicators.append(('VWAP', None))
    
    def ZSCORE(self, window: int = 20):
        """
        Calculate Z-Score for price normalization
        
        Args:
            window (int): Rolling window for mean/std calculation (default: 20)
            
        Returns:
            DataFrame: Self.df with Z-Score column added
        """
        if self.df is None:
            raise ValueError("Data not loaded.")
        
        if window <= 0:
            raise ValueError(f"Window must be positive, got {window}")
        
        col_name = f'ZSCORE_{window}'
        
        # Z-Score calculation
        rolling_mean = self.df['close'].rolling(window=window).mean()
        rolling_std = self.df['close'].rolling(window=window).std()
        
        self.df[col_name] = (self.df['close'] - rolling_mean) / rolling_std
        
        # Track for refresh functionality
        if ('ZSCORE', window) not in self.applied_indicators:
            self.applied_indicators.append(('ZSCORE', window))
    
    def refresh(self):
        """
        Refresh data and recalculate all previously applied indicators
        """
        # Store applied indicators
        indicators_backup = self.applied_indicators.copy()
        
        # Fetch fresh data
        self._fetch_data()
        
        # Clear and reapply all indicators
        self.applied_indicators = []
        
        for indicator, params in indicators_backup:
            try:
                if indicator == 'EMA':
                    self.EMA(params)
                elif indicator == 'RSI':
                    self.RSI(params)
                elif indicator == 'MACD':
                    self.MACD(params[0], params[1], params[2])
                elif indicator == 'ATR':
                    self.ATR(params)
                elif indicator == 'Supertrend':
                    self.Supertrend(params[0], params[1])
                elif indicator == 'ADX':
                    self.ADX(params)
                elif indicator == 'VWAP':
                    self.VWAP()
                elif indicator == 'ZSCORE':
                    self.ZSCORE(params)
            except Exception as e:
                self.console.print(f"[red]❌ Failed to recalculate {indicator}: {e}[/red]")
    
    def get_data(self):
        """
        Return complete DataFrame with all indicators
        
        Returns:
            DataFrame: Complete dataframe with all calculated indicators
        """
        return self.df
    
    def get_indicators_list(self):
        """
        Return list of all applied indicators
        
        Returns:
            list: List of applied indicators
        """
        return self.applied_indicators
