#!/usr/bin/env python3
"""
Web Viewer for Trading System
Connects to WebSocket server and displays real-time trading data
"""

import asyncio
import json
import argparse
import websockets
import os
import sys
from datetime import datetime
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.columns import Columns
from rich.align import Align

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.config import get_settings

# Create global config instance
settings = get_settings()

class TradingViewer:
    def __init__(self, channel: str):
        self.channel = channel
        self.console = Console()
        self.websocket = None
        self.running = True  # Changed to True by default
        self.latest_data = None
        self.connection_status = "🔴 Disconnected"
        self.reconnect_delay = 2  # seconds
        self.max_reconnect_delay = 30  # seconds
        
    async def connect(self):
        """Connect to WebSocket server with retry"""
        current_delay = self.reconnect_delay
        
        while self.running:
            try:
                uri = f"ws://{settings.WEBSOCKET_SERVER_HOST}:{settings.WEBSOCKET_SERVER_PORT}/{self.channel}"
                self.websocket = await websockets.connect(uri)
                self.connection_status = "🟢 Connected"
                return True
            except Exception as e:
                self.connection_status = f"🔴 Connection Error: {e}"
                self.console.print(f"[yellow]Connection failed. Retrying in {current_delay} seconds...[/yellow]")
                await asyncio.sleep(current_delay)
                current_delay = min(current_delay * 2, self.max_reconnect_delay)
        
        return False
    
    async def listen(self):
        """Listen for WebSocket messages with auto-reconnect"""
        while self.running:
            try:
                async for message in self.websocket:
                    data = json.loads(message)
                    if data.get('type') == self.channel:
                        self.latest_data = data
                    elif data.get('type') == 'error':
                        self.connection_status = f"🔴 Error: {data.get('message', 'Unknown error')}"
            except websockets.exceptions.ConnectionClosed:
                self.connection_status = "🔴 Connection Closed"
                if self.running:
                    self.console.print("[yellow]Connection lost. Attempting to reconnect...[/yellow]")
                    await self.connect()
            except Exception as e:
                self.connection_status = f"🔴 Error: {e}"
                if self.running:
                    self.console.print(f"[red]Error: {e}. Attempting to reconnect...[/red]")
                    await self.connect()
    
    def create_header(self) -> Panel:
        """Create header panel"""
        title = {
            'analysis': '📊 AI Trading Analysis Dashboard',
            'liveprice': '💰 Live Price Monitor',
            'broker': '🏦 Broker Trading Dashboard',
            'logs': '📜 Trading System Logs'
        }.get(self.channel, f'{self.channel.title()} Dashboard')
        
        return Panel(
            Align.center(f"[bold cyan]{title}[/bold cyan]\n{self.connection_status}"),
            title="[bold white]Trading System Viewer[/bold white]",
            border_style="cyan"
        )
    
    def create_analysis_view(self, data: Dict) -> Layout:
        """Create analysis view layout"""
        layout = Layout()
        
        if not data or 'data' not in data:
            layout.split_row(
                Layout(Panel("[yellow]Waiting for analysis data...[/yellow]", title="Status"))
            )
            return layout
        
        analysis_data = data['data']
        
        # Create main analysis table
        main_table = Table(title="🤖 AI Trading Analysis", show_header=True, header_style="bold magenta")
        main_table.add_column("Metric", style="cyan", no_wrap=True)
        main_table.add_column("Value", style="yellow")
        
        # Add key analysis metrics
        if 'summary' in analysis_data:
            main_table.add_row("📋 Summary", analysis_data['summary'])
        if 'current_trend' in analysis_data:
            main_table.add_row("📈 Current Trend", analysis_data['current_trend'])
        if 'signal' in analysis_data:
            main_table.add_row("🎯 Signal", analysis_data['signal'])
        if 'confidence' in analysis_data:
            main_table.add_row("🔥 Confidence", f"{analysis_data['confidence']}%")
        
        # Create price levels table
        price_table = Table(title="💰 Price Levels", show_header=True, header_style="bold green")
        price_table.add_column("Level", style="cyan")
        price_table.add_column("Price", style="yellow")
        
        if 'entry_price' in analysis_data:
            price_table.add_row("🎯 Entry", f"${analysis_data['entry_price']}")
        if 'stop_loss' in analysis_data:
            price_table.add_row("🛑 Stop Loss", f"${analysis_data['stop_loss']}")
        if 'take_profit' in analysis_data:
            price_table.add_row("🎊 Take Profit", f"${analysis_data['take_profit']}")
        
        # Create indicators table
        indicators_table = Table(title="📊 Technical Indicators", show_header=True, header_style="bold blue")
        indicators_table.add_column("Indicator", style="cyan")
        indicators_table.add_column("Value", style="yellow")
        
        if 'rsi' in analysis_data:
            indicators_table.add_row("RSI", f"{analysis_data['rsi']:.2f}")
        if 'macd_signal' in analysis_data:
            indicators_table.add_row("MACD", analysis_data['macd_signal'])
        if 'bollinger_signal' in analysis_data:
            indicators_table.add_row("Bollinger", analysis_data['bollinger_signal'])
        
        # Layout arrangement
        layout.split_row(
            Layout(Panel(main_table, border_style="magenta")),
            Layout(Panel(price_table, border_style="green"))
        )
        
        return layout
    
    def create_liveprice_view(self, data: Dict) -> Layout:
        """Create live price view layout"""
        layout = Layout()
        
        if not data or 'data' not in data:
            layout.split_row(
                Layout(Panel("[yellow]Waiting for live price data...[/yellow]", title="Status"))
            )
            return layout
        
        price_data = data['data']
        
        # Create price display
        price_table = Table(title="💰 Live Price Data", show_header=True, header_style="bold green")
        price_table.add_column("Symbol", style="cyan", no_wrap=True)
        price_table.add_column("Price", style="yellow")
        price_table.add_column("Change", style="green")
        price_table.add_column("Volume", style="blue")
        price_table.add_column("Time", style="magenta")
        
        symbol = price_data.get('symbol', 'N/A')
        price = price_data.get('price', 0)
        change = price_data.get('change', 0)
        volume = price_data.get('volume', 0)
        timestamp = price_data.get('timestamp', datetime.now().isoformat())
        
        change_color = "green" if change >= 0 else "red"
        change_text = f"[{change_color}]{change:+.2f}[/{change_color}]"
        
        price_table.add_row(
            symbol,
            f"${price:.2f}",
            change_text,
            f"{volume:,.0f}",
            timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else timestamp
        )
        
        layout.split_row(
            Layout(Panel(price_table, border_style="green"))
        )
        
        return layout
    
    def create_broker_view(self, data: Dict) -> Layout:
        """Create broker view layout"""
        layout = Layout()
        
        if not data or 'data' not in data:
            layout.split_row(
                Layout(Panel("[yellow]Waiting for broker data...[/yellow]", title="Status"))
            )
            return layout
        
        broker_data = data['data']
        
        # Account info table
        account_table = Table(title="🏦 Account Information", show_header=True, header_style="bold blue")
        account_table.add_column("Metric", style="cyan")
        account_table.add_column("Value", style="yellow")
        
        if 'balance' in broker_data:
            account_table.add_row("💰 Balance", f"${broker_data['balance']:.2f}")
        if 'equity' in broker_data:
            account_table.add_row("📈 Equity", f"${broker_data['equity']:.2f}")
        if 'margin' in broker_data:
            account_table.add_row("🎯 Margin", f"${broker_data['margin']:.2f}")
        if 'free_margin' in broker_data:
            account_table.add_row("🆓 Free Margin", f"${broker_data['free_margin']:.2f}")
        
        # Positions table
        positions_table = Table(title="📊 Open Positions", show_header=True, header_style="bold green")
        positions_table.add_column("Symbol", style="cyan")
        positions_table.add_column("Side", style="yellow")
        positions_table.add_column("Size", style="blue")
        positions_table.add_column("Entry", style="green")
        positions_table.add_column("Current", style="magenta")
        positions_table.add_column("PnL", style="red")
        
        if 'positions' in broker_data:
            for position in broker_data['positions']:
                side_color = "green" if position.get('side') == 'BUY' else "red"
                pnl = position.get('pnl', 0)
                pnl_color = "green" if pnl >= 0 else "red"
                
                positions_table.add_row(
                    position.get('symbol', 'N/A'),
                    f"[{side_color}]{position.get('side', 'N/A')}[/{side_color}]",
                    f"{position.get('size', 0):.4f}",
                    f"${position.get('entry_price', 0):.2f}",
                    f"${position.get('current_price', 0):.2f}",
                    f"[{pnl_color}]{pnl:+.2f}[/{pnl_color}]"
                )
        
        layout.split_row(
            Layout(Panel(account_table, border_style="blue")),
            Layout(Panel(positions_table, border_style="green"))
        )
        
        return layout
    
    def create_logs_view(self, data: Dict) -> Layout:
        """Create logs view layout"""
        layout = Layout()
        
        if not data or 'data' not in data:
            layout.split_row(
                Layout(Panel("[yellow]Waiting for log data...[/yellow]", title="Status"))
            )
            return layout
        
        logs_data = data['data']
        
        # Create logs table
        logs_table = Table(title="📜 Trading System Logs", show_header=True, header_style="bold red")
        logs_table.add_column("Time", style="cyan", no_wrap=True)
        logs_table.add_column("Type", style="yellow")
        logs_table.add_column("Level", style="blue")
        logs_table.add_column("Message", style="white")
        
        # Handle both single log entry and list of logs
        if isinstance(logs_data, list):
            log_entries = logs_data[-20:]  # Show last 20 entries
        else:
            log_entries = [logs_data]
        
        for log_entry in log_entries:
            timestamp = log_entry.get('timestamp', datetime.now().isoformat())
            log_type = log_entry.get('type', 'SYSTEM')
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')
            
            # Color coding based on level
            level_color = {
                'INFO': 'blue',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'SUCCESS': 'green'
            }.get(level, 'white')
            
            logs_table.add_row(
                timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else timestamp,
                log_type,
                f"[{level_color}]{level}[/{level_color}]",
                message
            )
        
        layout.split_row(
            Layout(Panel(logs_table, border_style="red"))
        )
        
        return layout
    
    def create_main_layout(self) -> Layout:
        """Create main layout based on channel"""
        layout = Layout()
        
        if self.latest_data:
            if self.channel == 'analysis':
                content = self.create_analysis_view(self.latest_data)
            elif self.channel == 'liveprice':
                content = self.create_liveprice_view(self.latest_data)
            elif self.channel == 'broker':
                content = self.create_broker_view(self.latest_data)
            elif self.channel == 'logs':
                content = self.create_logs_view(self.latest_data)
            else:
                content = Layout(Panel("[red]Unknown channel[/red]"))
        else:
            content = Layout(Panel("[yellow]Waiting for data...[/yellow]"))
        
        layout.split_column(
            Layout(self.create_header(), size=4),
            content
        )
        
        return layout
    
    async def run(self):
        """Run the viewer with auto-reconnect"""
        self.console.print(f"[bold green]Starting {self.channel} viewer...[/bold green]")
        self.console.print("[cyan]Press Ctrl+C to stop[/cyan]")
        
        if not await self.connect():
            self.console.print(f"[bold red]Failed to connect to WebSocket server[/bold red]")
            return
        
        # Start listening task
        listen_task = asyncio.create_task(self.listen())
        
        # Live display
        with Live(self.create_main_layout(), refresh_per_second=2, screen=True) as live:
            try:
                while self.running:
                    live.update(self.create_main_layout())
                    await asyncio.sleep(0.5)
            except KeyboardInterrupt:
                self.running = False
                self.console.print("\n[bold yellow]Shutting down viewer...[/bold yellow]")
            finally:
                listen_task.cancel()
                if self.websocket:
                    await self.websocket.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Trading System Web Viewer")
    parser.add_argument("--analysis", action="store_true", help="View AI trading analysis")
    parser.add_argument("--liveprice", action="store_true", help="View live price data")
    parser.add_argument("--broker", action="store_true", help="View broker dashboard")
    parser.add_argument("--logs", action="store_true", help="View trading logs")
    
    args = parser.parse_args()
    
    # Determine channel
    if args.analysis:
        channel = 'analysis'
    elif args.liveprice:
        channel = 'liveprice'
    elif args.broker:
        channel = 'broker'
    elif args.logs:
        channel = 'logs'
    else:
        print("Please specify a viewing mode:")
        print("  --analysis   View AI trading analysis")
        print("  --liveprice  View live price data")
        print("  --broker     View broker dashboard")
        print("  --logs       View trading logs")
        return
    
    # Create and run viewer
    viewer = TradingViewer(channel)
    
    try:
        asyncio.run(viewer.run())
    except KeyboardInterrupt:
        print("\nViewer stopped by user")

if __name__ == "__main__":
    main() 