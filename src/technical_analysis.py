import httpx
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import time
import numpy as np
from typing import List, Union, Optional
import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich import box


class HistoricalData:
    """
    Historical Data Technical Analysis Class using pandas-ta
    
    Usage:
        data = HistoricalData("ETHUSD")
        data.EMA([5, 15])  # Adds EMA_5, EMA_15 columns
        data.RSI(window=14)  # Adds RSI_14 column
        data.MACD()  # Adds MACD columns
        
        # Get current market status
        data.get_current_analysis()
        
        # Refresh all data and indicators
        data.refresh()
    """
    
    def __init__(self, symbol: str = 'BTCUSD', resolution: str = '5m', days: int = 10):
        """
        Initialize HistoricalData class
        
        Args:
            symbol (str): Trading pair symbol (default: 'BTCUSD')
            resolution (str): Timeframe - '1m', '5m', '15m', '1h', '1d' (default: '5m')
            days (int): Number of days of historical data (default: 30)
        """
        self.symbol = symbol
        self.resolution = resolution
        self.days = days
        self.df = None
        self.applied_indicators = []  # Track applied indicators for refresh
        self.console = Console()
        
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
    
    def get_current_analysis(self):
        """
        Display current market analysis with attractive console-based tables
        """
        if self.df is None:
            self.console.print("[red]❌ No data available.[/red]")
            return
        
        latest = self.df.iloc[-1]
        current_price = latest['close']
        
        # Create main layout
        layout = Layout()
        
        # Header Panel
        header_text = Text(f"📊 TECHNICAL ANALYSIS DASHBOARD", style="bold white")
        header_panel = Panel(
            header_text,
            title=f"🚀 {self.symbol}",
            title_align="left",
            border_style="blue",
            box=box.DOUBLE_EDGE
        )
        
        # Price Info Table
        price_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        price_table.add_column("📈 Market Data", style="cyan", width=20)
        price_table.add_column("💰 Value", style="yellow", width=25)
        price_table.add_column("📊 Status", style="green", width=20)
        
        # Calculate 24h change if possible
        if len(self.df) > 1:
            prev_price = self.df.iloc[-2]['close']
            change = current_price - prev_price
            change_pct = (change / prev_price) * 100
            change_color = "green" if change >= 0 else "red"
            change_symbol = "📈" if change >= 0 else "📉"
            change_text = f"[{change_color}]{change_symbol} {change:+.4f} ({change_pct:+.2f}%)[/{change_color}]"
        else:
            change_text = "[white]N/A[/white]"
        
        price_table.add_row("💵 Current Price", f"{current_price:.4f}", change_text)
        price_table.add_row("📅 Last Update", f"{self.df.index[-1].strftime('%Y-%m-%d %I:%M:%S %p')}", "🔄 Live")
        price_table.add_row("📊 Volume", f"{latest['volume']:,.0f}", "📦 Active")
        price_table.add_row("🎯 High", f"{latest['high']:.4f}", "⬆️")
        price_table.add_row("🎯 Low", f"{latest['low']:.4f}", "⬇️")
        
        # Technical Indicators Table
        indicators_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        indicators_table.add_column("🔍 Indicator", style="white", width=18)
        indicators_table.add_column("📊 Value", style="yellow", width=15)
        indicators_table.add_column("🎯 Signal", style="bold", width=25)
        indicators_table.add_column("💡 Interpretation", style="cyan", width=20)
        
        # EMA Analysis
        ema_cols = [col for col in self.df.columns if col.startswith('EMA_')]
        for col in ema_cols:
            if not pd.isna(latest[col]):
                ema_value = latest[col]
                period = col.split('_')[1]
                
                if current_price > ema_value:
                    signal = "[green]📈 Above EMA[/green]"
                    interpretation = "[green]Bullish[/green]"
                else:
                    signal = "[red]📉 Below EMA[/red]"
                    interpretation = "[red]Bearish[/red]"
                
                indicators_table.add_row(f"📊 EMA_{period}", f"{ema_value:.4f}", signal, interpretation)
        
        # RSI Analysis
        rsi_cols = [col for col in self.df.columns if col.startswith('RSI_')]
        for col in rsi_cols:
            if not pd.isna(latest[col]):
                rsi_value = latest[col]
                if rsi_value > 70:
                    signal = "[red]🔴 Overbought[/red]"
                    interpretation = "[red]Sell Signal[/red]"
                elif rsi_value < 30:
                    signal = "[green]🟢 Oversold[/green]"
                    interpretation = "[green]Buy Signal[/green]"
                else:
                    signal = "[yellow]⚪ Normal[/yellow]"
                    interpretation = "[yellow]Neutral[/yellow]"
                indicators_table.add_row(f"📊 {col}", f"{rsi_value:.2f}", signal, interpretation)
        
        # MACD Analysis
        macd_cols = [col for col in self.df.columns if col.startswith('MACD_') and not 'Signal' in col and not 'Histogram' in col]
        for col in macd_cols:
            if not pd.isna(latest[col]):
                signal_col = col.replace('MACD_', 'MACD_Signal_').split('_')
                signal_col = 'MACD_Signal_' + signal_col[-1]
                
                if signal_col in self.df.columns:
                    macd_val = latest[col]
                    signal_val = latest[signal_col]
                    
                    if macd_val > signal_val:
                        signal = "[green]📈 Bullish[/green]"
                        interpretation = "[green]Uptrend[/green]"
                    else:
                        signal = "[red]📉 Bearish[/red]"
                        interpretation = "[red]Downtrend[/red]"
                    indicators_table.add_row("🎯 MACD", f"{macd_val:.4f}", signal, interpretation)
        
        # ATR Analysis
        atr_cols = [col for col in self.df.columns if col.startswith('ATR_')]
        for col in atr_cols:
            if not pd.isna(latest[col]):
                atr_value = latest[col]
                period = col.split('_')[1]
                
                # ATR interpretation based on volatility
                if atr_value > current_price * 0.02:  # More than 2% of price
                    signal = "[red]🔥 High Volatility[/red]"
                    interpretation = "[red]Volatile[/red]"
                elif atr_value > current_price * 0.01:  # More than 1% of price
                    signal = "[yellow]⚡ Medium Volatility[/yellow]"
                    interpretation = "[yellow]Moderate[/yellow]"
                else:
                    signal = "[green]😌 Low Volatility[/green]"
                    interpretation = "[green]Stable[/green]"
                
                indicators_table.add_row(f"📏 ATR_{period}", f"{atr_value:.4f}", signal, interpretation)
        
        # Supertrend Analysis
        st_signal_cols = [col for col in self.df.columns if col == 'Supertrend_Signal']
        for col in st_signal_cols:
            if not pd.isna(latest[col]):
                if latest[col] == 1:
                    signal = "[green]🟢 UPTREND[/green]"
                    interpretation = "[green]Buy Zone[/green]"
                else:
                    signal = "[red]🔴 DOWNTREND[/red]"
                    interpretation = "[red]Sell Zone[/red]"
                indicators_table.add_row("⚡ Supertrend", f"{latest[col]}", signal, interpretation)
        
        # VWAP Analysis
        if 'VWAP' in self.df.columns and not pd.isna(latest['VWAP']):
            vwap_val = latest['VWAP']
            if current_price > vwap_val:
                signal = "[green]📈 Above VWAP[/green]"
                interpretation = "[green]Bullish[/green]"
            else:
                signal = "[red]📉 Below VWAP[/red]"
                interpretation = "[red]Bearish[/red]"
            indicators_table.add_row("💎 VWAP", f"{vwap_val:.4f}", signal, interpretation)
        
        # ADX Analysis
        adx_cols = [col for col in self.df.columns if col.startswith('ADX_')]
        for col in adx_cols:
            if not pd.isna(latest[col]):
                adx_val = latest[col]
                window = col.split('_')[1]
                
                di_plus_col = f'DI_Plus_{window}'
                di_minus_col = f'DI_Minus_{window}'
                
                if di_plus_col in self.df.columns and di_minus_col in self.df.columns:
                    di_plus = latest[di_plus_col]
                    di_minus = latest[di_minus_col]
                    
                    if adx_val > 25:
                        strength = "[green]Strong[/green]"
                    else:
                        strength = "[yellow]Weak[/yellow]"
                    
                    if di_plus > di_minus:
                        direction = "[green]📈 Uptrend[/green]"
                        interpretation = "[green]Bullish[/green]"
                    else:
                        direction = "[red]📉 Downtrend[/red]"
                        interpretation = "[red]Bearish[/red]"
                    
                    indicators_table.add_row("🎪 ADX", f"{adx_val:.2f}", f"{strength} {direction}", interpretation)
        
        # Z-Score Analysis
        zscore_cols = [col for col in self.df.columns if col.startswith('ZSCORE_')]
        for col in zscore_cols:
            if not pd.isna(latest[col]):
                zscore_val = latest[col]
                
                if zscore_val > 2:
                    signal = "[red]🔴 Extremely Overbought[/red]"
                    interpretation = "[red]Strong Sell[/red]"
                elif zscore_val > 1:
                    signal = "[yellow]🟡 Overbought[/yellow]"
                    interpretation = "[yellow]Consider Sell[/yellow]"
                elif zscore_val < -2:
                    signal = "[green]🟢 Extremely Oversold[/green]"
                    interpretation = "[green]Strong Buy[/green]"
                elif zscore_val < -1:
                    signal = "[yellow]🟡 Oversold[/yellow]"
                    interpretation = "[yellow]Consider Buy[/yellow]"
                else:
                    signal = "[white]⚪ Normal Range[/white]"
                    interpretation = "[white]Neutral[/white]"
                
                indicators_table.add_row(f"📐 {col}", f"{zscore_val:.2f}", signal, interpretation)
        
        # Display everything
        self.console.print(header_panel)
        self.console.print("")
        self.console.print(price_table)
        self.console.print("")
        
        if len(indicators_table.rows) > 0:
            indicators_panel = Panel(
                indicators_table,
                title="🔍 Technical Indicators Analysis",
                border_style="green",
                box=box.ROUNDED
            )
            self.console.print(indicators_panel)
        else:
            self.console.print(Panel(
                "[yellow]No technical indicators calculated yet. Use methods like EMA(), RSI(), MACD() to add indicators.[/yellow]",
                title="ℹ️ Information",
                border_style="yellow"
            ))
        
        # Footer with timestamp
        footer_text = f"⏰ Analysis generated at: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} IST"
        footer_panel = Panel(
            footer_text,
            border_style="blue",
            box=box.ASCII
        )
        self.console.print("")
        self.console.print(footer_panel)
    
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
