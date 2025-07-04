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
    
    def __init__(self, ui_enabled: bool = True):
        self.console = Console()
        self.settings = get_settings()
        self.ui_enabled = ui_enabled
    
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
        if not self.ui_enabled:
            return
        
        self.clear_screen()
        self.print_banner()
        
        # Create main info panel
        info = Text()
        info.append(f"\n📊 Analysis Results for {symbol}\n", style="bold cyan")
        info.append(f"Resolution: {data['resolution']} | History: {data['days']} days\n", style="dim")
        info.append(f"Last Update: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}\n", style="dim")
        
        # Add live price status
        if data.get('live_price_active'):
            info.append(f"🔴 Live Price: ${data.get('current_price', 'N/A'):.2f} (Real-time)\n", style="bold green")
        elif data.get('current_price'):
            info.append(f"📈 Current Price: ${data.get('current_price', 'N/A'):.2f} (Historical)\n", style="yellow")
        
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
        
        # Display Enhanced AI Analysis if available
        if 'ai_analysis' in data and data['ai_analysis']:
            ai_data = data['ai_analysis']
            
            # === MAIN AI SIGNALS TABLE ===
            main_ai_table = Table(show_header=True, header_style="bold magenta", box=box.ROUNDED, title="🤖 AI Trading Signals")
            main_ai_table.add_column("Signal", style="white", width=20)
            main_ai_table.add_column("Value", style="cyan", width=25)
            main_ai_table.add_column("Details", style="yellow", width=40)
            
            # Core trading signals
            main_ai_table.add_row("Recommendation", ai_data.get("recommendation", "N/A"), ai_data.get("reason", "N/A"))
            main_ai_table.add_row("Action Type", ai_data.get("action_type", "N/A"), f"Strength: {ai_data.get('action_strength', 0)}%")
            main_ai_table.add_row("Current Trend", ai_data.get("current_trend", "N/A"), f"Strength: {ai_data.get('trend_strength', 'N/A')}")
            main_ai_table.add_row("Signal Quality", ai_data.get("signal_quality", "N/A"), f"Confidence: {ai_data.get('confidence_level', 0)}%")
            main_ai_table.add_row("Market Regime", ai_data.get("market_regime", "N/A"), ai_data.get("market_structure", "N/A"))
            
            self.console.print("\n")
            self.console.print(main_ai_table)
            
            # === PRICE LEVELS TABLE ===
            levels_table = Table(show_header=True, header_style="bold green", box=box.ROUNDED, title="📈 Key Price Levels & Targets")
            levels_table.add_column("Level Type", style="white", width=20)
            levels_table.add_column("Price", style="green", width=15)
            levels_table.add_column("Additional Info", style="cyan", width=50)
            
            # Entry/Exit levels
            if ai_data.get("entry_price"):
                levels_table.add_row("Entry Price", f"${ai_data['entry_price']:.2f}", f"Method: {ai_data.get('stop_loss_method', 'Standard')}")
            
            if ai_data.get("stoploss"):
                levels_table.add_row("Stop Loss", f"${ai_data['stoploss']:.2f}", f"Risk Level: {ai_data.get('risk_level', 'Medium')}")
            
            # Multiple take profit targets
            if ai_data.get("take_profit_1"):
                levels_table.add_row("Take Profit 1", f"${ai_data['take_profit_1']:.2f}", f"R:R {ai_data.get('risk_to_reward', 'N/A')}")
            if ai_data.get("take_profit_2"):
                levels_table.add_row("Take Profit 2", f"${ai_data['take_profit_2']:.2f}", "Extended target")
            if ai_data.get("take_profit_3"):
                levels_table.add_row("Take Profit 3", f"${ai_data['take_profit_3']:.2f}", "Maximum extension")
            
            # Support/Resistance levels
            if ai_data.get("support_level"):
                levels_table.add_row("Support Level", f"${ai_data['support_level']:.2f}", "Key support zone")
            if ai_data.get("resistance_level"):
                levels_table.add_row("Resistance Level", f"${ai_data['resistance_level']:.2f}", "Key resistance zone")
            
            self.console.print(levels_table)
            
            # === FIBONACCI ANALYSIS TABLE ===
            if any(ai_data.get(f"fibonacci_{level}") for level in ["23_6", "38_2", "50_0", "61_8", "78_6"]):
                fib_table = Table(show_header=True, header_style="bold yellow", box=box.ROUNDED, title="🌟 Fibonacci Analysis")
                fib_table.add_column("Fibonacci Level", style="white", width=20)
                fib_table.add_column("Price", style="yellow", width=15)
                fib_table.add_column("Extension Targets", style="cyan", width=15)
                fib_table.add_column("Swing Points", style="magenta", width=15)
                
                # Retracement levels
                if ai_data.get("fibonacci_23_6"):
                    fib_table.add_row("23.6%", f"${ai_data['fibonacci_23_6']:.2f}", 
                                    f"${ai_data.get('fibonacci_extension_127', 0):.2f}" if ai_data.get('fibonacci_extension_127') else "N/A",
                                    f"High: ${ai_data.get('swing_high', 0):.2f}" if ai_data.get('swing_high') else "N/A")
                if ai_data.get("fibonacci_38_2"):
                    fib_table.add_row("38.2%", f"${ai_data['fibonacci_38_2']:.2f}", 
                                    f"${ai_data.get('fibonacci_extension_161', 0):.2f}" if ai_data.get('fibonacci_extension_161') else "N/A",
                                    f"Low: ${ai_data.get('swing_low', 0):.2f}" if ai_data.get('swing_low') else "N/A")
                if ai_data.get("fibonacci_50_0"):
                    fib_table.add_row("50.0%", f"${ai_data['fibonacci_50_0']:.2f}", 
                                    f"${ai_data.get('fibonacci_extension_261', 0):.2f}" if ai_data.get('fibonacci_extension_261') else "N/A",
                                    ai_data.get("fibonacci_confluence", "N/A")[:15])
                if ai_data.get("fibonacci_61_8"):
                    fib_table.add_row("61.8%", f"${ai_data['fibonacci_61_8']:.2f}", "Golden Ratio", "Key level")
                if ai_data.get("fibonacci_78_6"):
                    fib_table.add_row("78.6%", f"${ai_data['fibonacci_78_6']:.2f}", "Deep retracement", "Strong support")
                
                self.console.print(fib_table)
            
            # === MARKET ANALYSIS TABLE ===
            market_table = Table(show_header=True, header_style="bold blue", box=box.ROUNDED, title="📊 Market Structure & Patterns")
            market_table.add_column("Analysis Type", style="white", width=25)
            market_table.add_column("Current Status", style="blue", width=20)
            market_table.add_column("Details", style="cyan", width=40)
            
            # Pattern analysis
            market_table.add_row("Candlestick Patterns", ai_data.get("candlestick_patterns", "N/A"), 
                               f"Reliability: {ai_data.get('pattern_reliability', 'N/A')}")
            market_table.add_row("Reversal Patterns", ai_data.get("reversal_patterns", "N/A"), 
                               ai_data.get("pattern_context", "N/A"))
            market_table.add_row("Continuation Patterns", ai_data.get("continuation_patterns", "N/A"), 
                               ai_data.get("consolidation_pattern", "N/A"))
            
            # Breakout analysis
            market_table.add_row("Breakout Direction", ai_data.get("breakout_direction", "N/A"), 
                               f"Probability: {ai_data.get('breakout_probability', 0)}%")
            market_table.add_row("False Breakout Risk", ai_data.get("false_breakout_risk", "N/A"), 
                               f"Trend Continuation: {ai_data.get('trend_continuation_probability', 0)}%")
            
            # Volume analysis
            market_table.add_row("Volume Trend", ai_data.get("volume_trend", "N/A"), 
                               f"Confirmation: {ai_data.get('volume_confirmation', 'N/A')}")
            market_table.add_row("Smart Money Activity", ai_data.get("smart_money_activity", "N/A"), 
                               ai_data.get("institutional_behavior", "N/A"))
            
            self.console.print(market_table)
            
            # === INDICATOR CONFLUENCE TABLE ===
            confluence_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED, title="🎯 Indicator Confluence")
            confluence_table.add_column("Indicator Group", style="white", width=25)
            confluence_table.add_column("Signal", style="cyan", width=15)
            confluence_table.add_column("Analysis", style="yellow", width=45)
            
            confluence_table.add_row("Momentum Indicators", ai_data.get("momentum_confluence", "N/A"), 
                                   ai_data.get("momentum_forecast", "N/A"))
            confluence_table.add_row("Trend Indicators", ai_data.get("trend_confluence", "N/A"), 
                                   f"Price Movement: {ai_data.get('price_movement', 'N/A')}")
            confluence_table.add_row("Mean Reversion", ai_data.get("mean_reversion_signal", "N/A"), 
                                   ai_data.get("overbought_oversold_alert", "N/A"))
            confluence_table.add_row("Volatility Analysis", "Normal" if "Normal" in ai_data.get("volatility_analysis", "") else "Active", 
                                   ai_data.get("volatility_analysis", "N/A"))
            confluence_table.add_row("Overall Strength", f"{ai_data.get('indicator_strength', 0)}%", 
                                   ai_data.get("unusual_behavior", "N/A"))
            
            self.console.print(confluence_table)
            
            # === SENTIMENT & RISK TABLE ===
            sentiment_table = Table(show_header=True, header_style="bold red", box=box.ROUNDED, title="🧠 Market Sentiment & Risk Management")
            sentiment_table.add_column("Factor", style="white", width=25)
            sentiment_table.add_column("Status", style="red", width=20)
            sentiment_table.add_column("Recommendations", style="cyan", width=40)
            
            sentiment_table.add_row("Fear/Greed Index", ai_data.get("fear_greed_indicator", "N/A"), 
                                  ai_data.get("market_psychology", "N/A"))
            sentiment_table.add_row("Retail Sentiment", ai_data.get("retail_sentiment", "N/A"), 
                                  ai_data.get("sentiment_extremes", "N/A"))
            sentiment_table.add_row("Position Size", ai_data.get("position_size_recommendation", "N/A"), 
                                  f"Max Drawdown: {ai_data.get('max_drawdown_risk', 'N/A')}")
            sentiment_table.add_row("Time Horizon", ai_data.get("max_holding_period", "N/A"), 
                                  ai_data.get("time_horizon_detail", "N/A"))
            sentiment_table.add_row("Execution Notes", ai_data.get("execution_notes", "N/A"), 
                                  ai_data.get("key_levels_to_watch", "N/A"))
            
            if ai_data.get("reason_to_hold"):
                sentiment_table.add_row("Hold Reason", "Wait Signal", ai_data.get("reason_to_hold", "N/A"))
            
            self.console.print(sentiment_table)
            
            # === CATALYST EVENTS ===
            if ai_data.get("catalyst_events") and ai_data.get("catalyst_events") != "No major catalysts identified":
                catalyst_panel = Text()
                catalyst_panel.append(f"\n🔔 Market Catalysts: {ai_data.get('catalyst_events', 'N/A')}\n", style="bold orange")
                self.console.print(Panel(catalyst_panel, title="Important Events", box=box.ROUNDED))
            
            # === AI SUMMARY ===
            summary_panel = Text()
            summary_panel.append(f"\n📝 AI Summary: {ai_data.get('summary', 'N/A')}\n", style="bold white")
            summary_panel.append(f"💡 Note: {ai_data.get('note', 'N/A')}\n", style="italic cyan")
            self.console.print(Panel(summary_panel, title="AI Analysis Summary", box=box.ROUNDED))
            self.console.print("\n")
    
    def print_error(self, message: str):
        """Print error message"""
        if self.ui_enabled:
            self.console.print(f"❌ Error: {message}", style="bold red")
    
    def print_success(self, message: str):
        """Print success message"""
        if self.ui_enabled:
            self.console.print(f"✅ {message}", style="bold green")
    
    def print_warning(self, message: str):
        """Print warning message"""
        if self.ui_enabled:
            self.console.print(f"⚠️ {message}", style="bold yellow")
    
    def print_info(self, message: str):
        """Print info message"""
        if self.ui_enabled:
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