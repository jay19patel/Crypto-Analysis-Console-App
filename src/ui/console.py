import os
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from colorama import Fore, Style, init

from src.config import get_settings

# Initialize colorama for Windows
init()

class ConsoleUI:
    """Console UI manager for consistent output styling"""
    
    def __init__(self):
        self.console = Console()
        self.settings = get_settings()
    
    def clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_banner(self):
        """Print application banner"""
        banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    {self.settings.BANNER_TITLE}                      ║
║                {self.settings.BANNER_SUBTITLE}             ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
    
    def create_progress_bar(self, description: str) -> Progress:
        """Create a rich progress bar"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
        )
    
    def print_live_prices(self, prices: Dict[str, Dict[str, float]]):
        """Print live cryptocurrency prices"""
        self.clear_screen()
        self.print_banner()
        
        # Create a table for prices
        table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        table.add_column("Symbol", style="white")
        table.add_column("Price (USD)", style="green")
        table.add_column("Last Update", style="dim")
        
        for symbol, data in sorted(prices.items()):
            symbol_clean = symbol.replace('USD', '')
            price = data["price"]
            timestamp = data["timestamp"].strftime('%I:%M:%S %p')
            table.add_row(
                f"🔸 {symbol_clean}",
                f"${price:,.2f}",
                timestamp
            )
        
        self.console.print(table)
        print(f"\n{Style.DIM}Press Ctrl+C to stop{Style.RESET_ALL}")
    
    def print_analysis_results(self, data: Dict, symbol: str):
        """Print technical analysis results"""
        self.clear_screen()
        self.print_banner()
        
        # Create main info panel
        info = Text()
        info.append(f"\n📊 Analysis Results for {symbol}\n", style="bold cyan")
        info.append(f"Resolution: {data['resolution']} | History: {data['days']} days\n", style="dim")
        info.append(f"Last Update: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n", style="dim")
        
        self.console.print(Panel(info, box=box.ROUNDED))
        
        # Create indicators table
        indicators_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        indicators_table.add_column("Indicator", style="white", width=18)
        indicators_table.add_column("Value", style="yellow", width=15)
        indicators_table.add_column("Signal", style="bold", width=25)
        indicators_table.add_column("Interpretation", style="cyan", width=20)
        
        # Add indicators data
        for indicator in data['indicators']:
            indicators_table.add_row(
                indicator['name'],
                indicator['value'],
                indicator['signal'],
                indicator['interpretation']
            )
        
        self.console.print(indicators_table)
        
        # Create strategies table
        strategies_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED)
        strategies_table.add_column("Strategy", style="white", width=20)
        strategies_table.add_column("Signal", style="yellow", width=15)
        strategies_table.add_column("Strength", style="bold", width=10)
        strategies_table.add_column("Details", style="cyan", width=30)
        
        # Add strategies data
        for strategy in data['strategies']:
            strategies_table.add_row(
                strategy['name'],
                strategy['signal'],
                f"{strategy['strength']}%",
                strategy['interpretation']
            )
        
        self.console.print("\n")
        self.console.print(strategies_table)
    
        # Display consensus signal if available
        if 'consensus' in data:
            consensus = data['consensus']
            consensus_panel = Text()
            consensus_panel.append(f"\n🎯 Consensus Signal: {consensus['signal']}\n", style="bold yellow")
            consensus_panel.append(f"Confidence: {consensus['confidence']} | Strength: {consensus['strength']:.1f}%\n", style="cyan")
            consensus_panel.append(f"{consensus['interpretation']}\n", style="white")
            
            self.console.print(Panel(consensus_panel, title="Strategy Consensus", box=box.ROUNDED))
        
        # Display AI Analysis if available - ABOVE Strategy Consensus
        if 'ai_analysis' in data and data['ai_analysis']:
            ai_data = data['ai_analysis']
            
            # Create comprehensive AI analysis table with ALL fields
            ai_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED, title="🤖 AI Market Analysis")
            ai_table.add_column("Field", style="white", width=25)
            ai_table.add_column("Analysis", style="cyan", width=60)
            
            # Add ALL AI analysis fields
            ai_table.add_row("Summary", ai_data.get("summary", "N/A"))
            ai_table.add_row("Current Trend", ai_data.get("current_trend", "N/A"))
            ai_table.add_row("Candlestick Patterns", ai_data.get("candlestick_patterns", "N/A"))
            ai_table.add_row("Strength", ai_data.get("strength", "N/A"))
            ai_table.add_row("Recommendation", ai_data.get("recommendation", "N/A"))
            ai_table.add_row("Reason", ai_data.get("reason", "N/A"))
            ai_table.add_row("Price Movement", ai_data.get("price_movement", "N/A"))
            ai_table.add_row("Momentum Forecast", ai_data.get("momentum_forecast", "N/A"))
            ai_table.add_row("Action Type", ai_data.get("action_type", "N/A"))
            ai_table.add_row("Action Strength", f"{ai_data.get('action_strength', 0)}%")
            
            # Entry/Exit levels
            if ai_data.get("entry_price"):
                ai_table.add_row("Entry Price", f"${ai_data['entry_price']:.2f}")
            else:
                ai_table.add_row("Entry Price", "N/A")
                
            if ai_data.get("stoploss"):
                ai_table.add_row("Stop Loss", f"${ai_data['stoploss']:.2f}")
            else:
                ai_table.add_row("Stop Loss", "N/A")
                
            if ai_data.get("target"):
                ai_table.add_row("Target", f"${ai_data['target']:.2f}")
            else:
                ai_table.add_row("Target", "N/A")
            
            ai_table.add_row("Risk/Reward", ai_data.get("risk_to_reward", "N/A"))
            ai_table.add_row("Max Holding Period", ai_data.get("max_holding_period", "N/A"))
            
            if ai_data.get("reason_to_hold"):
                ai_table.add_row("Reason to Hold", ai_data.get("reason_to_hold", "N/A"))
            
            ai_table.add_row("Volatility Risk", ai_data.get("volatility_risk", "N/A"))
            ai_table.add_row("Unusual Behavior", ai_data.get("unusual_behavior", "N/A"))
            ai_table.add_row("Overbought/Oversold", ai_data.get("overbought_oversold_alert", "N/A"))
            ai_table.add_row("Note", ai_data.get("note", "N/A"))
            
            self.console.print("\n")
            self.console.print(ai_table)
            self.console.print("\n")
    
    def print_error(self, message: str):
        """Print error message"""
        self.console.print(f"❌ Error: {message}", style="bold red")
    
    def print_success(self, message: str):
        """Print success message"""
        self.console.print(f"✅ {message}", style="bold green")
    
    def print_warning(self, message: str):
        """Print warning message"""
        self.console.print(f"⚠️ {message}", style="bold yellow")
    
    def print_info(self, message: str):
        """Print info message"""
        self.console.print(f"ℹ️ {message}", style="bold blue")
    
    def print_analysis_with_simple_broker_actions(self, data: Dict, symbol: str, broker_actions: Dict):
        """Print analysis results with simple broker action messages"""
        # First print normal analysis
        self.print_analysis_results(data, symbol)
        
        # Then add simple one-line broker actions if any
        if broker_actions.get('has_actions', False):
            self.console.print("\n")
            self.console.print("=" * 70, style="dim")
            
            # Simple one-line messages for actions
            if broker_actions.get('trade_executed'):
                self.console.print("🚀 BROKER: Trade executed - New position opened", style="bold green")
            
            if broker_actions.get('positions_closed'):
                for pos_info in broker_actions.get('positions_closed', []):
                    self.console.print(f"🔔 BROKER: Position closed - {pos_info}", style="bold yellow")
            
            if broker_actions.get('monitoring_active') and not broker_actions.get('trade_executed') and not broker_actions.get('positions_closed'):
                self.console.print("👁️ BROKER: Monitoring positions for stop loss/target hits", style="bold blue")
            
            self.console.print("=" * 70, style="dim")
            self.console.print("\n") 