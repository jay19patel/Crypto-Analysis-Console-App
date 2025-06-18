import httpx
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

from ..config import get_settings
from ..ui.console import ConsoleUI

@dataclass
class IndicatorResult:
    """Data class for indicator calculation results"""
    name: str
    value: str
    signal: str
    interpretation: str

@dataclass
class StrategyResult:
    """Data class for trading strategy results"""
    name: str
    signal: str
    strength: float
    interpretation: str
    conditions_met: List[str]
    conditions_failed: List[str]

class TechnicalAnalysis:
    """Technical analysis engine with improved error handling and type safety"""
    
    def __init__(self, ui: ConsoleUI, symbol: str = 'BTCUSD', resolution: str = '5m', days: int = 10):
        """
        Initialize technical analysis engine
        
        Args:
            ui (ConsoleUI): Console UI instance
            symbol (str): Trading pair symbol
            resolution (str): Timeframe resolution
            days (int): Number of days of historical data
        """
        self.settings = get_settings()
        self.ui = ui
        self.symbol = symbol
        self.resolution = resolution
        self.days = days
        self.df: Optional[pd.DataFrame] = None
        self.indicators: List[IndicatorResult] = []
        self.strategies: List[StrategyResult] = []
        
        # Initialize HTTP client with timeout
        self.client = httpx.Client(timeout=self.settings.WEBSOCKET_TIMEOUT)
    
    def fetch_historical_data(self) -> bool:
        """
        Fetch historical price data
        
        Returns:
            bool: True if data was fetched successfully
        """
        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(days=self.days)
            
            # Fetch data from API
            response = self.client.get(
                f"{self.settings.HISTORICAL_URL}",
                params={
                    "symbol": self.symbol,
                    "resolution": self.resolution,
                    "from": int(start_time.timestamp()),
                    "to": int(end_time.timestamp())
                }
            )
            response.raise_for_status()
            
            # Process data
            data = response.json()
            self.df = pd.DataFrame({
                'timestamp': pd.to_datetime(data['t'], unit='s'),
                'open': data['o'],
                'high': data['h'],
                'low': data['l'],
                'close': data['c'],
                'volume': data['v']
            }).set_index('timestamp')
            
            return True
            
        except httpx.RequestError as e:
            self.ui.print_error(f"Failed to fetch data: {e}")
            return False
        except Exception as e:
            self.ui.print_error(f"Error processing data: {e}")
            return False
    
    def calculate_indicators(self) -> None:
        """Calculate all technical indicators"""
        if self.df is None or self.df.empty:
            self.ui.print_error("No data available for indicator calculation")
            return
        
        try:
            # Calculate EMAs
            for period in self.settings.EMA_PERIODS:
                self.df[f'EMA_{period}'] = ta.ema(self.df['close'], length=period)
            
            # Calculate RSI
            self.df[f'RSI_{self.settings.RSI_PERIOD}'] = ta.rsi(
                self.df['close'],
                length=self.settings.RSI_PERIOD
            )
            
            # Calculate MACD
            macd = ta.macd(
                self.df['close'],
                fast=self.settings.MACD_SETTINGS['fast'],
                slow=self.settings.MACD_SETTINGS['slow'],
                signal=self.settings.MACD_SETTINGS['signal']
            )
            self.df = pd.concat([self.df, macd], axis=1)
            
            # Calculate ATR
            self.df[f'ATR_{self.settings.ATR_PERIOD}'] = ta.atr(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                length=self.settings.ATR_PERIOD
            )
            
            # Calculate Stochastic
            stoch = ta.stoch(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                length=self.settings.STOCH_PERIOD
            )
            self.df = pd.concat([self.df, stoch], axis=1)
            
            # Calculate VWAP
            self.df['VWAP'] = ta.vwap(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                self.df['volume']
            )
            
        except Exception as e:
            self.ui.print_error(f"Error calculating indicators: {e}")
    
    def analyze_indicators(self) -> None:
        """Analyze indicators and generate signals"""
        if self.df is None or self.df.empty:
            return
        
        try:
            latest = self.df.iloc[-1]
            current_price = latest['close']
            
            # Clear previous results
            self.indicators = []
            
            # Analyze EMAs
            for period in self.settings.EMA_PERIODS:
                ema_value = latest[f'EMA_{period}']
                if current_price > ema_value:
                    signal = "📈 Above EMA"
                    interpretation = "Bullish"
                else:
                    signal = "📉 Below EMA"
                    interpretation = "Bearish"
                
                self.indicators.append(IndicatorResult(
                    name=f"EMA_{period}",
                    value=f"{ema_value:.2f}",
                    signal=signal,
                    interpretation=interpretation
                ))
            
            # Analyze RSI
            rsi_value = latest[f'RSI_{self.settings.RSI_PERIOD}']
            if rsi_value > 70:
                signal = "🔴 Overbought"
                interpretation = "Sell Signal"
            elif rsi_value < 30:
                signal = "🟢 Oversold"
                interpretation = "Buy Signal"
            else:
                signal = "⚪ Normal"
                interpretation = "Neutral"
            
            self.indicators.append(IndicatorResult(
                name=f"RSI_{self.settings.RSI_PERIOD}",
                value=f"{rsi_value:.2f}",
                signal=signal,
                interpretation=interpretation
            ))
            
            # Add more indicator analysis here...
            
        except Exception as e:
            self.ui.print_error(f"Error analyzing indicators: {e}")
    
    def analyze_strategies(self) -> None:
        """Analyze trading strategies"""
        if self.df is None or self.df.empty:
            return
        
        try:
            # Clear previous results
            self.strategies = []
            
            # Trend Following Strategy
            trend_conditions_met = []
            trend_conditions_failed = []
            
            # Check EMAs
            latest = self.df.iloc[-1]
            current_price = latest['close']
            
            for period in self.settings.EMA_PERIODS:
                ema_value = latest[f'EMA_{period}']
                if current_price > ema_value:
                    trend_conditions_met.append(f"Price above EMA_{period}")
                else:
                    trend_conditions_failed.append(f"Price below EMA_{period}")
            
            trend_strength = (len(trend_conditions_met) / len(self.settings.EMA_PERIODS)) * 100
            
            if trend_strength > 70:
                trend_signal = "BUY"
                trend_interpretation = "Strong uptrend"
            elif trend_strength < 30:
                trend_signal = "SELL"
                trend_interpretation = "Strong downtrend"
            else:
                trend_signal = "NEUTRAL"
                trend_interpretation = "Mixed trend signals"
            
            self.strategies.append(StrategyResult(
                name="Trend Following",
                signal=trend_signal,
                strength=trend_strength,
                interpretation=trend_interpretation,
                conditions_met=trend_conditions_met,
                conditions_failed=trend_conditions_failed
            ))
            
            # Add more strategy analysis here...
            
        except Exception as e:
            self.ui.print_error(f"Error analyzing strategies: {e}")
    
    def get_analysis_results(self) -> Dict[str, Any]:
        """
        Get complete analysis results
        
        Returns:
            Dict[str, Any]: Analysis results including indicators and strategies
        """
        return {
            'symbol': self.symbol,
            'resolution': self.resolution,
            'days': self.days,
            'indicators': [vars(i) for i in self.indicators],
            'strategies': [vars(s) for s in self.strategies]
        }
    
    def refresh(self) -> bool:
        """
        Refresh analysis with new data
        
        Returns:
            bool: True if refresh was successful
        """
        try:
            if self.fetch_historical_data():
                self.calculate_indicators()
                self.analyze_indicators()
                self.analyze_strategies()
                return True
            return False
        except Exception as e:
            self.ui.print_error(f"Error refreshing analysis: {e}")
            return False 