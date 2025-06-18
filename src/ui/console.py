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

from ..config import get_settings

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