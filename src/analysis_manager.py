#!/usr/bin/env python3
"""
Technical Analysis Manager Module
Handles analysis execution, display, and indicator management
Combined functionality from analysis_runner and analysis_display
"""

import time
import sys
import pandas as pd
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from technical_analysis import HistoricalData
from trading_strategies import TradingStrategies


class AnalysisManager:
    """
    Complete technical analysis management including execution and display
    Handles UI/display while HistoricalData focuses on data & calculations
    
    Usage:
        # Initialize and run single analysis
        manager = AnalysisManager()
        manager.run_single_analysis("BTCUSD")
        
        # Run continuous analysis loop
        manager.run_analysis_loop("ETHUSD", refresh_interval=30)
        
        # Manual control
        manager.initialize_data("BTCUSD", resolution="1h", days=30)
        manager.add_indicator("EMA", [10, 20, 50])
        manager.show_analysis(manager.data)
        manager.refresh_analysis()
        
        # Direct data access
        data = manager.get_current_data()
        df = data.get_data() if data else None
    """
    
    def __init__(self):
        self.console = Console()
        self.data = None  # Current HistoricalData instance
    
    def setup_default_indicators(self, data):
        """Setup default technical indicators for analysis"""
        try:
            self.print_message("🔧 Setting up default indicators...", "cyan")
            data.EMA([5, 15, 50])
            data.RSI(14)
            data.MACD()
            data.ATR(14)
            data.Supertrend()
            data.ADX()
            data.VWAP()
            data.ZSCORE(20)
            data.Stochastic(14)  # Added Stochastic indicator
            self.print_message("✅ All default indicators loaded successfully!", "green")
        except Exception as e:
            self.print_message(f"❌ Error setting up indicators: {e}", "red")
            raise
    
    def initialize_data(self, symbol, resolution='5m', days=10):
        """
        Initialize data with technical indicators
        
        Args:
            symbol (str): Trading symbol
            resolution (str): Timeframe  
            days (int): Historical data days
            
        Returns:
            bool: Success status
        """
        try:
            self.print_message(f"🚀 Initializing analysis for {symbol}...", "cyan")
            self.data = HistoricalData(symbol=symbol, resolution=resolution, days=days)
            
            self.setup_default_indicators(self.data)
            
            self.print_message("✅ Analysis ready!", "green")
            return True
            
        except Exception as e:
            self.print_message(f"❌ Error: {e}", "red")
            return False
    
    def run_single_analysis(self, symbol, resolution='5m', days=10):
        """
        Run analysis once
        
        Args:
            symbol (str): Trading symbol
            resolution (str): Timeframe
            days (int): Historical data days
        """
        if not self.initialize_data(symbol, resolution, days):
            return False
            
        self.print_message("=" * 80, "white")
        self.show_analysis(self.data)
        return True
    
    def run_analysis_loop(self, symbol, refresh_interval, resolution='5m', days=10):
        """
        Run analysis in a loop with specified refresh interval
        
        Args:
            symbol (str): Trading symbol
            refresh_interval (int): Refresh interval in seconds
            resolution (str): Timeframe
            days (int): Historical data days
        """
        # Initialize data first
        if not self.initialize_data(symbol, resolution, days):
            return False
        
        try:
            self.print_message(f"🔄 Starting analysis loop - refreshing every {refresh_interval} seconds", "green")
            self.print_message("Press Ctrl+C to stop", "yellow")
            self.print_message("=" * 80, "white")
            
            while True:
                try:
                    # Clear screen for better display
                    self.clear_screen()
                    
                    # Show analysis
                    self.show_analysis(self.data)
                    
                    # Wait for next refresh
                    self.print_message(f"\n⏳ Next refresh in {refresh_interval} seconds... (Press Ctrl+C to stop)", "dim white")
                    time.sleep(refresh_interval)
                    
                    # Refresh data and indicators
                    self.print_message("🔄 Refreshing data...", "cyan")
                    self.data.refresh()
                    
                except KeyboardInterrupt:
                    self.print_message("\n🛑 Analysis stopped by user", "yellow")
                    break
                except Exception as e:
                    self.print_message(f"\n❌ Error during analysis: {e}", "red")
                    self.print_message(f"⏳ Retrying in {refresh_interval} seconds...", "yellow")
                    time.sleep(refresh_interval)
            
            return True
                    
        except Exception as e:
            self.print_message(f"❌ Failed to start analysis loop: {e}", "red")
            return False
    
    def check_requirements(self):
        """
        Check if all required dependencies are available
        
        Returns:
            bool: True if all requirements are met
        """
        try:
            # Test imports
            import pandas as pd
            import pandas_ta as ta
            import httpx
            import numpy as np
            from rich.console import Console
            
            self.print_message("✅ All technical analysis dependencies are available", "green")
            return True
            
        except ImportError as e:
            self.print_message(f"❌ Missing dependency: {e}", "red")
            self.print_message("Please install required packages: pip install -r requirements.txt", "yellow")
            return False
        except Exception as e:
            self.print_message(f"❌ Error checking requirements: {e}", "red")
            return False
    
    def show_analysis(self, data):
        """
        Display current market analysis with attractive console-based tables
        
        Args:
            data: HistoricalData instance with calculated indicators
        """
        if data.df is None:
            self.console.print("[red]❌ No data available.[/red]")
            return
        
        latest = data.df.iloc[-1]
        current_price = latest['close']
        
        # Technical Indicators Table
        indicators_table = self._create_indicators_table(data, latest, current_price)
        
        # Trading Strategies Table
        strategies_table = self._create_strategies_table(data)
        
        if len(indicators_table.rows) > 0:
            # Create detailed title with all info
            timestamp = data.df.index[-1].strftime('%Y-%m-%d %I:%M:%S %p')
            panel_title = f"🔍 {data.symbol} | Resolution: {data.resolution} | History: {data.days} days | {timestamp}"
            
            # Create a combined panel with both tables
            indicators_panel = Panel(
                indicators_table,
                title=panel_title,
                border_style="green",
                box=box.ROUNDED
            )
            self.console.print(indicators_panel)
            
            # Show strategies panel separately
            if len(strategies_table.rows) > 0:
                strategies_panel = Panel(
                    strategies_table,
                    title="📊 Trading Strategies Analysis",
                    border_style="cyan",
                    box=box.ROUNDED
                )
                self.console.print(strategies_panel)
        else:
            self.console.print(Panel(
                "[yellow]No technical indicators calculated yet. Use methods like EMA(), RSI(), MACD() to add indicators.[/yellow]",
                title="ℹ️ Information",
                border_style="yellow"
            ))
    
    def _create_indicators_table(self, data, latest, current_price):
        """Create technical indicators table"""
        indicators_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        indicators_table.add_column("🔍 Indicator", style="white", width=18)
        indicators_table.add_column("📊 Value", style="yellow", width=15)
        indicators_table.add_column("🎯 Signal", style="bold", width=25)
        indicators_table.add_column("💡 Interpretation", style="cyan", width=20)
        
        # Add various analysis methods - ALL AVAILABLE INDICATORS
        self._add_ema_analysis(indicators_table, data.df, latest, current_price)
        self._add_rsi_analysis(indicators_table, data.df, latest)
        self._add_macd_analysis(indicators_table, data.df, latest)
        self._add_atr_analysis(indicators_table, data.df, latest)
        self._add_supertrend_analysis(indicators_table, data.df, latest)
        self._add_vwap_analysis(indicators_table, data.df, latest, current_price)
        self._add_adx_analysis(indicators_table, data.df, latest)
        self._add_zscore_analysis(indicators_table, data.df, latest)
        
        return indicators_table
    
    def _add_ema_analysis(self, table, df, latest, current_price):
        """Add EMA analysis to indicators table"""
        ema_cols = [col for col in df.columns if col.startswith('EMA_')]
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
                
                table.add_row(f"📊 EMA_{period}", f"{ema_value:.4f}", signal, interpretation)
    
    def _add_atr_analysis(self, table, df, latest):
        """Add ATR analysis to indicators table"""
        atr_cols = [col for col in df.columns if col.startswith('ATR_')]
        for col in atr_cols:
            if not pd.isna(latest[col]):
                atr_value = latest[col]
                period = col.split('_')[1]
                
                # ATR interpretation based on volatility
                if atr_value > latest['close'] * 0.02:  # More than 2% of price
                    signal = "[red]🔥 High Volatility[/red]"
                    interpretation = "[red]Volatile[/red]"
                elif atr_value > latest['close'] * 0.01:  # More than 1% of price
                    signal = "[yellow]⚡ Medium Volatility[/yellow]"
                    interpretation = "[yellow]Moderate[/yellow]"
                else:
                    signal = "[green]😌 Low Volatility[/green]"
                    interpretation = "[green]Stable[/green]"
                
                table.add_row(f"📏 ATR_{period}", f"{atr_value:.4f}", signal, interpretation)
    
    def _add_rsi_analysis(self, table, df, latest):
        """Add RSI analysis to indicators table"""
        rsi_cols = [col for col in df.columns if col.startswith('RSI_')]
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
                table.add_row(f"📊 {col}", f"{rsi_value:.2f}", signal, interpretation)
    
    def _add_macd_analysis(self, table, df, latest):
        """Add MACD analysis to indicators table"""
        macd_cols = [col for col in df.columns if col.startswith('MACD_') and not 'Signal' in col and not 'Histogram' in col]
        for col in macd_cols:
            if not pd.isna(latest[col]):
                signal_col = col.replace('MACD_', 'MACD_Signal_').split('_')
                signal_col = 'MACD_Signal_' + signal_col[-1]
                
                if signal_col in df.columns:
                    macd_val = latest[col]
                    signal_val = latest[signal_col]
                    
                    if macd_val > signal_val:
                        signal = "[green]📈 Bullish[/green]"
                        interpretation = "[green]Uptrend[/green]"
                    else:
                        signal = "[red]📉 Bearish[/red]"
                        interpretation = "[red]Downtrend[/red]"
                    table.add_row("🎯 MACD", f"{macd_val:.4f}", signal, interpretation)
    
    def _add_supertrend_analysis(self, table, df, latest):
        """Add Supertrend analysis to indicators table"""
        st_signal_cols = [col for col in df.columns if col == 'Supertrend_Signal']
        for col in st_signal_cols:
            if not pd.isna(latest[col]):
                if latest[col] == 1:
                    signal = "[green]🟢 UPTREND[/green]"
                    interpretation = "[green]Buy Zone[/green]"
                else:
                    signal = "[red]🔴 DOWNTREND[/red]"
                    interpretation = "[red]Sell Zone[/red]"
                table.add_row("⚡ Supertrend", f"{latest[col]}", signal, interpretation)
    
    def _add_vwap_analysis(self, table, df, latest, current_price):
        """Add VWAP analysis to indicators table"""
        if 'VWAP' in df.columns and not pd.isna(latest['VWAP']):
            vwap_val = latest['VWAP']
            if current_price > vwap_val:
                signal = "[green]📈 Above VWAP[/green]"
                interpretation = "[green]Bullish[/green]"
            else:
                signal = "[red]📉 Below VWAP[/red]"
                interpretation = "[red]Bearish[/red]"
            table.add_row("💎 VWAP", f"{vwap_val:.4f}", signal, interpretation)
    
    def _add_adx_analysis(self, table, df, latest):
        """Add ADX analysis to indicators table"""
        adx_cols = [col for col in df.columns if col.startswith('ADX_')]
        for col in adx_cols:
            if not pd.isna(latest[col]):
                adx_val = latest[col]
                window = col.split('_')[1]
                
                di_plus_col = f'DI_Plus_{window}'
                di_minus_col = f'DI_Minus_{window}'
                
                if di_plus_col in df.columns and di_minus_col in df.columns:
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
                    
                    table.add_row("🎪 ADX", f"{adx_val:.2f}", f"{strength} {direction}", interpretation)
    
    def _add_zscore_analysis(self, table, df, latest):
        """Add Z-Score analysis to indicators table"""
        zscore_cols = [col for col in df.columns if col.startswith('ZSCORE_')]
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
                
                table.add_row(f"📐 {col}", f"{zscore_val:.2f}", signal, interpretation)
    
    def _create_strategies_table(self, data) -> Table:
        """Create trading strategies analysis table"""
        strategies_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        strategies_table.add_column("📈 Strategy", style="white", width=20)
        strategies_table.add_column("🎯 Signal", style="bold", width=15)
        strategies_table.add_column("💪 Strength", style="yellow", width=15)
        strategies_table.add_column("✅ Conditions Met", style="green", width=30)
        strategies_table.add_column("❌ Failed Conditions", style="red", width=30)
        
        # Initialize trading strategies
        strategies = TradingStrategies(data)
        
        # Get signals from all strategies
        signals = strategies.analyze_all()
        
        # Add each strategy to the table
        for signal in signals:
            # Format signal color based on type
            signal_color = {
                "BUY": "[green]",
                "SELL": "[red]",
                "NEUTRAL": "[yellow]"
            }.get(signal.signal, "[white]")
            
            # Format strength with color gradient
            strength_color = "[green]" if signal.strength >= 70 else "[yellow]" if signal.strength >= 30 else "[red]"
            
            strategies_table.add_row(
                signal.strategy_name,
                f"{signal_color}{signal.signal}[/]",
                f"{strength_color}{signal.strength:.1f}%[/]",
                "\n".join(signal.conditions_met) if signal.conditions_met else "-",
                "\n".join(signal.conditions_failed) if signal.conditions_failed else "-"
            )
        
        return strategies_table
    
    def print_message(self, message, style="white"):
        """Print a styled message"""
        self.console.print(f"[{style}]{message}[/{style}]")
    
    def refresh_analysis(self):
        """
        Refresh current data and show updated analysis
        
        Returns:
            bool: Success status
        """
        if self.data is None:
            self.print_message("❌ No data initialized. Call initialize_data() first.", "red")
            return False
        
        try:
            self.print_message("🔄 Refreshing data...", "cyan")
            self.data.refresh()
            self.show_analysis(self.data)
            return True
        except Exception as e:
            self.print_message(f"❌ Error refreshing data: {e}", "red")
            return False
    
    def get_current_data(self):
        """
        Get current HistoricalData instance
        
        Returns:
            HistoricalData: Current data instance or None
        """
        return self.data
    
    def add_indicator(self, indicator_name, *args, **kwargs):
        """
        Add a new indicator to current data
        
        Args:
            indicator_name (str): Name of indicator (EMA, RSI, MACD, etc.)
            *args: Arguments for the indicator
            **kwargs: Keyword arguments for the indicator
            
        Returns:
            bool: Success status
        """
        if self.data is None:
            self.print_message("❌ No data initialized. Call initialize_data() first.", "red")
            return False
        
        try:
            method = getattr(self.data, indicator_name)
            method(*args, **kwargs)
            self.print_message(f"✅ Added {indicator_name} indicator", "green")
            return True
        except AttributeError:
            self.print_message(f"❌ Indicator {indicator_name} not found", "red")
            return False
        except Exception as e:
            self.print_message(f"❌ Error adding {indicator_name}: {e}", "red")
            return False
    
    def clear_screen(self):
        """Clear the console screen"""
        self.console.clear() 