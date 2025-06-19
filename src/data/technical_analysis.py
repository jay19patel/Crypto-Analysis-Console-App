import httpx
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta, timezone
import time
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

from ..config import get_settings
from ..ui.console import ConsoleUI
from ..strategies import StrategyManager

@dataclass
class IndicatorResult:
    """Data class for indicator calculation results"""
    name: str
    value: str
    signal: str
    interpretation: str

class TechnicalAnalysis:
    """Technical analysis engine with strategies integration"""
    
    def __init__(self, ui: ConsoleUI, symbol: str = 'BTCUSD', resolution: str = '5m', days: int = 10):
        self.ui = ui
        self.symbol = symbol
        self.resolution = resolution
        self.days = days
        self.settings = get_settings()
        self.df = None
        self.indicators = []
        self.strategy_manager = StrategyManager()
        self.strategy_results = []
        self.ai_analysis_result = None
        self.applied_indicators = []  # Track applied indicators for refresh
    
    def fetch_historical_data(self) -> bool:
        """Fetch historical data from Delta Exchange"""
        try:
            url = self.settings.HISTORICAL_URL
            
            # Calculate time range
            end_time = int(datetime.now(timezone.utc).timestamp())
            start_time = int((datetime.now(timezone.utc) - timedelta(days=self.days)).timestamp())
            
            params = {
                'symbol': self.symbol,
                'resolution': self.resolution,
                'start': start_time,
                'end': end_time
            }
            
            with httpx.Client() as client:
                response = client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                candles = result.get('result', [])
            
            if not candles:
                self.ui.print_error(f"No data found for {self.symbol}")
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
            
            self.ui.print_success(f"Successfully fetched {len(self.df)} candles for {self.symbol}")
            return True
            
        except httpx.RequestError as e:
            self.ui.print_error(f"Failed to fetch data: {e}")
            return False
        except Exception as e:
            self.ui.print_error(f"Error processing data: {e}")
            return False
    
    def calculate_indicators(self) -> None:
        """Calculate all technical indicators using the proven approach"""
        if self.df is None or self.df.empty:
            self.ui.print_error("No data available for indicator calculation")
            return
        
        try:
            # Clear applied indicators for fresh calculation
            self.applied_indicators = []
            
            # Calculate EMAs
            for period in self.settings.EMA_PERIODS:
                self.df[f'EMA_{period}'] = ta.ema(self.df['close'], length=period)
                self.applied_indicators.append(('EMA', period))
            
            # Calculate RSI
            rsi_period = self.settings.RSI_PERIOD
            self.df[f'RSI_{rsi_period}'] = ta.rsi(self.df['close'], length=rsi_period)
            self.applied_indicators.append(('RSI', rsi_period))
            
            # Calculate MACD
            fast = self.settings.MACD_SETTINGS['fast']
            slow = self.settings.MACD_SETTINGS['slow']
            signal = self.settings.MACD_SETTINGS['signal']
            
            macd_data = ta.macd(self.df['close'], fast=fast, slow=slow, signal=signal)
            self.df[f'MACD_{fast}_{slow}_{signal}'] = macd_data[f'MACD_{fast}_{slow}_{signal}']
            self.df[f'MACDs_{fast}_{slow}_{signal}'] = macd_data[f'MACDs_{fast}_{slow}_{signal}']
            self.df[f'MACDh_{fast}_{slow}_{signal}'] = macd_data[f'MACDh_{fast}_{slow}_{signal}']
            self.applied_indicators.append(('MACD', (fast, slow, signal)))
            
            # Calculate ATR
            atr_period = self.settings.ATR_PERIOD
            self.df[f'ATR_{atr_period}'] = ta.atr(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                length=atr_period
            )
            self.applied_indicators.append(('ATR', atr_period))
            
            # Calculate Stochastic
            stoch_period = self.settings.STOCH_PERIOD
            stoch_data = ta.stoch(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                k=stoch_period,
                d=3,
                smooth_k=3
            )
            self.df[f'STOCHk_{stoch_period}_3_3'] = stoch_data[f'STOCHk_{stoch_period}_3_3']
            self.df[f'STOCHd_{stoch_period}_3_3'] = stoch_data[f'STOCHd_{stoch_period}_3_3']
            self.applied_indicators.append(('Stochastic', stoch_period))
            
            # Calculate VWAP
            self.df['VWAP'] = ta.vwap(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                self.df['volume']
            )
            self.applied_indicators.append(('VWAP', None))
            
            # Calculate Supertrend
            st_period = self.settings.SUPERTREND_PERIOD
            st_multiplier = self.settings.SUPERTREND_MULTIPLIER
            
            supertrend_data = ta.supertrend(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                length=st_period,
                multiplier=st_multiplier
            )
            
            self.df[f'SUPERT_{st_period}_{st_multiplier}'] = supertrend_data[f'SUPERT_{st_period}_{st_multiplier}']
            self.df[f'SUPERTd_{st_period}_{st_multiplier}'] = supertrend_data[f'SUPERTd_{st_period}_{st_multiplier}']
            self.df[f'SUPERTl_{st_period}_{st_multiplier}'] = supertrend_data[f'SUPERTl_{st_period}_{st_multiplier}']
            self.df[f'SUPERTs_{st_period}_{st_multiplier}'] = supertrend_data[f'SUPERTs_{st_period}_{st_multiplier}']
            self.applied_indicators.append(('Supertrend', (st_period, st_multiplier)))
            
            # Calculate ADX
            adx_period = self.settings.ADX_PERIOD
            adx_data = ta.adx(
                self.df['high'],
                self.df['low'],
                self.df['close'],
                length=adx_period
            )
            
            self.df[f'ADX_{adx_period}'] = adx_data[f'ADX_{adx_period}']
            self.df[f'DMP_{adx_period}'] = adx_data[f'DMP_{adx_period}']
            self.df[f'DMN_{adx_period}'] = adx_data[f'DMN_{adx_period}']
            self.applied_indicators.append(('ADX', adx_period))
            
            # Calculate Z-Score
            zscore_period = self.settings.ZSCORE_PERIOD
            rolling_mean = self.df['close'].rolling(window=zscore_period).mean()
            rolling_std = self.df['close'].rolling(window=zscore_period).std()
            self.df[f'ZSCORE_{zscore_period}'] = (self.df['close'] - rolling_mean) / rolling_std
            self.applied_indicators.append(('ZSCORE', zscore_period))
            
            self.ui.print_success(f"Successfully calculated {len(self.applied_indicators)} indicators")
            
        except Exception as e:
            self.ui.print_error(f"Error calculating indicators: {e}")
            import traceback
            traceback.print_exc()
    
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
                if f'EMA_{period}' in latest:
                    ema_value = latest[f'EMA_{period}']
                    if pd.notna(ema_value):
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
            rsi_col = f'RSI_{self.settings.RSI_PERIOD}'
            if rsi_col in latest:
                rsi_value = latest[rsi_col]
                if pd.notna(rsi_value):
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
            
            # Analyze MACD
            fast = self.settings.MACD_SETTINGS['fast']
            slow = self.settings.MACD_SETTINGS['slow']
            signal_period = self.settings.MACD_SETTINGS['signal']
            
            macd_col = f'MACD_{fast}_{slow}_{signal_period}'
            signal_col = f'MACDs_{fast}_{slow}_{signal_period}'
            
            if macd_col in latest and signal_col in latest:
                macd_value = latest[macd_col]
                macd_signal = latest[signal_col]
                
                if pd.notna(macd_value) and pd.notna(macd_signal):
                    if macd_value > macd_signal:
                        signal = "📈 Bullish"
                        interpretation = "Above Signal"
                    else:
                        signal = "📉 Bearish"
                        interpretation = "Below Signal"
                    
                    self.indicators.append(IndicatorResult(
                        name="MACD",
                        value=f"{macd_value:.4f}",
                        signal=signal,
                        interpretation=interpretation
                    ))
            
            # Analyze ATR
            atr_col = f'ATR_{self.settings.ATR_PERIOD}'
            if atr_col in latest:
                atr_value = latest[atr_col]
                if pd.notna(atr_value):
                    self.indicators.append(IndicatorResult(
                        name=f"ATR_{self.settings.ATR_PERIOD}",
                        value=f"{atr_value:.2f}",
                        signal="📊 Volatility",
                        interpretation="Risk Measure"
                    ))
            
            # Analyze Stochastic
            stoch_k_col = f'STOCHk_{self.settings.STOCH_PERIOD}_3_3'
            stoch_d_col = f'STOCHd_{self.settings.STOCH_PERIOD}_3_3'
            
            if stoch_k_col in latest and stoch_d_col in latest:
                stoch_k = latest[stoch_k_col]
                stoch_d = latest[stoch_d_col]
                
                if pd.notna(stoch_k) and pd.notna(stoch_d):
                    if stoch_k > 80:
                        signal = "🔴 Overbought"
                        interpretation = "Sell Zone"
                    elif stoch_k < 20:
                        signal = "🟢 Oversold"
                        interpretation = "Buy Zone"
                    else:
                        signal = "⚪ Normal"
                        interpretation = "Neutral"
                    
                    self.indicators.append(IndicatorResult(
                        name="Stochastic",
                        value=f"{stoch_k:.1f}",
                        signal=signal,
                        interpretation=interpretation
                    ))
            
            # Analyze VWAP
            if 'VWAP' in latest:
                vwap_value = latest['VWAP']
                if pd.notna(vwap_value):
                    if current_price > vwap_value:
                        signal = "📈 Above VWAP"
                        interpretation = "Bullish"
                    else:
                        signal = "📉 Below VWAP"
                        interpretation = "Bearish"
                    
                    self.indicators.append(IndicatorResult(
                        name="VWAP",
                        value=f"{vwap_value:.2f}",
                        signal=signal,
                        interpretation=interpretation
                    ))
            
            # Analyze Supertrend
            st_period = self.settings.SUPERTREND_PERIOD
            st_multiplier = self.settings.SUPERTREND_MULTIPLIER
            supert_col = f'SUPERT_{st_period}_{st_multiplier}'
            supertd_col = f'SUPERTd_{st_period}_{st_multiplier}'
            
            if supert_col in latest and supertd_col in latest:
                supert_value = latest[supert_col]
                supert_direction = latest[supertd_col]
                
                if pd.notna(supert_value) and pd.notna(supert_direction):
                    if supert_direction == 1:  # Bullish trend
                        signal = "🟢 Bullish Trend"
                        interpretation = "Strong Buy"
                    else:  # Bearish trend
                        signal = "🔴 Bearish Trend"
                        interpretation = "Strong Sell"
                    
                    self.indicators.append(IndicatorResult(
                        name="Supertrend",
                        value=f"{supert_value:.2f}",
                        signal=signal,
                        interpretation=interpretation
                    ))
            
            # Analyze ADX
            adx_period = self.settings.ADX_PERIOD
            adx_col = f'ADX_{adx_period}'
            dmp_col = f'DMP_{adx_period}'
            dmn_col = f'DMN_{adx_period}'
            
            if adx_col in latest and dmp_col in latest and dmn_col in latest:
                adx_value = latest[adx_col]
                dmp_value = latest[dmp_col]
                dmn_value = latest[dmn_col]
                
                if pd.notna(adx_value) and pd.notna(dmp_value) and pd.notna(dmn_value):
                    if adx_value > 25:
                        if dmp_value > dmn_value:
                            signal = "💪 Strong Uptrend"
                            interpretation = "Strong Bullish"
                        else:
                            signal = "💪 Strong Downtrend"
                            interpretation = "Strong Bearish"
                    elif adx_value > 20:
                        signal = "📊 Moderate Trend"
                        interpretation = "Trending Market"
                    else:
                        signal = "➡️ Weak Trend"
                        interpretation = "Sideways Market"
                    
                    self.indicators.append(IndicatorResult(
                        name="ADX",
                        value=f"{adx_value:.2f}",
                        signal=signal,
                        interpretation=interpretation
                    ))
            
            # Analyze Z-Score
            zscore_col = f'ZSCORE_{self.settings.ZSCORE_PERIOD}'
            if zscore_col in latest:
                zscore_value = latest[zscore_col]
                if pd.notna(zscore_value):
                    if zscore_value > 2:
                        signal = "🔴 Extremely High"
                        interpretation = "Overbought"
                    elif zscore_value > 1:
                        signal = "🟡 High"
                        interpretation = "Above Normal"
                    elif zscore_value < -2:
                        signal = "🟢 Extremely Low"
                        interpretation = "Oversold"
                    elif zscore_value < -1:
                        signal = "🟡 Low"
                        interpretation = "Below Normal"
                    else:
                        signal = "⚪ Normal"
                        interpretation = "Average Range"
                    
                    self.indicators.append(IndicatorResult(
                        name="Z-Score",
                        value=f"{zscore_value:.2f}",
                        signal=signal,
                        interpretation=interpretation
                    ))
            
            self.ui.print_success(f"Successfully analyzed {len(self.indicators)} indicators")
            
        except Exception as e:
            self.ui.print_error(f"Error analyzing indicators: {e}")
            import traceback
            traceback.print_exc()
    
    def analyze_strategies(self) -> None:
        """Analyze trading strategies using the strategy manager"""
        if self.df is None or self.df.empty:
            return
        
        try:
            # Use the strategy manager to analyze all strategies
            self.strategy_results = self.strategy_manager.analyze_all(self.df)
            
            # Get AI analysis result if available
            for strategy in self.strategy_manager.strategies:
                if hasattr(strategy, 'get_ai_analysis') and strategy.name == "AI Powered":
                    self.ai_analysis_result = strategy.get_ai_analysis()
                    break
            
        except Exception as e:
            self.ui.print_error(f"Error analyzing strategies: {e}")
            self.strategy_results = []
    
    def get_analysis_results(self) -> Dict[str, Any]:
        """Get complete analysis results"""
        # Get strategies results
        strategies_dict = []
        for result in self.strategy_results:
            strategies_dict.append({
                'name': result.name,
                'signal': result.signal.value,
                'confidence': result.confidence.value,
                'strength': result.strength,
                'interpretation': result.interpretation
            })
        
        # Calculate consensus
        if self.strategy_results:
            consensus = self.strategy_manager.get_consensus_signal(self.strategy_results)
        else:
            consensus = {
                'signal': 'NEUTRAL',
                'confidence': 'VERY_LOW',
                'strength': 0,
                'interpretation': 'No strategies analyzed'
            }
        
        return {
            'symbol': self.symbol,
            'resolution': self.resolution,
            'days': self.days,
            'indicators': [vars(i) for i in self.indicators],
            'strategies': strategies_dict,
            'consensus': consensus,
            'ai_analysis': self.ai_analysis_result
        }
    
    def refresh(self) -> bool:
        """Refresh all data and analysis"""
        try:
            success = self.fetch_historical_data()
            if success:
                self.calculate_indicators()
                self.analyze_indicators()
                self.analyze_strategies()
                return True
            return False
        except Exception as e:
            self.ui.print_error(f"Error during refresh: {e}")
            return False 