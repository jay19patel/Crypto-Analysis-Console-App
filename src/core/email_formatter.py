"""
Centralized Email Formatter Class
Manages all email templates and formatting for trading notifications
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.config import get_settings, get_trading_config


class EmailTemplate(Enum):
    """Essential email template types"""
    TRADE_EXECUTION = "trade_execution"
    POSITION_EXIT = "position_exit"
    RISK_ALERT = "risk_alert"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


@dataclass
class TradeExecutionData:
    """Data structure for trade execution emails"""
    symbol: str
    signal: str  # BUY/SELL
    price: float
    quantity: float
    leverage: float
    margin_used: float
    capital_remaining: float
    investment_amount: float
    leveraged_amount: float
    trade_id: str
    position_id: str
    strategy_name: str
    confidence: float
    trading_fee: float
    timestamp: datetime
    account_balance_before: float
    account_balance_after: float


@dataclass
class PositionExitData:
    """Data structure for position exit emails"""
    symbol: str
    position_type: str  # LONG/SHORT
    entry_price: float
    exit_price: float
    quantity: float
    leverage: float
    pnl: float
    pnl_percentage: float
    investment_amount: float
    leveraged_amount: float
    margin_used: float
    trading_fee: float
    exit_fee: float
    total_fees: float
    position_id: str
    trade_duration: str
    exit_reason: str
    account_balance_before: float
    account_balance_after: float
    account_growth: float
    account_growth_percentage: float
    total_portfolio_pnl: float
    win_rate: float
    timestamp: datetime


class EmailFormatter:
    """Centralized email formatter for all trading notifications"""
    
    def __init__(self):
        """Initialize email formatter"""
        self.settings = get_settings()
        self.trading_config = get_trading_config()
        self.logger = logging.getLogger("email_formatter")
        
        # Email styling constants
        self.base_styles = """
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                margin: 0; 
                padding: 20px; 
                line-height: 1.6; 
                background-color: #f5f5f5;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }
            .header { 
                color: white; 
                padding: 30px; 
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 28px;
                font-weight: 300;
            }
            .content { 
                padding: 30px; 
            }
            .section {
                margin-bottom: 25px;
                padding: 20px;
                background-color: #f8f9fa;
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }
            .section h3 {
                margin: 0 0 15px 0;
                color: #333;
                font-size: 18px;
                font-weight: 600;
            }
            .data-table { 
                width: 100%; 
                border-collapse: collapse; 
                background-color: white;
                border-radius: 6px;
                overflow: hidden;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            .data-table td { 
                padding: 12px 16px; 
                border-bottom: 1px solid #e9ecef;
                vertical-align: middle;
            }
            .data-table td:first-child {
                background-color: #f8f9fa;
                font-weight: 600;
                color: #495057;
                width: 40%;
            }
            .data-table td:last-child {
                font-family: 'Courier New', monospace;
                color: #212529;
            }
            .data-table tr:last-child td {
                border-bottom: none;
            }
            .footer { 
                background-color: #f8f9fa;
                padding: 20px 30px;
                border-top: 1px solid #dee2e6;
                text-align: center;
                color: #6c757d; 
                font-size: 14px; 
            }
            .profit { color: #28a745; font-weight: bold; }
            .loss { color: #dc3545; font-weight: bold; }
            .neutral { color: #6c757d; }
            .highlight { background-color: #fff3cd; padding: 5px 10px; border-radius: 4px; }
        """
        
        self.logger.info("EmailFormatter initialized successfully")
    
    def format_trade_execution_email(self, data: TradeExecutionData) -> tuple[str, str]:
        """Format trade execution email with detailed position information"""
        try:
            # Email subject
            subject = f"🚀 Trade Executed: {data.signal} {data.symbol} at ${data.price:.2f}"
            
            # Calculate additional metrics
            position_value = data.price * data.quantity
            margin_percentage = (data.margin_used / data.account_balance_before) * 100 if data.account_balance_before > 0 else 0
            leveraged_exposure = position_value * data.leverage
            
            # Determine color based on signal
            header_color = "#28a745" if data.signal == "BUY" else "#dc3545"
            
            # Build HTML content
            html_body = f"""
            <html>
            <head>
                <style>{self.base_styles}</style>
            </head>
            <body>
                <div class="container">
                    <div class="header" style="background: linear-gradient(135deg, {header_color} 0%, {header_color}dd 100%);">
                        <h1>Trade Executed Successfully</h1>
                        <p>{data.signal} {data.symbol} at ${data.price:.2f}</p>
                        <p>Strategy: {data.strategy_name} | Confidence: {data.confidence:.1f}%</p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h3>Trade Details</h3>
                            <table class="data-table">
                                <tr><td>Symbol</td><td>{data.symbol}</td></tr>
                                <tr><td>Signal</td><td><span class="highlight">{data.signal}</span></td></tr>
                                <tr><td>Execution Price</td><td>${data.price:.2f}</td></tr>
                                <tr><td>Quantity</td><td>{data.quantity:.6f}</td></tr>
                                <tr><td>Position Value</td><td>${position_value:,.2f}</td></tr>
                                <tr><td>Strategy</td><td>{data.strategy_name}</td></tr>
                                <tr><td>Confidence Level</td><td>{data.confidence:.1f}%</td></tr>
                                <tr><td>Trade ID</td><td>{data.trade_id}</td></tr>
                                <tr><td>Position ID</td><td>{data.position_id}</td></tr>
                            </table>
                        </div>
                        
                        <div class="section">
                            <h3>Leverage & Margin Details</h3>
                            <table class="data-table">
                                <tr><td>Leverage Used</td><td><span class="highlight">{data.leverage:.1f}x</span></td></tr>
                                <tr><td>Margin Required</td><td>${data.margin_used:,.2f}</td></tr>
                                <tr><td>Margin Percentage</td><td>{margin_percentage:.2f}% of account</td></tr>
                                <tr><td>Leveraged Exposure</td><td>${leveraged_exposure:,.2f}</td></tr>
                                <tr><td>Trading Fee</td><td>${data.trading_fee:.2f}</td></tr>
                                <tr><td>Total Cost</td><td>${data.margin_used + data.trading_fee:,.2f}</td></tr>
                            </table>
                        </div>
                        
                        <div class="section">
                            <h3>Account Impact</h3>
                            <table class="data-table">
                                <tr><td>Balance Before Trade</td><td>${data.account_balance_before:,.2f}</td></tr>
                                <tr><td>Balance After Trade</td><td>${data.account_balance_after:,.2f}</td></tr>
                                <tr><td>Capital Remaining</td><td>${data.capital_remaining:,.2f}</td></tr>
                                <tr><td>Investment Amount</td><td>${data.investment_amount:,.2f}</td></tr>
                                <tr><td>Available for Trading</td><td>${data.capital_remaining - data.margin_used:,.2f}</td></tr>
                            </table>
                        </div>
                        
                        <div class="section">
                            <h3>Risk Information</h3>
                            <table class="data-table">
                                <tr><td>Stop Loss</td><td>At {self.trading_config['stop_loss_pct']*100:.1f}% loss</td></tr>
                                <tr><td>Target Profit</td><td>At {self.trading_config['target_pct']*100:.1f}% gain</td></tr>
                                <tr><td>Max Risk</td><td>${data.margin_used * self.trading_config['stop_loss_pct']:,.2f}</td></tr>
                                <tr><td>Max Reward</td><td>${data.margin_used * self.trading_config['target_pct']:,.2f}</td></tr>
                                <tr><td>Risk/Reward Ratio</td><td>1:{self.trading_config['target_pct']/self.trading_config['stop_loss_pct']:.1f}</td></tr>
                            </table>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Executed:</strong> {data.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                        <p>This is an automated notification from your Professional Trading System.</p>
                        <p>🤖 Generated with Claude Code | Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return subject, html_body
            
        except Exception as e:
            self.logger.error(f"Error formatting trade execution email: {e}")
            return f"Trade Executed: {data.symbol}", f"<p>Error formatting email: {str(e)}</p>"
    
    def format_position_exit_email(self, data: PositionExitData) -> tuple[str, str]:
        """Format position exit email with comprehensive PnL and account details"""
        try:
            # Email subject with profit/loss indicator
            pnl_indicator = "📈 PROFIT" if data.pnl > 0 else "📉 LOSS"
            subject = f"{pnl_indicator}: {data.symbol} Position Closed | P&L: ${data.pnl:,.2f}"
            
            # Determine colors
            pnl_color = "#28a745" if data.pnl > 0 else "#dc3545"
            header_color = "#28a745" if data.pnl > 0 else "#dc3545"
            
            # Calculate additional metrics
            total_return = data.exit_price - data.entry_price if data.position_type == "LONG" else data.entry_price - data.exit_price
            roi_percentage = (data.pnl / data.margin_used * 100) if data.margin_used > 0 else 0
            
            html_body = f"""
            <html>
            <head>
                <style>{self.base_styles}</style>
            </head>
            <body>
                <div class="container">
                    <div class="header" style="background: linear-gradient(135deg, {header_color} 0%, {header_color}dd 100%);">
                        <h1>Position Closed: {data.symbol}</h1>
                        <p>{data.position_type} Position | P&L: <span style="font-size: 24px;">${data.pnl:,.2f}</span></p>
                        <p>Exit Reason: {data.exit_reason}</p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h3>Position Summary</h3>
                            <table class="data-table">
                                <tr><td>Symbol</td><td>{data.symbol}</td></tr>
                                <tr><td>Position Type</td><td><span class="highlight">{data.position_type}</span></td></tr>
                                <tr><td>Entry Price</td><td>${data.entry_price:.2f}</td></tr>
                                <tr><td>Exit Price</td><td>${data.exit_price:.2f}</td></tr>
                                <tr><td>Quantity</td><td>{data.quantity:.6f}</td></tr>
                                <tr><td>Leverage</td><td>{data.leverage:.1f}x</td></tr>
                                <tr><td>Position Duration</td><td>{data.trade_duration}</td></tr>
                                <tr><td>Position ID</td><td>{data.position_id}</td></tr>
                            </table>
                        </div>
                        
                        <div class="section">
                            <h3>Profit & Loss Analysis</h3>
                            <table class="data-table">
                                <tr><td>P&L Amount</td><td><span class="{'profit' if data.pnl > 0 else 'loss'}">${data.pnl:,.2f}</span></td></tr>
                                <tr><td>P&L Percentage</td><td><span class="{'profit' if data.pnl_percentage > 0 else 'loss'}">{data.pnl_percentage:.2f}%</span></td></tr>
                                <tr><td>ROI on Margin</td><td><span class="{'profit' if roi_percentage > 0 else 'loss'}">{roi_percentage:.2f}%</span></td></tr>
                                <tr><td>Price Movement</td><td>${total_return:.2f} per unit</td></tr>
                                <tr><td>Investment Amount</td><td>${data.investment_amount:,.2f}</td></tr>
                                <tr><td>Leveraged Amount</td><td>${data.leveraged_amount:,.2f}</td></tr>
                                <tr><td>Margin Used</td><td>${data.margin_used:,.2f}</td></tr>
                            </table>
                        </div>
                        
                        <div class="section">
                            <h3>Fees & Costs</h3>
                            <table class="data-table">
                                <tr><td>Entry Trading Fee</td><td>${data.trading_fee:.2f}</td></tr>
                                <tr><td>Exit Trading Fee</td><td>${data.exit_fee:.2f}</td></tr>
                                <tr><td>Total Fees</td><td>${data.total_fees:.2f}</td></tr>
                                <tr><td>Net P&L (After Fees)</td><td><span class="{'profit' if data.pnl > 0 else 'loss'}">${data.pnl:,.2f}</span></td></tr>
                            </table>
                        </div>
                        
                        <div class="section">
                            <h3>Account Impact</h3>
                            <table class="data-table">
                                <tr><td>Balance Before Exit</td><td>${data.account_balance_before:,.2f}</td></tr>
                                <tr><td>Balance After Exit</td><td>${data.account_balance_after:,.2f}</td></tr>
                                <tr><td>Account Growth</td><td><span class="{'profit' if data.account_growth > 0 else 'loss'}">${data.account_growth:,.2f}</span></td></tr>
                                <tr><td>Account Growth %</td><td><span class="{'profit' if data.account_growth_percentage > 0 else 'loss'}">{data.account_growth_percentage:.2f}%</span></td></tr>
                                <tr><td>Total Portfolio P&L</td><td><span class="{'profit' if data.total_portfolio_pnl > 0 else 'loss'}">${data.total_portfolio_pnl:,.2f}</span></td></tr>
                                <tr><td>Overall Win Rate</td><td>{data.win_rate:.1f}%</td></tr>
                            </table>
                        </div>
                        
                        <div class="section">
                            <h3>Performance Metrics</h3>
                            <table class="data-table">
                                <tr><td>Trade Outcome</td><td><span class="{'profit' if data.pnl > 0 else 'loss'}">{'PROFITABLE' if data.pnl > 0 else 'LOSS'}</span></td></tr>
                                <tr><td>Risk Reward Achieved</td><td>{abs(data.pnl_percentage / self.trading_config['stop_loss_pct'] / 100):.2f}:1</td></tr>
                                <tr><td>Capital Efficiency</td><td>{(abs(data.pnl) / data.margin_used * 100):.2f}%</td></tr>
                                <tr><td>Leverage Multiplier</td><td>{data.leverage:.1f}x effective</td></tr>
                            </table>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Position Closed:</strong> {data.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                        <p>This is an automated notification from your Professional Trading System.</p>
                        <p>🤖 Generated with Claude Code | Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return subject, html_body
            
        except Exception as e:
            self.logger.error(f"Error formatting position exit email: {e}")
            return f"Position Closed: {data.symbol}", f"<p>Error formatting email: {str(e)}</p>"
    
    def format_risk_alert_email(self, symbol: str, alert_type: str, current_price: float, 
                               risk_level: str, additional_data: Dict[str, Any] = None) -> tuple[str, str]:
        """Format risk alert email"""
        try:
            subject = f"🚨 Risk Alert: {symbol} - {alert_type}"
            
            additional_data = additional_data or {}
            
            html_body = f"""
            <html>
            <head>
                <style>{self.base_styles}</style>
            </head>
            <body>
                <div class="container">
                    <div class="header" style="background: linear-gradient(135deg, #dc3545 0%, #dc3545dd 100%);">
                        <h1>🚨 Risk Alert</h1>
                        <p>{symbol} - {alert_type}</p>
                        <p>Risk Level: <span class="highlight">{risk_level.upper()}</span></p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h3>Alert Details</h3>
                            <table class="data-table">
                                <tr><td>Symbol</td><td>{symbol}</td></tr>
                                <tr><td>Alert Type</td><td><span class="loss">{alert_type}</span></td></tr>
                                <tr><td>Current Price</td><td>${current_price:,.2f}</td></tr>
                                <tr><td>Risk Level</td><td><span class="loss">{risk_level.upper()}</span></td></tr>
                                <tr><td>Alert Time</td><td>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                            </table>
                        </div>
                        
                        {'<div class="section"><h3>Additional Information</h3><table class="data-table">' + 
                         ''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in additional_data.items()]) + 
                         '</table></div>' if additional_data else ''}
                        
                        <div class="section">
                            <h3>Recommended Actions</h3>
                            <ul>
                                <li>Review open positions immediately</li>
                                <li>Consider reducing position sizes</li>
                                <li>Check stop-loss orders</li>
                                <li>Monitor market conditions closely</li>
                                <li>Consider adding funds if margin call risk</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Alert Generated:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                        <p>This is an automated risk alert from your Professional Trading System.</p>
                        <p>🤖 Generated with Claude Code | Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return subject, html_body
            
        except Exception as e:
            self.logger.error(f"Error formatting risk alert email: {e}")
            return f"Risk Alert: {symbol}", f"<p>Error formatting email: {str(e)}</p>"
    
    def format_system_error_email(self, error_message: str, component: str,
                                 additional_data: Dict[str, Any] = None) -> tuple[str, str]:
        """Format system error email"""
        try:
            subject = f"❌ System Error: {component}"
            
            additional_data = additional_data or {}
            
            html_body = f"""
            <html>
            <head>
                <style>{self.base_styles}</style>
            </head>
            <body>
                <div class="container">
                    <div class="header" style="background: linear-gradient(135deg, #dc3545 0%, #dc3545dd 100%);">
                        <h1>❌ System Error</h1>
                        <p>Component: {component}</p>
                        <p>Critical System Alert</p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h3>Error Details</h3>
                            <table class="data-table">
                                <tr><td>Component</td><td><span class="loss">{component}</span></td></tr>
                                <tr><td>Error Message</td><td>{error_message}</td></tr>
                                <tr><td>Severity</td><td><span class="loss">CRITICAL</span></td></tr>
                                <tr><td>Error Time</td><td>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                            </table>
                        </div>
                        
                        {'<div class="section"><h3>Additional Context</h3><table class="data-table">' + 
                         ''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in additional_data.items()]) + 
                         '</table></div>' if additional_data else ''}
                        
                        <div class="section">
                            <h3>Recommended Actions</h3>
                            <ul>
                                <li>Check system logs immediately</li>
                                <li>Verify all trading operations</li>
                                <li>Monitor system recovery</li>
                                <li>Contact system administrator</li>
                                <li>Review recent configuration changes</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p><strong>Error Occurred:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                        <p>This is an automated error alert from your Professional Trading System.</p>
                        <p>🤖 Generated with Claude Code | Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return subject, html_body
            
        except Exception as e:
            self.logger.error(f"Error formatting system error email: {e}")
            return f"System Error: {component}", f"<p>Error formatting email: {str(e)}</p>"
    
    def format_system_startup_email(self, system_data: Dict[str, Any]) -> tuple[str, str]:
        """Format system startup email with comprehensive configuration"""
        try:
            subject = "🚀 Trading System Started Successfully"
            
            # Extract data sections
            system_config = system_data.get('system_config', {})
            trading_params = system_data.get('trading_params', {})
            active_strategies = system_data.get('active_strategies', [])
            trading_symbols = system_data.get('trading_symbols', [])
            system_status = system_data.get('system_status', {})
            account_summary = system_data.get('account_summary', {})
            positions_summary = system_data.get('positions_summary', {})
            
            # Build sections HTML
            sections_html = ""
            
            if system_config:
                sections_html += f"""
                <div class="section">
                    <h3>System Configuration</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in system_config.items()])}
                    </table>
                </div>
                """
            
            if trading_params:
                sections_html += f"""
                <div class="section">
                    <h3>Trading Parameters</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in trading_params.items()])}
                    </table>
                </div>
                """
            
            if active_strategies:
                sections_html += f"""
                <div class="section">
                    <h3>Active Strategies ({len(active_strategies)})</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>Strategy {i+1}</td><td>{strategy}</td></tr>' 
                                 for i, strategy in enumerate(active_strategies)])}
                    </table>
                </div>
                """
            
            if trading_symbols:
                sections_html += f"""
                <div class="section">
                    <h3>Trading Symbols ({len(trading_symbols)})</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>Symbol {i+1}</td><td>{symbol}</td></tr>' 
                                 for i, symbol in enumerate(trading_symbols)])}
                    </table>
                </div>
                """
            
            if account_summary:
                sections_html += f"""
                <div class="section">
                    <h3>Account Summary</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in account_summary.items()])}
                    </table>
                </div>
                """
            
            if positions_summary:
                sections_html += f"""
                <div class="section">
                    <h3>Positions Summary</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in positions_summary.items()])}
                    </table>
                </div>
                """
            
            html_body = f"""
            <html>
            <head>
                <style>{self.base_styles}</style>
            </head>
            <body>
                <div class="container">
                    <div class="header" style="background: linear-gradient(135deg, #28a745 0%, #28a745dd 100%);">
                        <h1>🚀 Trading System Started</h1>
                        <p>Professional Trading System</p>
                        <p>System Status: <span class="highlight">OPERATIONAL</span></p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h3>System Status</h3>
                            <p style="margin: 0; font-size: 16px; color: #495057;">
                                Your Professional Trading System has been started successfully and is now running with the configuration shown below.
                            </p>
                        </div>
                        
                        {sections_html}
                    </div>
                    
                    <div class="footer">
                        <p><strong>System Started:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                        <p>This is an automated notification from your Professional Trading System.</p>
                        <p>🤖 Generated with Claude Code | Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return subject, html_body
            
        except Exception as e:
            self.logger.error(f"Error formatting system startup email: {e}")
            return "Trading System Started", f"<p>Error formatting email: {str(e)}</p>"
    
    def format_system_shutdown_email(self, shutdown_data: Dict[str, Any]) -> tuple[str, str]:
        """Format system shutdown email with final statistics"""
        try:
            subject = "🛑 Trading System Shutdown Complete"
            
            # Extract data sections
            statistics = shutdown_data.get('statistics', {})
            account_summary = shutdown_data.get('account_summary', {})
            final_positions = shutdown_data.get('final_positions', [])
            uptime_seconds = shutdown_data.get('uptime_seconds', 0)
            
            # Format uptime
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            
            if hours > 0:
                uptime_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                uptime_str = f"{minutes}m {seconds}s"
            else:
                uptime_str = f"{seconds} seconds"
            
            # Build sections HTML
            sections_html = f"""
            <div class="section">
                <h3>Session Summary</h3>
                <table class="data-table">
                    <tr><td>Session Duration</td><td>{uptime_str}</td></tr>
                    <tr><td>Shutdown Time</td><td>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                    <tr><td>Shutdown Status</td><td><span class="highlight">GRACEFUL</span></td></tr>
                </table>
            </div>
            """
            
            if statistics:
                sections_html += f"""
                <div class="section">
                    <h3>System Statistics</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in statistics.items()])}
                    </table>
                </div>
                """
            
            if account_summary:
                sections_html += f"""
                <div class="section">
                    <h3>Final Account Summary</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>{key.replace("_", " ").title()}</td><td>{value}</td></tr>' 
                                 for key, value in account_summary.items()])}
                    </table>
                </div>
                """
            
            if final_positions:
                sections_html += f"""
                <div class="section">
                    <h3>Final Positions ({len(final_positions)})</h3>
                    <table class="data-table">
                        {''.join([f'<tr><td>Position {i+1}</td><td>{pos.get("symbol", "N/A")} - {pos.get("position_type", "N/A")}</td></tr>' 
                                 for i, pos in enumerate(final_positions[:10])])}
                    </table>
                </div>
                """
            
            html_body = f"""
            <html>
            <head>
                <style>{self.base_styles}</style>
            </head>
            <body>
                <div class="container">
                    <div class="header" style="background: linear-gradient(135deg, #6c757d 0%, #6c757ddd 100%);">
                        <h1>🛑 System Shutdown Complete</h1>
                        <p>Professional Trading System</p>
                        <p>Session Duration: <span class="highlight">{uptime_str}</span></p>
                    </div>
                    
                    <div class="content">
                        <div class="section">
                            <h3>Shutdown Message</h3>
                            <p style="margin: 0; font-size: 16px; color: #495057;">
                                Your Professional Trading System has been shutdown gracefully after running for {uptime_str}. 
                                Below is the summary of system performance and final statistics.
                            </p>
                        </div>
                        
                        {sections_html}
                    </div>
                    
                    <div class="footer">
                        <p><strong>System Shutdown:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                        <p>This is an automated notification from your Professional Trading System.</p>
                        <p>🤖 Generated with Claude Code | Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return subject, html_body
            
        except Exception as e:
            self.logger.error(f"Error formatting system shutdown email: {e}")
            return "Trading System Shutdown", f"<p>Error formatting email: {str(e)}</p>"
    
    def get_template_info(self, template_type: EmailTemplate) -> Dict[str, str]:
        """Get information about available email templates"""
        template_info = {
            EmailTemplate.TRADE_EXECUTION: "Detailed trade execution notification with leverage, margin, and capital information",
            EmailTemplate.POSITION_EXIT: "Comprehensive position exit notification with PnL analysis and account impact",
            EmailTemplate.RISK_ALERT: "Risk management alerts for portfolio and position monitoring",
            EmailTemplate.SYSTEM_ERROR: "Critical system error notifications with diagnostic information",
            EmailTemplate.SYSTEM_STARTUP: "System startup notification with complete configuration overview",
            EmailTemplate.SYSTEM_SHUTDOWN: "System shutdown notification with session statistics and final account status",
            EmailTemplate.ACCOUNT_UPDATE: "Account balance and status update notifications",
            EmailTemplate.PROFIT_ALERT: "Significant profit achievement notifications",
            EmailTemplate.LOSS_ALERT: "Loss threshold breach notifications",
            EmailTemplate.MARGIN_CALL: "Margin call risk and leverage warnings"
        }
        
        return {
            "name": template_type.value,
            "description": template_info.get(template_type, "Email template for trading notifications")
        }