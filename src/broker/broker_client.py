"""
Main Broker Client for trading system
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from src.broker.account_manager import AccountManager
from src.broker.position_manager import PositionManager
from src.broker.trade_executor import TradeExecutor
from src.config import get_settings
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
import time
import logging

logger = logging.getLogger(__name__)

class BrokerClient:
    """Main broker client integrating all trading components"""
    
    def __init__(self, websocket_server=None):
        """Initialize broker client"""
        self.logger = logging.getLogger(__name__)
        self.console = Console()
        self.settings = get_settings()
        self.websocket_server = websocket_server
        
        # Initialize components in correct order
        self.account_manager = AccountManager(websocket_server)
        self.position_manager = PositionManager(self, websocket_server)
        self.trade_executor = TradeExecutor(websocket_server, self.account_manager, self.position_manager)
        
        self.is_initialized = False
        self.last_updated = None
    
    def initialize(self) -> bool:
        """Initialize all broker components"""
        try:
            # Initialize account manager
            if not self.account_manager.connect():
                self.logger.error("Failed to connect account manager")
                return False
            
            if not self.account_manager.initialize_account():
                self.logger.error("Failed to initialize account manager")
                return False
            
            # Initialize position manager - connect and load positions
            if not self.position_manager.connect():
                self.logger.error("Failed to connect position manager")
                return False
            
            if not self.position_manager.load_positions():
                self.logger.error("Failed to load positions")
                return False
            
            # Set algorithm status to running
            self.account_manager.start_algo()
            
            self.is_initialized = True
            self.logger.info("Broker system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing broker system: {e}")
            return False
    
    def process_analysis_signal(
        self,
        symbol: str,
        analysis_results: Dict[str, Any],
        current_price: float
    ) -> bool:
        """Process analysis results and execute trades if conditions are met"""
        
        if not self.is_initialized:
            return False
        
        try:
            # First check AI Market Analysis for Action Type
            ai_analysis = analysis_results.get('ai_analysis')
            if ai_analysis and isinstance(ai_analysis, dict):
                action_type = ai_analysis.get('action_type', '').upper()
                action_strength = ai_analysis.get('action_strength', 0)
                
                if action_type in ['BUY', 'SELL'] and action_strength > 0:
                    self.logger.info(f"🤖 AI Analysis Signal: {action_type} | Strength: {action_strength}%")
                    
                    # Use actual MongoDB _id from analysis_results
                    analysis_id = str(analysis_results.get('_id', ''))
                    
                    return self.trade_executor.process_signal(
                        symbol=symbol,
                        signal=action_type,
                        confidence=action_strength,
                        current_price=current_price,
                        strategy_name="AI Market Analysis",
                        analysis_data=analysis_results,
                        analysis_id=analysis_id
                    )
            
            # Fallback to consensus signal if AI analysis not available
            consensus = analysis_results.get('consensus', {})
            signal = consensus.get('signal', 'NEUTRAL')
            confidence = consensus.get('strength', 0)
            
            # Get strategy that contributed to the signal
            strategies = analysis_results.get('strategies', [])
            contributing_strategy = "Consensus"
            
            for strategy in strategies:
                if strategy.get('signal', '').upper() == signal:
                    contributing_strategy = strategy.get('name', 'Unknown')
                    break
            
            # Process the signal
            if signal in ['BUY', 'SELL']:
                self.logger.info(f"📊 Consensus Signal: {signal} | Confidence: {confidence}%")
                
                # Use actual MongoDB _id from analysis_results
                analysis_id = str(analysis_results.get('_id', ''))
                
                return self.trade_executor.process_signal(
                    symbol=symbol,
                    signal=signal,
                    confidence=confidence,
                    current_price=current_price,
                    strategy_name=contributing_strategy,
                    analysis_data=analysis_results,
                    analysis_id=analysis_id
                )
            
            self.logger.info(f"⚪ No trading signal: {signal} (Strength: {confidence}%)")
            return False
            
        except Exception as e:
            self.logger.error(f"Error processing analysis signal: {e}")
            return False
    
    def monitor_positions(self, prices: Dict[str, Dict[str, float]]) -> None:
        """Monitor open positions and check for updates
        
        Args:
            prices: Dictionary of current prices with additional data
        """
        try:
            for position in self.position_manager.positions:
                if position.status == "OPEN":
                    # Get current price data
                    price_data = prices.get(position.symbol)
                    if not price_data:
                        continue
                    
                    current_price = price_data["price"]
                    mark_price = price_data.get("mark_price", current_price)
                    
                    # Calculate position metrics
                    pnl = position.calculate_pnl(mark_price)
                    margin_used = position.calculate_margin_used(mark_price)
                    liquidation_price = position.calculate_liquidation_price()
                    
                    # Check position status
                    if margin_used >= self.settings.BROKER_MARGIN_CALL_THRESHOLD:
                        self.log_message(
                            f"⚠️ MARGIN CALL WARNING - {position.symbol}: Margin used {margin_used*100:.1f}% | " +
                            f"Current: ${current_price:.2f} | Liquidation: ${liquidation_price:.2f}",
                            "warning"
                        )
                    
                    if margin_used >= self.settings.BROKER_LIQUIDATION_THRESHOLD:
                        self.log_message(
                            f"🚨 LIQUIDATION WARNING - {position.symbol}: Margin used {margin_used*100:.1f}% | " +
                            f"Current: ${current_price:.2f} | Liquidation: ${liquidation_price:.2f}",
                            "error"
                        )
                        
                        # Auto close position if too close to liquidation
                        if margin_used >= 0.98:  # 98% margin used
                            self.trade_executor.close_position(position, "LIQUIDATION_PROTECTION")
                    
                    # Check stop loss and take profit
                    if position.type == "LONG":
                        if current_price <= position.stop_loss:
                            self.trade_executor.close_position(position, "STOP_LOSS")
                        elif current_price >= position.target_price:
                            self.trade_executor.close_position(position, "TAKE_PROFIT")
                    else:  # SHORT
                        if current_price >= position.stop_loss:
                            self.trade_executor.close_position(position, "STOP_LOSS")
                        elif current_price <= position.target_price:
                            self.trade_executor.close_position(position, "TAKE_PROFIT")
                    
                    # Send position update to WebSocket
                    if self.websocket_server:
                        self.send_message(
                            MessageFormatter.format_message(
                                MessageType.POSITIONS,
                                {
                                    "position_id": position.id,
                                    "symbol": position.symbol,
                                    "type": position.type,
                                    "entry_price": position.entry_price,
                                    "current_price": current_price,
                                    "pnl": pnl,
                                    "margin_used": margin_used,
                                    "liquidation_price": liquidation_price,
                                    "stop_loss": position.stop_loss,
                                    "target_price": position.target_price,
                                    "timestamp": datetime.now().isoformat()
                                },
                                "broker_client"
                            )
                        )
                    
                    # Log position status if debug enabled
                    if self.settings.BROKER_DEBUG_POSITION_MONITORING:
                        self.log_message(
                            f"Position Update - {position.symbol} ({position.type}): " +
                            f"Entry: ${position.entry_price:.2f} | Current: ${current_price:.2f} | " +
                            f"P&L: ${pnl:.2f} ({(pnl/position.entry_price)*100:.1f}%) | " +
                            f"Margin Used: {margin_used*100:.1f}%",
                            "info"
                        )
            
        except Exception as e:
            self.log_message(f"Error monitoring positions: {e}", "error")
    
    def display_broker_dashboard(self, show_last_updated: bool = False) -> None:
        """Display comprehensive broker dashboard"""
        
        if not self.is_initialized:
            self.logger.error("Broker system not initialized")
            return
        
        try:
            # Update last updated time
            self.last_updated = datetime.now()
            
            # Clear screen for clean display
            self.console.clear_screen()
            self.console.print_banner()
            
            # Display last updated time if requested
            if show_last_updated:
                self.console.print(f"🕒 Last Updated: {self.last_updated.strftime('%Y-%m-%d %I:%M:%S %p')}", style="dim")
                self.console.print()
            
            # Get trading summary
            summary = self.trade_executor.get_trading_summary()
            account = summary['account']
            positions = summary['positions']
            trading_status = summary['trading_status']
            
            # Create main dashboard
            self._display_account_summary(account, trading_status)
            self._display_positions_summary(positions)
            self._display_recent_trades(positions.get('recent_closed_positions', []))
            self._display_open_positions(positions.get('open_positions_list', []))
            
            # Display refresh info if this is auto-refresh mode
            if show_last_updated:
                next_refresh = self.last_updated + timedelta(seconds=self.settings.BROKER_UI_REFRESH_INTERVAL)
                self.console.print()
                self.console.print(f"🔄 Auto-refresh: Every {self.settings.BROKER_UI_REFRESH_INTERVAL} seconds | Next refresh: {next_refresh.strftime('%I:%M:%S %p')}", style="dim")
                self.console.print("Press Ctrl+C to stop", style="dim")
            
        except Exception as e:
            self.logger.error(f"Error displaying dashboard: {e}")
    
    def _display_account_summary(self, account: Dict[str, Any], trading_status: Dict[str, Any]) -> None:
        """Display account summary"""
        
        # Account details table
        account_table = Table(title="💰 Account Summary", show_header=True, header_style="bold magenta")
        account_table.add_column("Metric", style="cyan", no_wrap=True)
        account_table.add_column("Value", style="green")
        
        # Add account data
        account_table.add_row("Account Name", account.get('name', 'N/A'))
        account_table.add_row("Current Balance", f"${account.get('current_balance', 0):.2f}")
        account_table.add_row("Initial Balance", f"${account.get('initial_balance', 0):.2f}")
        account_table.add_row("Brokerage Charges", f"${account.get('brokerage_charges', 0):.2f}")
        
        # Calculate profit/loss
        pnl = account.get('total_profit_loss', 0)
        pnl_color = "green" if pnl >= 0 else "red"
        pnl_symbol = "+" if pnl >= 0 else ""
        account_table.add_row("Total P&L", f"[{pnl_color}]{pnl_symbol}${pnl:.2f}[/{pnl_color}]")
        
        # Growth percentage
        growth = account.get('growth_percentage', 0)
        growth_color = "green" if growth >= 0 else "red"
        growth_symbol = "+" if growth >= 0 else ""
        account_table.add_row("Account Growth", f"[{growth_color}]{growth_symbol}{growth:.2f}%[/{growth_color}]")
        
        # Trading statistics
        account_table.add_row("Total Trades", str(account.get('total_trades', 0)))
        account_table.add_row("Profitable Trades", str(account.get('profitable_trades', 0)))
        account_table.add_row("Win Rate", f"{account.get('win_rate', 0):.1f}%")
        
        # Daily trading status
        trades_remaining = trading_status.get('trades_remaining', 0)
        daily_count = account.get('daily_trades_count', 0)
        daily_limit = account.get('daily_trades_limit', 5)
        
        status_color = "green" if trades_remaining > 0 else "red"
        account_table.add_row("Daily Trades", f"[{status_color}]{daily_count}/{daily_limit}[/{status_color}]")
        account_table.add_row("Trades Remaining", f"[{status_color}]{trades_remaining}[/{status_color}]")
        
        # Margin trading information
        max_leverage = account.get('max_leverage', 1)
        total_margin_used = account.get('total_margin_used', 0)
        current_balance = account.get('current_balance', 0)
        
        account_table.add_row("Max Leverage", f"[bright_magenta]{max_leverage:.0f}x[/bright_magenta]")
        account_table.add_row("Margin Used", f"${total_margin_used:.2f}")
        account_table.add_row("Available Funds", f"${current_balance:.2f}")
        
        # Algorithm status
        algo_status = account.get('algo_status', False)
        status_color = "green" if algo_status else "red"
        status_text = "🟢 RUNNING" if algo_status else "🔴 STOPPED"
        account_table.add_row("Algorithm Status", f"[{status_color}]{status_text}[/{status_color}]")
        
        self.console.print(account_table)
        self.console.print()
    
    def _display_positions_summary(self, positions: Dict[str, Any]) -> None:
        """Display positions summary"""
        
        summary_table = Table(title="📊 Positions Overview", show_header=True, header_style="bold blue")
        summary_table.add_column("Category", style="cyan")
        summary_table.add_column("Count", style="yellow")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Positions", str(positions.get('total_positions', 0)), "-")
        summary_table.add_row("Open Positions", str(positions.get('open_positions', 0)), f"${positions.get('total_open_value', 0):.2f}")
        summary_table.add_row("Closed Positions", str(positions.get('closed_positions', 0)), "-")
        
        # Unrealized P&L
        unrealized_pnl = positions.get('total_unrealized_pnl', 0)
        pnl_color = "green" if unrealized_pnl >= 0 else "red"
        pnl_symbol = "+" if unrealized_pnl >= 0 else ""
        summary_table.add_row("Unrealized P&L", "-", f"[{pnl_color}]{pnl_symbol}${unrealized_pnl:.2f}[/{pnl_color}]")
        
        self.console.print(summary_table)
        self.console.print()
    
    def _display_recent_trades(self, recent_trades: List[Any]) -> None:
        """Display recent closed trades"""
        
        if not recent_trades:
            self.console.print(Panel("📈 No recent trades found", style="yellow"))
            self.console.print()
            return
        
        trades_table = Table(title="📈 Recent Trades (Top 5)", show_header=True, header_style="bold green")
        trades_table.add_column("Symbol", style="cyan")
        trades_table.add_column("Type", style="magenta")
        trades_table.add_column("Entry", style="blue")
        trades_table.add_column("Exit", style="blue")
        trades_table.add_column("P&L", style="white")
        trades_table.add_column("Duration", style="yellow")
        trades_table.add_column("Strategy", style="dim")
        
        for trade in recent_trades[:5]:
            # P&L formatting
            pnl = trade.pnl
            pnl_color = "green" if pnl >= 0 else "red"
            pnl_symbol = "+" if pnl >= 0 else ""
            pnl_str = f"[{pnl_color}]{pnl_symbol}${pnl:.2f}[/{pnl_color}]"
            
            trades_table.add_row(
                trade.symbol,
                trade.position_type.value,
                f"${trade.entry_price:.2f}",
                f"${trade.exit_price:.2f}" if trade.exit_price else "N/A",
                pnl_str,
                trade.holding_time or "N/A",
                trade.strategy_name[:15] if trade.strategy_name else "Manual"
            )
        
        self.console.print(trades_table)
        self.console.print()
    
    def _display_open_positions(self, open_positions: List[Any]) -> None:
        """Display open positions with margin trading information"""
        
        if not open_positions:
            self.console.print(Panel("🔄 No open positions", style="blue"))
            self.console.print()
            return
        
        positions_table = Table(title="🔄 Open Positions", show_header=True, header_style="bold yellow")
        positions_table.add_column("Symbol", style="cyan")
        positions_table.add_column("Type", style="magenta")
        positions_table.add_column("Entry", style="blue")
        positions_table.add_column("Leverage", style="bright_magenta")
        positions_table.add_column("Quantity", style="white")
        positions_table.add_column("Position Value", style="green")
        positions_table.add_column("Margin Used", style="yellow")
        positions_table.add_column("Trading Fee", style="dim")
        positions_table.add_column("Current P&L", style="white")
        positions_table.add_column("Margin Risk", style="red")
        positions_table.add_column("Stop Loss", style="red")
        positions_table.add_column("Target", style="green")
        positions_table.add_column("Analysis ID", style="dim")
        positions_table.add_column("Duration", style="yellow")
        
        for position in open_positions:
            try:
                # P&L formatting
                pnl = position.pnl
                pnl_color = "green" if pnl >= 0 else "red"
                pnl_symbol = "+" if pnl >= 0 else ""
                pnl_str = f"[{pnl_color}]{pnl_symbol}${pnl:.2f}[/{pnl_color}]"
                
                # Leverage display
                leverage_str = f"{position.leverage:.0f}x" if position.leverage > 1 else "1x"
                if position.leverage > 1:
                    leverage_str = f"[bright_magenta]{leverage_str}[/bright_magenta]"
                
                # Margin risk calculation and display
                margin_risk_str = "N/A"
                if position.leverage > 1 and position.margin_used > 0:
                    # Get current price to calculate margin usage
                    current_price = position.entry_price  # Fallback to entry price
                    # In real scenario, you would pass current prices here
                    margin_usage = position.calculate_margin_usage(current_price)
                    
                    if margin_usage >= 0.95:
                        margin_risk_str = f"[red]💀 {margin_usage*100:.1f}%[/red]"
                    elif margin_usage >= 0.8:
                        margin_risk_str = f"[yellow]⚠️  {margin_usage*100:.1f}%[/yellow]"
                    elif margin_usage > 0:
                        margin_risk_str = f"[orange]{margin_usage*100:.1f}%[/orange]"
                    else:
                        margin_risk_str = f"[green]✅ Safe[/green]"
                else:
                    margin_risk_str = "[green]No Risk[/green]"
                
                # Margin used display
                margin_used_str = f"${position.margin_used:.2f}" if position.margin_used > 0 else "N/A"
                
                # Trading fee display
                trading_fee_str = f"${position.trading_fee:.2f}" if position.trading_fee > 0 else "N/A"
                
                # Analysis ID display (MongoDB _id format)
                analysis_id_str = "Manual"
                if position.analysis_id and position.analysis_id.strip():
                    # Display shortened MongoDB _id (first 8 characters)
                    if len(position.analysis_id) >= 8:
                        analysis_id_str = position.analysis_id[:8] + "..."
                    else:
                        analysis_id_str = position.analysis_id
                
                # Safe holding time calculation
                try:
                    holding_time = position.calculate_holding_time()
                except:
                    holding_time = "N/A"
                
                positions_table.add_row(
                    position.symbol,
                    position.position_type.value,
                    f"${position.entry_price:.2f}",
                    leverage_str,
                    f"{position.quantity:.6f}",
                    f"${position.invested_amount:.2f}",
                    margin_used_str,
                    trading_fee_str,
                    pnl_str,
                    margin_risk_str,
                    f"${position.stop_loss:.2f}" if position.stop_loss else "N/A",
                    f"${position.target:.2f}" if position.target else "N/A",
                    analysis_id_str,
                    holding_time
                )
            except Exception as e:
                self.logger.error(f"Error displaying position: {e}")
                continue
        
        self.console.print(positions_table)
        self.console.print()
    
    def get_broker_status(self) -> Dict[str, Any]:
        """Get comprehensive broker status"""
        if not self.is_initialized:
            return {'error': 'Broker not initialized'}
        
        try:
            # Get trading summary
            summary = self.trade_executor.get_trading_summary()
            
            return {
                'is_initialized': self.is_initialized,
                'account': summary['account'],
                'positions': summary['positions'],
                'trading_status': summary['trading_status'],
                'last_updated': self.last_updated.isoformat() if self.last_updated else None
            }
            
        except Exception as e:
            return {'error': f'Error getting broker status: {e}'}
    
    def close_position_manually(self, position_id: str, current_price: float) -> bool:
        """Manually close a position"""
        return self.trade_executor.force_close_position(position_id, current_price, "Manual close")
    
    def display_broker_actions(self, trade_executed: bool, closed_positions: List[str]) -> None:
        """Display broker actions summary after analysis"""
        if not trade_executed and not closed_positions:
            return
        
        # Create actions summary
        actions_table = Table(title="🤖 Broker Actions", show_header=True, header_style="bold yellow")
        actions_table.add_column("Action", style="cyan")
        actions_table.add_column("Details", style="white")
        actions_table.add_column("Status", style="green")
        
        if trade_executed:
            actions_table.add_row("🚀 Trade Execution", "New position opened", "✅ Completed")
        
        for position_id in closed_positions:
            position = self.position_manager.get_position_by_id(position_id)
            if position:
                reason = "Target/SL Hit" if "Hit" in position.notes else "Auto Close"
                actions_table.add_row("🔔 Position Closed", f"{position.symbol} | {reason}", "✅ Completed")
        
        self.console.print(actions_table)
        self.console.print()
    
    def get_broker_actions_summary(self) -> Dict[str, Any]:
        """Get summary of recent broker actions"""
        try:
            summary = self.trade_executor.get_trading_summary()
            account = summary['account']
            positions = summary['positions']
            
            return {
                'last_action': 'No recent activity',
                'can_trade': account.get('daily_trades_count', 0) < account.get('daily_trades_limit', 5),
                'trades_today': account.get('daily_trades_count', 0),
                'open_positions': positions.get('open_positions', 0),
                'account_status': 'Active' if account.get('current_balance', 0) > 0 else 'Inactive'
            }
        except:
            return {}
    
    def disconnect(self) -> None:
        """Disconnect all components"""
        try:
            # Set algorithm status to stopped before disconnecting
            if self.account_manager and self.account_manager.account:
                self.account_manager.stop_algo()
            
            self.account_manager.disconnect()
            self.position_manager.disconnect()
            self.logger.info("Broker system disconnected")
        except Exception as e:
            self.logger.error(f"Error disconnecting broker: {e}")

    def log_info(self, message: str):
        """Log information message"""
        self.logger.info(message)

    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(message)

    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(message) 