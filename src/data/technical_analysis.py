import logging
import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    print("⚠️ pandas_ta not available, using basic indicators")
    PANDAS_TA_AVAILABLE = False
    ta = None
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import uuid

from src.config import get_settings
from src.system.message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    """Technical analysis engine with strategies integration"""
    
    def __init__(self, websocket_server=None, mongodb_client=None):
        """
        Initialize Technical Analysis
        
        Args:
            websocket_server: WebSocket server for sending messages
            mongodb_client: MongoDB client for data storage
        """
        self.logger = logging.getLogger(__name__)
        self.websocket_server = websocket_server
        self.mongodb_client = mongodb_client
        self.settings = get_settings()
        
        # Data storage
        self.df = None
        self.current_symbol = None
        
        # Analysis parameters
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        self.sma_short = 20
        self.sma_long = 50
        self.ema_short = 12
        self.ema_long = 26
        
        # Symbols to analyze
        self.symbols = self.settings.DEFAULT_SYMBOLS

    def send_message(self, message: Dict):
        """Send message through WebSocket if available"""
        if self.websocket_server and hasattr(self.websocket_server, 'queue_message'):
            self.websocket_server.queue_message(message)

    def log_message(self, message: str, level: str = "info"):
        """Send log message"""
        self.logger.log(getattr(logging, level.upper()), message)
        if self.websocket_server:
            self.send_message(
                MessageFormatter.format_log(message, level, "technical_analysis")
            )


    
    def fetch_historical_data(self, symbol: str, timeframe: str = "5m", limit: int = 2880) -> bool:
        """
        Fetch historical data for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')
            timeframe: Timeframe for candles (default: 5m)
            limit: Number of candles to fetch (default: 2880 for 10 days of 5m candles)
            
        Returns:
            bool: True if data fetched successfully, False otherwise
        """
        try:
            # Calculate time range (10 days back from now)
            end_time = int(datetime.now().timestamp())
            start_time = end_time - (10 * 24 * 60 * 60)  # 10 days back
            
            url = f"{self.settings.DELTA_API_URL}/history/candles"
            params = {
                'symbol': symbol,
                'resolution': timeframe,
                'start': start_time,
                'end': end_time
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'result' in data and data['result']:
                candles = data['result']
                
                # Convert to DataFrame
                df_data = []
                for candle in candles:
                    df_data.append({
                        'timestamp': pd.to_datetime(candle['time'], unit='s'),
                        'open': float(candle['open']),
                        'high': float(candle['high']),
                        'low': float(candle['low']),
                        'close': float(candle['close']),
                        'volume': float(candle['volume']) if 'volume' in candle else 0
                    })
                
                self.df = pd.DataFrame(df_data)
                self.df.set_index('timestamp', inplace=True)
                self.df = self.df.sort_index()
                self.current_symbol = symbol
                
                self.log_message(f"Successfully fetched {len(self.df)} candles for {symbol}", "info")
                return True
            else:
                self.log_message(f"No data received for {symbol}", "warning")
                return False
                
        except Exception as e:
            self.log_message(f"Error fetching data for {symbol}: {e}", "error")
            return False

    def calculate_indicators(self) -> Dict[str, Any]:
        """
        Calculate technical indicators
        
        Returns:
            Dict containing all calculated indicators
        """
        if self.df is None or len(self.df) < 50:
            return {}
        
        try:
            indicators = {}
            
            if PANDAS_TA_AVAILABLE and ta is not None:
                # Use pandas_ta for technical analysis
                # RSI
                rsi = ta.rsi(self.df['close'], length=self.rsi_period)
                indicators['rsi'] = rsi.values if rsi is not None else np.array([])
                
                # MACD
                macd_data = ta.macd(self.df['close'], fast=self.macd_fast, slow=self.macd_slow, signal=self.macd_signal)
                if macd_data is not None:
                    indicators['macd'] = macd_data[f'MACD_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].values
                    indicators['macd_signal'] = macd_data[f'MACDs_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].values
                    indicators['macd_histogram'] = macd_data[f'MACDh_{self.macd_fast}_{self.macd_slow}_{self.macd_signal}'].values
                else:
                    indicators['macd'] = np.array([])
                    indicators['macd_signal'] = np.array([])
                    indicators['macd_histogram'] = np.array([])
                
                # Bollinger Bands
                bb_data = ta.bbands(self.df['close'], length=self.bb_period, std=self.bb_std)
                if bb_data is not None:
                    indicators['bb_upper'] = bb_data[f'BBU_{self.bb_period}_{self.bb_std}'].values
                    indicators['bb_middle'] = bb_data[f'BBM_{self.bb_period}_{self.bb_std}'].values
                    indicators['bb_lower'] = bb_data[f'BBL_{self.bb_period}_{self.bb_std}'].values
                else:
                    indicators['bb_upper'] = np.array([])
                    indicators['bb_middle'] = np.array([])
                    indicators['bb_lower'] = np.array([])
                
                # Moving Averages
                sma_short = ta.sma(self.df['close'], length=self.sma_short)
                sma_long = ta.sma(self.df['close'], length=self.sma_long)
                ema_short = ta.ema(self.df['close'], length=self.ema_short)
                ema_long = ta.ema(self.df['close'], length=self.ema_long)
                
                indicators['sma_short'] = sma_short.values if sma_short is not None else np.array([])
                indicators['sma_long'] = sma_long.values if sma_long is not None else np.array([])
                indicators['ema_short'] = ema_short.values if ema_short is not None else np.array([])
                indicators['ema_long'] = ema_long.values if ema_long is not None else np.array([])
                
                # Stochastic
                stoch_data = ta.stoch(self.df['high'], self.df['low'], self.df['close'])
                if stoch_data is not None:
                    indicators['stoch_k'] = stoch_data['STOCHk_14_3_3'].values
                    indicators['stoch_d'] = stoch_data['STOCHd_14_3_3'].values
                else:
                    indicators['stoch_k'] = np.array([])
                    indicators['stoch_d'] = np.array([])
                
                # Williams %R
                willr = ta.willr(self.df['high'], self.df['low'], self.df['close'])
                indicators['williams_r'] = willr.values if willr is not None else np.array([])
                
                # ATR (Average True Range)
                atr = ta.atr(self.df['high'], self.df['low'], self.df['close'])
                indicators['atr'] = atr.values if atr is not None else np.array([])
                
                # Volume indicators
                obv = ta.obv(self.df['close'], self.df['volume'])
                indicators['obv'] = obv.values if obv is not None else np.array([])
                
                # ADX (Average Directional Index)
                adx = ta.adx(self.df['high'], self.df['low'], self.df['close'])
                if adx is not None:
                    indicators['adx'] = adx['ADX_14'].values
                else:
                    indicators['adx'] = np.array([])
            else:
                # Fallback to basic indicators using pandas
                self.log_message("Using basic indicators (pandas_ta not available)", "warning")
                
                # Simple Moving Averages
                indicators['sma_short'] = self.df['close'].rolling(window=self.sma_short).mean().values
                indicators['sma_long'] = self.df['close'].rolling(window=self.sma_long).mean().values
                
                # Exponential Moving Averages  
                indicators['ema_short'] = self.df['close'].ewm(span=self.ema_short).mean().values
                indicators['ema_long'] = self.df['close'].ewm(span=self.ema_long).mean().values
                
                # Basic RSI calculation
                delta = self.df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
                rs = gain / loss
                indicators['rsi'] = (100 - (100 / (1 + rs))).values
                
                # Basic Bollinger Bands
                bb_middle = self.df['close'].rolling(window=self.bb_period).mean()
                bb_std = self.df['close'].rolling(window=self.bb_period).std()
                indicators['bb_middle'] = bb_middle.values
                indicators['bb_upper'] = (bb_middle + (bb_std * self.bb_std)).values
                indicators['bb_lower'] = (bb_middle - (bb_std * self.bb_std)).values
                
                # Set empty arrays for unavailable indicators
                indicators['macd'] = np.array([])
                indicators['macd_signal'] = np.array([])
                indicators['macd_histogram'] = np.array([])
                indicators['stoch_k'] = np.array([])
                indicators['stoch_d'] = np.array([])
                indicators['williams_r'] = np.array([])
                indicators['atr'] = np.array([])
                indicators['obv'] = np.array([])
                indicators['adx'] = np.array([])
            
            return indicators
            
        except Exception as e:
            self.log_message(f"Error calculating indicators: {e}", "error")
            return {}

    def analyze_trend(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market trend
        
        Args:
            indicators: Dictionary of calculated indicators
            
        Returns:
            Dict containing trend analysis
        """
        if not indicators:
            return {}
        
        try:
            trend_analysis = {
                'direction': 'NEUTRAL',
                'strength': 0,
                'signals': []
            }
            
            # Get latest values (handle NaN values)
            latest_idx = -1
            
            # Moving Average Trend
            sma_short = indicators.get('sma_short', [])
            sma_long = indicators.get('sma_long', [])
            
            if len(sma_short) > 0 and len(sma_long) > 0:
                if not np.isnan(sma_short[latest_idx]) and not np.isnan(sma_long[latest_idx]):
                    if sma_short[latest_idx] > sma_long[latest_idx]:
                        trend_analysis['signals'].append('SMA_BULLISH')
                        trend_analysis['strength'] += 1
                    elif sma_short[latest_idx] < sma_long[latest_idx]:
                        trend_analysis['signals'].append('SMA_BEARISH')
                        trend_analysis['strength'] -= 1
            
            # EMA Trend
            ema_short = indicators.get('ema_short', [])
            ema_long = indicators.get('ema_long', [])
            
            if len(ema_short) > 0 and len(ema_long) > 0:
                if not np.isnan(ema_short[latest_idx]) and not np.isnan(ema_long[latest_idx]):
                    if ema_short[latest_idx] > ema_long[latest_idx]:
                        trend_analysis['signals'].append('EMA_BULLISH')
                        trend_analysis['strength'] += 1
                    elif ema_short[latest_idx] < ema_long[latest_idx]:
                        trend_analysis['signals'].append('EMA_BEARISH')
                        trend_analysis['strength'] -= 1
            
            # MACD Trend
            macd = indicators.get('macd', [])
            macd_signal = indicators.get('macd_signal', [])
            
            if len(macd) > 0 and len(macd_signal) > 0:
                if not np.isnan(macd[latest_idx]) and not np.isnan(macd_signal[latest_idx]):
                    if macd[latest_idx] > macd_signal[latest_idx]:
                        trend_analysis['signals'].append('MACD_BULLISH')
                        trend_analysis['strength'] += 1
                    elif macd[latest_idx] < macd_signal[latest_idx]:
                        trend_analysis['signals'].append('MACD_BEARISH')
                        trend_analysis['strength'] -= 1
            
            # ADX Trend Strength
            adx = indicators.get('adx', [])
            if len(adx) > 0 and not np.isnan(adx[latest_idx]):
                if adx[latest_idx] > 25:
                    trend_analysis['signals'].append('STRONG_TREND')
                elif adx[latest_idx] < 20:
                    trend_analysis['signals'].append('WEAK_TREND')
            
            # Determine overall direction
            if trend_analysis['strength'] > 1:
                trend_analysis['direction'] = 'BULLISH'
            elif trend_analysis['strength'] < -1:
                trend_analysis['direction'] = 'BEARISH'
            else:
                trend_analysis['direction'] = 'NEUTRAL'
            
            return trend_analysis
            
        except Exception as e:
            self.log_message(f"Error analyzing trend: {e}", "error")
            return {}

    def analyze_momentum(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market momentum
        
        Args:
            indicators: Dictionary of calculated indicators
            
        Returns:
            Dict containing momentum analysis
        """
        if not indicators:
            return {}
        
        try:
            momentum_analysis = {
                'condition': 'NEUTRAL',
                'strength': 0,
                'signals': []
            }
            
            latest_idx = -1
            
            # RSI Analysis
            rsi = indicators.get('rsi', [])
            if len(rsi) > 0 and not np.isnan(rsi[latest_idx]):
                rsi_val = rsi[latest_idx]
                if rsi_val > 70:
                    momentum_analysis['signals'].append('RSI_OVERBOUGHT')
                    momentum_analysis['strength'] -= 1
                elif rsi_val < 30:
                    momentum_analysis['signals'].append('RSI_OVERSOLD')
                    momentum_analysis['strength'] += 1
                elif rsi_val > 50:
                    momentum_analysis['signals'].append('RSI_BULLISH')
                    momentum_analysis['strength'] += 0.5
                elif rsi_val < 50:
                    momentum_analysis['signals'].append('RSI_BEARISH')
                    momentum_analysis['strength'] -= 0.5
            
            # Stochastic Analysis
            stoch_k = indicators.get('stoch_k', [])
            stoch_d = indicators.get('stoch_d', [])
            
            if len(stoch_k) > 0 and len(stoch_d) > 0:
                if not np.isnan(stoch_k[latest_idx]) and not np.isnan(stoch_d[latest_idx]):
                    if stoch_k[latest_idx] > 80 and stoch_d[latest_idx] > 80:
                        momentum_analysis['signals'].append('STOCH_OVERBOUGHT')
                        momentum_analysis['strength'] -= 1
                    elif stoch_k[latest_idx] < 20 and stoch_d[latest_idx] < 20:
                        momentum_analysis['signals'].append('STOCH_OVERSOLD')
                        momentum_analysis['strength'] += 1
            
            # Williams %R Analysis
            williams_r = indicators.get('williams_r', [])
            if len(williams_r) > 0 and not np.isnan(williams_r[latest_idx]):
                wr_val = williams_r[latest_idx]
                if wr_val > -20:
                    momentum_analysis['signals'].append('WILLR_OVERBOUGHT')
                    momentum_analysis['strength'] -= 1
                elif wr_val < -80:
                    momentum_analysis['signals'].append('WILLR_OVERSOLD')
                    momentum_analysis['strength'] += 1
            
            # Determine overall momentum condition
            if momentum_analysis['strength'] > 1:
                momentum_analysis['condition'] = 'OVERSOLD'
            elif momentum_analysis['strength'] < -1:
                momentum_analysis['condition'] = 'OVERBOUGHT'
            else:
                momentum_analysis['condition'] = 'NEUTRAL'
            
            return momentum_analysis
            
        except Exception as e:
            self.log_message(f"Error analyzing momentum: {e}", "error")
            return {}

    def generate_trading_signals(self, indicators: Dict[str, Any], trend: Dict[str, Any], momentum: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on analysis
        
        Args:
            indicators: Technical indicators
            trend: Trend analysis
            momentum: Momentum analysis
            
        Returns:
            List of trading signals
        """
        signals = []
        
        try:
            # Strategy 1: Trend Following
            if trend.get('direction') == 'BULLISH' and momentum.get('condition') != 'OVERBOUGHT':
                signals.append({
                    'strategy': 'Trend Following',
                    'signal': 'BUY',
                    'confidence': min(85, 60 + abs(trend.get('strength', 0)) * 5),
                    'reason': f"Bullish trend with {momentum.get('condition', 'neutral')} momentum"
                })
            elif trend.get('direction') == 'BEARISH' and momentum.get('condition') != 'OVERSOLD':
                signals.append({
                    'strategy': 'Trend Following',
                    'signal': 'SELL',
                    'confidence': min(85, 60 + abs(trend.get('strength', 0)) * 5),
                    'reason': f"Bearish trend with {momentum.get('condition', 'neutral')} momentum"
                })
            
            # Strategy 2: Mean Reversion
            if momentum.get('condition') == 'OVERSOLD' and trend.get('direction') != 'BEARISH':
                signals.append({
                    'strategy': 'Mean Reversion',
                    'signal': 'BUY',
                    'confidence': 70,
                    'reason': 'Oversold condition with potential reversal'
                })
            elif momentum.get('condition') == 'OVERBOUGHT' and trend.get('direction') != 'BULLISH':
                signals.append({
                    'strategy': 'Mean Reversion',
                    'signal': 'SELL',
                    'confidence': 70,
                    'reason': 'Overbought condition with potential reversal'
                })
            
            # Strategy 3: Bollinger Band Squeeze
            bb_upper = indicators.get('bb_upper', [])
            bb_lower = indicators.get('bb_lower', [])
            close = self.df['close'].values if self.df is not None else []
            
            if len(bb_upper) > 0 and len(bb_lower) > 0 and len(close) > 0:
                latest_idx = -1
                if not np.isnan(bb_upper[latest_idx]) and not np.isnan(bb_lower[latest_idx]):
                    if close[latest_idx] > bb_upper[latest_idx]:
                        signals.append({
                            'strategy': 'Bollinger Breakout',
                            'signal': 'BUY',
                            'confidence': 75,
                            'reason': 'Price broke above upper Bollinger Band'
                        })
                    elif close[latest_idx] < bb_lower[latest_idx]:
                        signals.append({
                            'strategy': 'Bollinger Reversal',
                            'signal': 'BUY',
                            'confidence': 65,
                            'reason': 'Price touched lower Bollinger Band'
                        })
            
            # If no strong signals, suggest WAIT
            if not signals:
                signals.append({
                    'strategy': 'Conservative',
                    'signal': 'WAIT',
                    'confidence': 50,
                    'reason': 'No clear trading opportunity identified'
                })
            
        except Exception as e:
            self.log_message(f"Error generating signals: {e}", "error")
            signals.append({
                'strategy': 'Error',
                'signal': 'WAIT',
                'confidence': 0,
                'reason': f'Analysis error: {str(e)}'
            })
        
        return signals

    def analyze_symbol(self, symbol: str, current_price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a single symbol
        
        Args:
            symbol: Symbol to analyze
            current_price: Current price if available
            
        Returns:
            Dict containing analysis results or None if failed
        """
        try:
            # Format symbol for API (remove dash)
            symbol_formatted = symbol.replace('-', '')
            
            # Fetch historical data
            if not self.fetch_historical_data(symbol_formatted):
                return None
            
            # Calculate indicators
            indicators = self.calculate_indicators()
            if not indicators:
                self.log_message(f"No indicators calculated for {symbol}", "warning")
                return None
            
            # Analyze trend and momentum
            trend_analysis = self.analyze_trend(indicators)
            momentum_analysis = self.analyze_momentum(indicators)
            
            # Generate trading signals
            strategies = self.generate_trading_signals(indicators, trend_analysis, momentum_analysis)
            
            # Get current price from data if not provided
            if current_price is None and self.df is not None and len(self.df) > 0:
                current_price = float(self.df['close'].iloc[-1])
            
            # Create analysis result
            analysis_result = {
                'symbol': symbol,
                'analysis_id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'trend': trend_analysis,
                'momentum': momentum_analysis,
                'strategies': strategies,
                'indicators': {
                    'rsi': float(indicators['rsi'][-1]) if len(indicators.get('rsi', [])) > 0 and not np.isnan(indicators['rsi'][-1]) else None,
                    'macd': float(indicators['macd'][-1]) if len(indicators.get('macd', [])) > 0 and not np.isnan(indicators['macd'][-1]) else None,
                    'bb_position': 'middle'  # Simplified for now
                }
            }
            
            # Store in MongoDB if available
            if self.mongodb_client:
                try:
                    self.mongodb_client.store_analysis_result(analysis_result)
                except Exception as e:
                    self.log_message(f"Failed to store analysis in MongoDB: {e}", "warning")
            
            self.log_message(f"Analysis completed for {symbol}", "info")
            return analysis_result
            
        except Exception as e:
            self.log_message(f"Error analyzing {symbol}: {e}", "error")
            return None

    def analyze_all_symbols(self) -> Dict[str, Any]:
        """
        Analyze all configured symbols
        
        Returns:
            Dict containing analysis results for all symbols
        """
        results = {}
        
        for symbol in self.symbols:
            try:
                self.log_message(f"Analyzing {symbol}...", "info")
                result = self.analyze_symbol(symbol)
                if result:
                    results[symbol] = result
                else:
                    self.log_message(f"Failed to analyze {symbol}", "warning")
                    
            except Exception as e:
                self.log_message(f"Error analyzing {symbol}: {e}", "error")
        
        return results

    def analyze_all(self, current_prices: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Analyze all symbols with optional current prices
        
        Args:
            current_prices: Optional dict of current prices by symbol
            
        Returns:
            Dict containing analysis results for all symbols
        """
        return self.analyze_all_symbols() 