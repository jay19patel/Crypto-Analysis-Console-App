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


class AnalysisManager:
    """
    Complete technical analysis management including execution and display
    """
    
    def __init__(self):
        self.console = Console()
    
    def setup_default_indicators(self, data):
        """Setup default technical indicators for analysis"""
        try:
            self.print_message("🔧 Setting up default indicators...", "cyan")
            data.EMA([5, 15, 50])
            data.RSI(14)
            data.MACD()
            data.ATR(14)  # Added ATR to default indicators
            data.Supertrend()
            data.ADX()
            data.VWAP()
            data.ZSCORE(20)
            self.print_message("✅ All default indicators loaded successfully!", "green")
        except Exception as e:
            self.print_message(f"❌ Error setting up indicators: {e}", "red")
            raise
    
    def run_single_analysis(self, symbol, resolution='5m', days=10):
        """
        Run analysis once
        
        Args:
            symbol (str): Trading symbol
            resolution (str): Timeframe
            days (int): Historical data days
        """
        try:
            self.print_message(f"🚀 Initializing analysis for {symbol}...", "cyan")
            data = HistoricalData(symbol=symbol, resolution=resolution, days=days)
            
            self.setup_default_indicators(data)
            
            self.print_message("✅ Analysis ready!", "green")
            self.print_message("=" * 80, "white")
            
            self.show_analysis(data)
            
            return True
            
        except Exception as e:
            self.print_message(f"❌ Error: {e}", "red")
            return False
    
    def run_analysis_loop(self, symbol, refresh_interval, resolution='5m', days=10):
        """
        Run analysis in a loop with specified refresh interval
        
        Args:
            symbol (str): Trading symbol
            refresh_interval (int): Refresh interval in seconds
            resolution (str): Timeframe
            days (int): Historical data days
        """
        try:
            # Initialize data
            self.print_message(f"🚀 Initializing analysis for {symbol}...", "cyan")
            data = HistoricalData(symbol=symbol, resolution=resolution, days=days)
            
            # Setup default indicators
            self.setup_default_indicators(data)
            
            self.print_message(f"🔄 Starting analysis loop - refreshing every {refresh_interval} seconds", "green")
            self.print_message("Press Ctrl+C to stop", "yellow")
            self.print_message("=" * 80, "white")
            
            while True:
                try:
                    # Clear screen for better display
                    self.clear_screen()
                    
                    # Show analysis
                    self.show_analysis(data)
                    
                    # Wait for next refresh
                    self.print_message(f"\n⏳ Next refresh in {refresh_interval} seconds... (Press Ctrl+C to stop)", "dim white")
                    time.sleep(refresh_interval)
                    
                    # Refresh data and indicators
                    self.print_message("🔄 Refreshing data...", "cyan")
                    data.refresh()
                    
                except KeyboardInterrupt:
                    self.print_message("\n🛑 Analysis stopped by user", "yellow")
                    break
                except Exception as e:
                    self.print_message(f"\n❌ Error during analysis: {e}", "red")
                    self.print_message(f"⏳ Retrying in {refresh_interval} seconds...", "yellow")
                    time.sleep(refresh_interval)
            
            return True
                    
        except Exception as e:
            self.print_message(f"❌ Failed to initialize: {e}", "red")
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
        
        # Header Panel
        header_text = Text(f"📊 TECHNICAL ANALYSIS DASHBOARD", style="bold white")
        header_panel = Panel(
            header_text,
            title=f"🚀 {data.symbol}",
            title_align="left",
            border_style="blue",
            box=box.DOUBLE_EDGE
        )
        
        # Price Info Table
        price_table = self._create_price_table(data, latest, current_price)
        
        # Technical Indicators Table
        indicators_table = self._create_indicators_table(data, latest, current_price)
        
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
        self._show_footer()
    
    def _create_price_table(self, data, latest, current_price):
        """Create price information table"""
        price_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        price_table.add_column("📈 Market Data", style="cyan", width=20)
        price_table.add_column("💰 Value", style="yellow", width=25)
        price_table.add_column("📊 Status", style="green", width=20)
        
        # Calculate change if possible
        if len(data.df) > 1:
            prev_price = data.df.iloc[-2]['close']
            change = current_price - prev_price
            change_pct = (change / prev_price) * 100
            change_color = "green" if change >= 0 else "red"
            change_symbol = "📈" if change >= 0 else "📉"
            change_text = f"[{change_color}]{change_symbol} {change:+.4f} ({change_pct:+.2f}%)[/{change_color}]"
        else:
            change_text = "[white]N/A[/white]"
        
        price_table.add_row("💵 Current Price", f"{current_price:.4f}", change_text)
        price_table.add_row("📅 Last Update", f"{data.df.index[-1].strftime('%Y-%m-%d %I:%M:%S %p')}", "🔄 Live")
        price_table.add_row("📊 Volume", f"{latest['volume']:,.0f}", "📦 Active")
        price_table.add_row("🎯 High", f"{latest['high']:.4f}", "⬆️")
        price_table.add_row("🎯 Low", f"{latest['low']:.4f}", "⬇️")
        
        return price_table
    
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
    
    def _show_footer(self):
        """Display footer with timestamp"""
        footer_text = f"⏰ Analysis generated at: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')} IST"
        footer_panel = Panel(
            footer_text,
            border_style="blue",
            box=box.ASCII
        )
        self.console.print("")
        self.console.print(footer_panel)
    
    def print_message(self, message, style="white"):
        """Print a styled message"""
        self.console.print(f"[{style}]{message}[/{style}]")
    
    def clear_screen(self):
        """Clear the console screen"""
        self.console.clear() 