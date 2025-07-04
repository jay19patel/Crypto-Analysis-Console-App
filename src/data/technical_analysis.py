import httpx
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, timezone
import time
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

from src.config import get_settings
from src.strategies.strategy_manager import StrategyManager
from src.strategies.base_strategy import SignalType, ConfidenceLevel
from src.system.message_formatter import MessageFormatter, MessageType

logger = logging.getLogger(__name__)

@dataclass
class IndicatorResult:
    """Data class for indicator calculation results"""
    name: str
    value: str
    signal: str
    interpretation: str

class TechnicalAnalysis:
    """Technical analysis engine with strategies integration"""
    
    def __init__(self, websocket_server=None, mongodb_client=None):
        """Initialize technical analysis engine
        
        Args:
            websocket_server: WebSocket server instance for sending messages
            mongodb_client: MongoDB client instance for saving results
        """
        self.logger = logging.getLogger(__name__)
        self.websocket_server = websocket_server
        self.mongodb_client = mongodb_client
        self.settings = get_settings()
        self.df = None
        self.indicators = []
        self.strategy_manager = StrategyManager()
        self.strategy_results = []
        self.ai_analysis_result = None
        self.applied_indicators = []  # Track applied indicators for refresh

    def send_message(self, message: Dict):
        """Send message through WebSocket if available"""
        if self.websocket_server:
            self.websocket_server.queue_message(message)

    def log_message(self, message: str, level: str = "info"):
        """Send log message"""
        self.logger.log(getattr(logging, level.upper()), message)
        if self.websocket_server:
            self.send_message(
                MessageFormatter.format_log(message, level, "technical_analysis")
            )

    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate Moving Average Convergence Divergence"""
        exp1 = data.ewm(span=fast, adjust=False).mean()
        exp2 = data.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return {
            'macd': macd,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()

    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator"""
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        k = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d = k.rolling(window=d_period).mean()
        return {
            'k': k,
            'd': d
        }

    def calculate_vwap(self, high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """Calculate Volume Weighted Average Price"""
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    def fetch_historical_data(self, symbol: str = 'BTCUSD', resolution: str = '5m', days: int = 10) -> bool:
        """Fetch historical data from Delta Exchange"""
        try:
            url = self.settings.HISTORICAL_URL
            
            # Calculate time range
            end_time = int(datetime.now(timezone.utc).timestamp())
            start_time = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
            
            params = {
                'symbol': symbol,
                'resolution': resolution,
                'start': start_time,
                'end': end_time
            }
            
            with httpx.Client() as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                candles = result.get('result', [])
            
            if not candles:
                self.log_message(f"No data found for {symbol}", "error")
                return False
            
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
            
            self.log_message(f"Successfully fetched {len(self.df)} candles for {symbol}", "info")
            return True
            
        except httpx.RequestError as e:
            self.log_message(f"Failed to fetch data: {e}", "error")
            return False
        except Exception as e:
            self.log_message(f"Error processing data: {e}", "error")
            return False
    
    def calculate_indicators(self) -> None:
        """Calculate all technical indicators"""
        if self.df is None or self.df.empty:
            self.log_message("No data available for indicator calculation", "error")
            return
        
        try:
            # Clear applied indicators for fresh calculation
            self.applied_indicators = []
            
            # Calculate EMAs
            for period in self.settings.EMA_PERIODS:
                self.df[f'EMA_{period}'] = self.calculate_ema(self.df['close'], period)
                self.applied_indicators.append(('EMA', period))
            
            # Calculate RSI
            rsi_period = self.settings.RSI_PERIOD
            self.df[f'RSI_{rsi_period}'] = self.calculate_rsi(self.df['close'], rsi_period)
            self.applied_indicators.append(('RSI', rsi_period))
            
            # Calculate MACD
            fast = self.settings.MACD_SETTINGS['fast']
            slow = self.settings.MACD_SETTINGS['slow']
            signal = self.settings.MACD_SETTINGS['signal']
            
            macd_data = self.calculate_macd(self.df['close'], fast, slow, signal)
            self.df[f'MACD_{fast}_{slow}_{signal}'] = macd_data['macd']
            self.df[f'MACDs_{fast}_{slow}_{signal}'] = macd_data['signal']
            self.df[f'MACDh_{fast}_{slow}_{signal}'] = macd_data['histogram']
            self.applied_indicators.append(('MACD', (fast, slow, signal)))
            
            # Calculate ATR
            atr_period = self.settings.ATR_PERIOD
            self.df[f'ATR_{atr_period}'] = self.calculate_atr(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                atr_period
            )
            self.applied_indicators.append(('ATR', atr_period))
            
            # Calculate Stochastic
            stoch_period = self.settings.STOCH_PERIOD
            stoch_data = self.calculate_stochastic(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                stoch_period,
                3
            )
            self.df[f'STOCHk_{stoch_period}_3_3'] = stoch_data['k']
            self.df[f'STOCHd_{stoch_period}_3_3'] = stoch_data['d']
            self.applied_indicators.append(('Stochastic', stoch_period))
            
            # Calculate VWAP
            self.df['VWAP'] = self.calculate_vwap(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                self.df['volume']
            )
            self.applied_indicators.append(('VWAP', None))
            
            self.log_message(f"Successfully calculated {len(self.applied_indicators)} indicators", "info")
            
        except Exception as e:
            self.log_message(f"Error calculating indicators: {e}", "error")
            import traceback
            traceback.print_exc()
    
    def analyze_indicators(self) -> None:
        """Analyze indicators and generate signals"""
        if self.df is None or self.df.empty:
            self.log_message("No data available for analysis", "error")
            return
        
        try:
            # Get latest values
            latest = self.df.iloc[-1]
            
            # Store indicator results
            self.indicators = []
            
            # Analyze EMAs
            for period in self.settings.EMA_PERIODS:
                ema_value = latest[f'EMA_{period}']
                close = latest['close']
                
                if close > ema_value:
                    signal = "BULLISH"
                    interpretation = f"Price above EMA {period}"
                else:
                    signal = "BEARISH"
                    interpretation = f"Price below EMA {period}"
                
                self.indicators.append(IndicatorResult(
                    name=f"EMA_{period}",
                    value=f"{ema_value:.2f}",
                    signal=signal,
                    interpretation=interpretation
                ))
            
            # Analyze RSI
            rsi_period = self.settings.RSI_PERIOD
            rsi_value = latest[f'RSI_{rsi_period}']
            
            if rsi_value > 70:
                signal = "BEARISH"
                interpretation = "Overbought"
            elif rsi_value < 30:
                signal = "BULLISH"
                interpretation = "Oversold"
            else:
                signal = "NEUTRAL"
                interpretation = "Normal range"
            
            self.indicators.append(IndicatorResult(
                name=f"RSI_{rsi_period}",
                value=f"{rsi_value:.2f}",
                signal=signal,
                interpretation=interpretation
            ))
            
            # Analyze MACD
            fast = self.settings.MACD_SETTINGS['fast']
            slow = self.settings.MACD_SETTINGS['slow']
            signal = self.settings.MACD_SETTINGS['signal']
            
            macd_value = latest[f'MACD_{fast}_{slow}_{signal}']
            signal_value = latest[f'MACDs_{fast}_{slow}_{signal}']
            histogram = latest[f'MACDh_{fast}_{slow}_{signal}']
            
            if macd_value > signal_value:
                signal = "BULLISH"
                interpretation = "MACD above signal line"
            else:
                signal = "BEARISH"
                interpretation = "MACD below signal line"
            
            self.indicators.append(IndicatorResult(
                name=f"MACD_{fast}_{slow}_{signal}",
                value=f"{macd_value:.2f}",
                signal=signal,
                interpretation=interpretation
            ))
            
            # Analyze ATR
            atr_period = self.settings.ATR_PERIOD
            atr_value = latest[f'ATR_{atr_period}']
            
            self.indicators.append(IndicatorResult(
                name=f"ATR_{atr_period}",
                value=f"{atr_value:.2f}",
                signal="NEUTRAL",
                interpretation=f"Volatility indicator"
            ))
            
            # Analyze Stochastic
            stoch_period = self.settings.STOCH_PERIOD
            k_value = latest[f'STOCHk_{stoch_period}_3_3']
            d_value = latest[f'STOCHd_{stoch_period}_3_3']
            
            if k_value > 80:
                signal = "BEARISH"
                interpretation = "Overbought"
            elif k_value < 20:
                signal = "BULLISH"
                interpretation = "Oversold"
            else:
                signal = "NEUTRAL"
                interpretation = "Normal range"
            
            self.indicators.append(IndicatorResult(
                name=f"STOCH_{stoch_period}",
                value=f"K: {k_value:.2f}, D: {d_value:.2f}",
                signal=signal,
                interpretation=interpretation
            ))
            
            # Analyze VWAP
            vwap = latest['VWAP']
            close = latest['close']
            
            if close > vwap:
                signal = "BULLISH"
                interpretation = "Price above VWAP"
            else:
                signal = "BEARISH"
                interpretation = "Price below VWAP"
            
            self.indicators.append(IndicatorResult(
                name="VWAP",
                value=f"{vwap:.2f}",
                signal=signal,
                interpretation=interpretation
            ))
            
            # Send indicator analysis through WebSocket
            if self.websocket_server:
                self.send_message(
                    MessageFormatter.format_message(
                        MessageType.ANALYSIS,
                        {
                            "indicators": [
                                {
                                    "name": ind.name,
                                    "value": ind.value,
                                    "signal": ind.signal,
                                    "interpretation": ind.interpretation
                                }
                                for ind in self.indicators
                            ]
                        },
                        "technical_analysis"
                    )
                )
            
        except Exception as e:
            self.log_message(f"Error analyzing indicators: {e}", "error")
            import traceback
            traceback.print_exc()
    
    def analyze_strategies(self) -> None:
        """Run strategy analysis"""
        if self.df is None or self.df.empty:
            self.log_message("No data available for strategy analysis", "error")
            return
        
        try:
            # Run strategy analysis
            self.strategy_results = self.strategy_manager.analyze_all(self.df)
            
            # Send strategy analysis through WebSocket
            if self.websocket_server:
                self.send_message(
                    MessageFormatter.format_message(
                        MessageType.ANALYSIS,
                        {
                            "strategies": self.strategy_results
                        },
                        "technical_analysis"
                    )
                )
            
        except Exception as e:
            self.log_message(f"Error analyzing strategies: {e}", "error")
    
    def get_analysis_results(self) -> Dict[str, Any]:
        """Get combined analysis results"""
        try:
            results = {
                "timestamp": datetime.now().isoformat(),
                "indicators": [
                    {
                        "name": ind.name,
                        "value": ind.value,
                        "signal": ind.signal,
                        "interpretation": ind.interpretation
                    }
                    for ind in self.indicators
                ],
                "strategies": self.strategy_results,
                "ai_analysis": self.ai_analysis_result
            }
            
            # Save to MongoDB if available
            if self.mongodb_client:
                try:
                    self.mongodb_client.save_analysis_result(results)
                except Exception as e:
                    self.log_message(f"Error saving to MongoDB: {e}", "error")
            
            return results
            
        except Exception as e:
            self.log_message(f"Error getting analysis results: {e}", "error")
            return {}
    
    def analyze_all(self, prices: Dict[str, float]) -> Dict[str, Any]:
        """Run complete analysis for all symbols"""
        results = {}
        
        for symbol, price in prices.items():
            try:
                if self.fetch_historical_data(symbol):
                    self.calculate_indicators()
                    self.analyze_indicators()
                    self.analyze_strategies()
                    results[symbol] = self.get_analysis_results()
                    
            except Exception as e:
                self.log_message(f"Error analyzing {symbol}: {e}", "error")
        
        return results 