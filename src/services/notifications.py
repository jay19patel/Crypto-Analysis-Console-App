"""
Advanced Notification System for Trading Bot
Handles email notifications, async execution, and multiple notification channels
Uses centralized EmailFormatter for all email templates
"""

import asyncio
import logging
import smtplib
import ssl
import threading
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from src.database.mongodb_client import AsyncMongoDBClient
from src.core.email_formatter import EmailFormatter, TradeExecutionData, PositionExitData
try:
    from src.database.schemas import NotificationLog, NotificationStatus
except ImportError:
    # Define NotificationStatus if not available in schemas
    class NotificationStatus:
        SENT = "sent"
        FAILED = "failed"
        SKIPPED = "skipped"
        PENDING = "pending"
from src.config import get_settings, get_fastapi_mail_config


class NotificationType(Enum):
    """Essential notification types"""
    TRADE_EXECUTION = "trade_execution"
    POSITION_CLOSE = "position_close"
    RISK_ALERT = "risk_alert"
    SYSTEM_ERROR = "system_error"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationEvent:
    """Notification event data"""
    type: NotificationType
    priority: NotificationPriority
    title: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id: Optional[str] = None
    trade_id: Optional[str] = None
    position_id: Optional[str] = None
    symbol: Optional[str] = None
    price: Optional[float] = None
    pnl: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type.value,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "trade_id": self.trade_id,
            "position_id": self.position_id,
            "symbol": self.symbol,
            "price": self.price,
            "pnl": self.pnl
        }


class EmailNotifier:
    """Email notification handler using FastAPI-Mail and MongoDB logging with centralized EmailFormatter"""
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("notifications.email")
        self.mail_config = ConnectionConfig(**get_fastapi_mail_config())
        self.fastmail = FastMail(self.mail_config)
        self.mongo_client = None
        self._mongo_initialized = False
        
        # Initialize centralized email formatter
        self.email_formatter = EmailFormatter()
        
        # Email deduplication cache (trade_id -> timestamp)
        self._sent_emails = {}
        self._cache_timeout = 300  # 5 minutes

    async def _ensure_mongo_connection(self):
        """Ensure MongoDB connection is established"""
        if not self._mongo_initialized:
            try:
                self.mongo_client = AsyncMongoDBClient()
                # Try to connect - some clients have connect method, others don't
                if hasattr(self.mongo_client, 'connect'):
                    await self.mongo_client.connect()
                # Test the connection by attempting a simple operation
                await self._test_mongo_connection()
                self._mongo_initialized = True
                self.logger.info("MongoDB connection established for notifications")
            except Exception as e:
                self.logger.error(f"Failed to connect to MongoDB: {e}")
                # Don't set mongo_client to None here, let it try to work
                self._mongo_initialized = False

    async def _test_mongo_connection(self):
        """Test MongoDB connection"""
        try:
            # Try to ping the database or do a simple operation
            if hasattr(self.mongo_client, 'ping'):
                await self.mongo_client.ping()
            else:
                # Try a simple find operation to test connection
                collection_name = "notifications"
                await self.mongo_client.find_documents(collection_name, {}, limit=1)
        except Exception as e:
            self.logger.warning(f"MongoDB connection test failed: {e}")
            # Don't raise the exception, just log it

    async def send_email(self, subject: str, body: str, recipients: list = None) -> bool:
        """Send email using FastAPI-Mail"""
        if not self.settings.EMAIL_NOTIFICATIONS_ENABLED:
            self.logger.info("Email notifications are disabled")
            return False
            
        if not recipients:
            # Use FASTAPI_MAIL_FROM as fallback recipient if no specific recipients provided
            if self.settings.FASTAPI_MAIL_FROM:
                recipients = [self.settings.FASTAPI_MAIL_FROM]
            
        if not recipients:
            self.logger.warning("No email recipients configured")
            return False
            
        if not self.settings.FASTAPI_MAIL_FROM or '@' not in self.settings.FASTAPI_MAIL_FROM:
            self.logger.warning("FASTAPI_MAIL_FROM is not set to a valid email address!")
            return False

        try:
            message = MessageSchema(
                subject=subject,
                recipients=recipients,
                body=body,
                subtype="html"
            )
            await self.fastmail.send_message(message)
            self.logger.info(f"Email sent successfully to {recipients}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    async def send_notification_email(self, event: NotificationEvent) -> bool:
        """Send notification email and log to database with deduplication"""
        if not self.settings.EMAIL_NOTIFICATIONS_ENABLED:
            self.logger.info("Email notifications are disabled")
            await self._log_notification_to_db(event, "skipped", "Email notifications disabled")
            return False
            
        if not self._should_send_email_for_event(event):
            self.logger.info(f"Email notification skipped for event type: {event.type.value}")
            await self._log_notification_to_db(event, "skipped", f"Event type {event.type.value} disabled")
            return False

        # Check for duplicate emails (for trade execution and risk alerts)
        if self._is_duplicate_notification(event):
            self.logger.info(f"Duplicate/throttled notification prevented: {event.title}")
            await self._log_notification_to_db(event, "skipped", "Duplicate notification prevented")
            return False

        subject = self._create_email_subject(event)
        body = self._create_email_body(event)
        
        status = "failed"
        error = None
        sent = False
        
        try:
            sent = await self.send_email(subject, body)
            if sent:
                status = "sent"
                # Mark email as sent for deduplication/throttling
                self._mark_notification_sent(event)
                self.logger.info(f"Notification email sent successfully: {event.title}")
            else:
                error = "Email sending failed"
                self.logger.error(f"Failed to send notification email: {event.title}")
        except Exception as e:
            status = "failed"
            error = str(e)
            self.logger.error(f"Exception while sending notification email: {e}")

        # Always log to database regardless of email success/failure
        await self._log_notification_to_db(event, status, error)
        
        return sent

    async def _log_notification_to_db(self, event: NotificationEvent, status: str, error: str = None):
        """Log notification to MongoDB database"""
        try:
            await self._ensure_mongo_connection()
            
            if not self.mongo_client:
                self.logger.error("MongoDB client not available for logging")
                return False

            log_data = {
                "type": event.type.value,
                "priority": event.priority.value,
                "title": event.title,
                "message": event.message,
                "data": event.data,
                "timestamp": event.timestamp,
                "user_id": event.user_id,
                "trade_id": event.trade_id,
                "position_id": event.position_id,
                "symbol": event.symbol,
                "price": event.price,
                "pnl": event.pnl,
                "status": status,
                "error": error,
                "created_at": datetime.now(timezone.utc)
            }

            result = await self.mongo_client.insert_document("notifications", log_data)
            
            if result:
                self.logger.info(f"Notification logged to database: {event.title} (Status: {status})")
                return True
            else:
                self.logger.error(f"Failed to log notification to database: {event.title}")
                return False
                
        except Exception as ex:
            self.logger.error(f"Exception while logging to database: {ex}")
            return False
    
    def _should_send_email_for_event(self, event: NotificationEvent) -> bool:
        """Check if email should be sent for this event type"""
        # Send emails for all essential notification types
        return event.type in [
            NotificationType.TRADE_EXECUTION,
            NotificationType.POSITION_CLOSE,
            NotificationType.RISK_ALERT,
            NotificationType.SYSTEM_ERROR,
            NotificationType.SYSTEM_STARTUP,
            NotificationType.SYSTEM_SHUTDOWN
        ]
    
    def _is_duplicate_notification(self, event: NotificationEvent) -> bool:
        """Check if this notification was already sent recently (supports throttling)"""
        
        # Clean old entries
        current_time = time.time()
        self._sent_emails = {
            key: timestamp for key, timestamp in self._sent_emails.items()
            if current_time - timestamp < self._cache_timeout
        }
        
        # For trade executions, use trade_id for strict deduplication
        if event.trade_id:
            cache_key = f"{event.type.value}_{event.trade_id}"
            return cache_key in self._sent_emails
        
        # For risk alerts, use symbol + alert type for throttling (10 minutes)
        if event.type == NotificationType.RISK_ALERT:
            risk_throttle_window = 600  # 10 minutes for risk alerts
            symbol = event.symbol or "PORTFOLIO"
            alert_type = event.data.get("alert_type", "Risk Alert")
            cache_key = f"risk_{symbol}_{alert_type}"
            
            # Check if this specific risk alert was sent recently
            if cache_key in self._sent_emails:
                time_since_last = current_time - self._sent_emails[cache_key]
                return time_since_last < risk_throttle_window
        
        # For other notifications, no throttling by default
        return False
    
    def _mark_notification_sent(self, event: NotificationEvent):
        """Mark this notification as sent in the cache"""
        current_time = time.time()
        
        # For trade executions
        if event.trade_id:
            cache_key = f"{event.type.value}_{event.trade_id}"
            self._sent_emails[cache_key] = current_time
        
        # For risk alerts
        elif event.type == NotificationType.RISK_ALERT:
            symbol = event.symbol or "PORTFOLIO"
            alert_type = event.data.get("alert_type", "Risk Alert")
            cache_key = f"risk_{symbol}_{alert_type}"
            self._sent_emails[cache_key] = current_time
    
    def _create_email_subject(self, event: NotificationEvent) -> str:
        """Create email subject line"""
        priority_emoji = {
            NotificationPriority.LOW: "📧",
            NotificationPriority.MEDIUM: "⚠️",
            NotificationPriority.HIGH: "🚨",
            NotificationPriority.CRITICAL: "🚨🚨"
        }
        
        emoji = priority_emoji.get(event.priority, "📧")
        return f"{emoji} Trading Bot - {event.title}"
    
    def _create_email_body(self, event: NotificationEvent) -> str:
        """Create HTML email body using centralized EmailFormatter"""
        try:
            # Special handling for startup and shutdown emails
            if event.type in [NotificationType.SYSTEM_STARTUP, NotificationType.SYSTEM_SHUTDOWN]:
                return self._create_system_email_body(event)
            
            # Use EmailFormatter for specific notification types
            if event.type == NotificationType.TRADE_EXECUTION:
                trade_data_dict = event.data.get("trade_execution_data")
                if trade_data_dict:
                    # Reconstruct TradeExecutionData object from dictionary
                    if isinstance(trade_data_dict, dict):
                        trade_data = TradeExecutionData(
                            symbol=trade_data_dict.get("symbol", ""),
                            signal=trade_data_dict.get("signal", ""),
                            price=trade_data_dict.get("price", 0.0),
                            quantity=trade_data_dict.get("quantity", 0.0),
                            leverage=trade_data_dict.get("leverage", 1.0),
                            margin_used=trade_data_dict.get("margin_used", 0.0),
                            capital_remaining=trade_data_dict.get("capital_remaining", 0.0),
                            investment_amount=trade_data_dict.get("investment_amount", 0.0),
                            leveraged_amount=trade_data_dict.get("leveraged_amount", 0.0),
                            trade_id=trade_data_dict.get("trade_id", ""),
                            position_id=trade_data_dict.get("position_id", ""),
                            strategy_name=trade_data_dict.get("strategy_name", ""),
                            confidence=trade_data_dict.get("confidence", 100.0),
                            trading_fee=trade_data_dict.get("trading_fee", 0.0),
                            timestamp=datetime.fromisoformat(trade_data_dict.get("timestamp")) if trade_data_dict.get("timestamp") else datetime.now(timezone.utc),
                            account_balance_before=trade_data_dict.get("account_balance_before", 0.0),
                            account_balance_after=trade_data_dict.get("account_balance_after", 0.0)
                        )
                    else:
                        trade_data = trade_data_dict  # Already a TradeExecutionData object
                    
                    _, email_body = self.email_formatter.format_trade_execution_email(trade_data)
                    return email_body
            
            elif event.type == NotificationType.POSITION_CLOSE:
                exit_data_dict = event.data.get("position_exit_data")
                if exit_data_dict:
                    # Reconstruct PositionExitData object from dictionary
                    if isinstance(exit_data_dict, dict):
                        exit_data = PositionExitData(
                            symbol=exit_data_dict.get("symbol", ""),
                            position_type=exit_data_dict.get("position_type", ""),
                            entry_price=exit_data_dict.get("entry_price", 0.0),
                            exit_price=exit_data_dict.get("exit_price", 0.0),
                            quantity=exit_data_dict.get("quantity", 0.0),
                            leverage=exit_data_dict.get("leverage", 1.0),
                            pnl=exit_data_dict.get("pnl", 0.0),
                            pnl_percentage=exit_data_dict.get("pnl_percentage", 0.0),
                            investment_amount=exit_data_dict.get("investment_amount", 0.0),
                            leveraged_amount=exit_data_dict.get("leveraged_amount", 0.0),
                            margin_used=exit_data_dict.get("margin_used", 0.0),
                            trading_fee=exit_data_dict.get("trading_fee", 0.0),
                            exit_fee=exit_data_dict.get("exit_fee", 0.0),
                            total_fees=exit_data_dict.get("total_fees", 0.0),
                            position_id=exit_data_dict.get("position_id", ""),
                            trade_duration=exit_data_dict.get("trade_duration", ""),
                            exit_reason=exit_data_dict.get("exit_reason", ""),
                            account_balance_before=exit_data_dict.get("account_balance_before", 0.0),
                            account_balance_after=exit_data_dict.get("account_balance_after", 0.0),
                            account_growth=exit_data_dict.get("account_growth", 0.0),
                            account_growth_percentage=exit_data_dict.get("account_growth_percentage", 0.0),
                            total_portfolio_pnl=exit_data_dict.get("total_portfolio_pnl", 0.0),
                            win_rate=exit_data_dict.get("win_rate", 0.0),
                            timestamp=datetime.fromisoformat(exit_data_dict.get("timestamp")) if exit_data_dict.get("timestamp") else datetime.now(timezone.utc)
                        )
                    else:
                        exit_data = exit_data_dict  # Already a PositionExitData object
                        
                    _, email_body = self.email_formatter.format_position_exit_email(exit_data)
                    return email_body
            
            elif event.type == NotificationType.RISK_ALERT:
                _, email_body = self.email_formatter.format_risk_alert_email(
                    symbol=event.symbol or "PORTFOLIO",
                    alert_type=event.data.get("alert_type", "Risk Alert"),
                    current_price=event.price or 0.0,
                    risk_level=event.data.get("risk_level", "unknown"),
                    additional_data=event.data
                )
                return email_body
            
            elif event.type == NotificationType.SYSTEM_ERROR:
                _, email_body = self.email_formatter.format_system_error_email(
                    error_message=event.message,
                    component=event.data.get("component", "Unknown"),
                    additional_data=event.data
                )
                return email_body
            
            # Fallback to legacy email format for other types
            return self._create_legacy_email_body(event)
            
        except Exception as e:
            self.logger.error(f"Error creating email body with EmailFormatter: {e}")
            # Fallback to legacy format
            return self._create_legacy_email_body(event)
    
    def _create_legacy_email_body(self, event: NotificationEvent) -> str:
        """Create legacy HTML email body format"""
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Color coding based on priority
        priority_colors = {
            NotificationPriority.LOW: "#28a745",
            NotificationPriority.MEDIUM: "#ffc107",
            NotificationPriority.HIGH: "#fd7e14",
            NotificationPriority.CRITICAL: "#dc3545"
        }
        
        color = priority_colors.get(event.priority, "#6c757d")
        
        # Create data table if data exists
        data_html = ""
        if event.data:
            data_html = "<h3>Additional Details:</h3><table border='1' style='border-collapse: collapse; width: 100%;'>"
            for key, value in event.data.items():
                # Skip complex objects
                if isinstance(value, (str, int, float, bool)) or value is None:
                    data_html += f"<tr><td style='padding: 8px; background-color: #f8f9fa;'><strong>{key.replace('_', ' ').title()}</strong></td><td style='padding: 8px;'>{value}</td></tr>"
            data_html += "</table>"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 8px; }}
                .content {{ margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px; }}
                .info-row {{ margin: 10px 0; }}
                .footer {{ color: #6c757d; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #dee2e6; }}
                table {{ margin-top: 15px; }}
                td {{ border: 1px solid #dee2e6; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{event.title}</h2>
                <p style="margin: 5px 0;"><strong>Priority:</strong> {event.priority.value.upper()}</p>
                <p style="margin: 5px 0;"><strong>Type:</strong> {event.type.value.replace('_', ' ').title()}</p>
            </div>
            
            <div class="content">
                <h3>Message:</h3>
                <p>{event.message}</p>
                
                <div class="info-row">
                    {f'<p><strong>Symbol:</strong> {event.symbol}</p>' if event.symbol else ''}
                    {f'<p><strong>Price:</strong> ${event.price:,.2f}</p>' if event.price else ''}
                    {f'<p><strong>P&L:</strong> <span style="color: {"green" if event.pnl and event.pnl > 0 else "red"}">${event.pnl:,.2f}</span></p>' if event.pnl is not None else ''}
                    {f'<p><strong>Trade ID:</strong> {event.trade_id}</p>' if event.trade_id else ''}
                    {f'<p><strong>Position ID:</strong> {event.position_id}</p>' if event.position_id else ''}
                    {f'<p><strong>User ID:</strong> {event.user_id}</p>' if event.user_id else ''}
                </div>
                
                {data_html}
            </div>
            
            <div class="footer">
                <p><strong>Timestamp:</strong> {timestamp}</p>
                <p>This is an automated notification from your Trading Bot system.</p>
                <p>🤖 Generated with Claude Code | Co-Authored-By: Claude &lt;noreply@anthropic.com&gt;</p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _create_system_email_body(self, event: NotificationEvent) -> str:
        """Create enhanced HTML email body for system startup/shutdown events using EmailFormatter"""
        try:
            if event.type == NotificationType.SYSTEM_STARTUP:
                _, email_body = self.email_formatter.format_system_startup_email(event.data)
                return email_body
            elif event.type == NotificationType.SYSTEM_SHUTDOWN:
                _, email_body = self.email_formatter.format_system_shutdown_email(event.data)
                return email_body
            else:
                # Fallback to legacy format
                return self._create_legacy_system_email_body(event)
        except Exception as e:
            self.logger.error(f"Error creating system email body with EmailFormatter: {e}")
            return self._create_legacy_system_email_body(event)
    
    def _create_legacy_system_email_body(self, event: NotificationEvent) -> str:
        """Create legacy system email body format"""
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Color scheme for system events
        if event.type == NotificationType.SYSTEM_STARTUP:
            header_color = "#28a745"  # Green for startup
            title_emoji = ""
        else:
            header_color = "#6c757d"  # Gray for shutdown
            title_emoji = ""
        
        # Extract system data
        system_config = event.data.get('system_config', {})
        trading_params = event.data.get('trading_params', {})
        active_strategies = event.data.get('active_strategies', [])
        trading_symbols = event.data.get('trading_symbols', [])
        system_status = event.data.get('system_status', {})
        statistics = event.data.get('statistics', {})
        account_summary = event.data.get('account_summary', {})
        positions_summary = event.data.get('positions_summary', {})
        
        # Build HTML sections
        config_html = ""
        if system_config:
            config_html = f"""
            <div class="section">
                <h3>SYSTEM CONFIGURATION</h3>
                <table class="config-table">
                    <tr><td>Strategy Execution Interval</td><td>{system_config.get('strategy_execution_interval', 'N/A')}</td></tr>
                    <tr><td>Historical Data Update</td><td>{system_config.get('historical_data_update', 'N/A')}</td></tr>
                    <tr><td>Live Price Updates</td><td>{system_config.get('live_price_updates', 'N/A')}</td></tr>
                    <tr><td>Risk Check Interval</td><td>{system_config.get('risk_check_interval', 'N/A')}</td></tr>
                </table>
            </div>
            """
        
        trading_html = ""
        if trading_params:
            trading_html = f"""
            <div class="section">
                <h3>TRADING PARAMETERS</h3>
                <table class="config-table">
                    <tr><td>Initial Balance</td><td>{trading_params.get('initial_balance', 'N/A')}</td></tr>
                    <tr><td>Balance Per Trade</td><td>{trading_params.get('balance_per_trade', 'N/A')}</td></tr>
                    <tr><td>Default Leverage</td><td>{trading_params.get('default_leverage', 'N/A')}</td></tr>
                    <tr><td>Stop Loss</td><td>{trading_params.get('stop_loss', 'N/A')}</td></tr>
                    <tr><td>Target Profit</td><td>{trading_params.get('target_profit', 'N/A')}</td></tr>
                    <tr><td>Min Confidence</td><td>{trading_params.get('min_confidence', 'N/A')}</td></tr>
                    <tr><td>Daily Trade Limit</td><td>{trading_params.get('daily_trade_limit', 'N/A')}</td></tr>
                </table>
            </div>
            """
        
        strategies_html = ""
        if active_strategies:
            strategy_list = ''.join([f"<tr><td>{strategy}</td></tr>" for strategy in active_strategies])
            strategies_html = f"""
            <div class="section">
                <h3>ACTIVE STRATEGIES</h3>
                <table class="config-table">
                    {strategy_list}
                </table>
            </div>
            """
        
        symbols_html = ""
        if trading_symbols:
            symbol_list = ''.join([f"<tr><td>{symbol}</td></tr>" for symbol in trading_symbols])
            symbols_html = f"""
            <div class="section">
                <h3>TRADING SYMBOLS</h3>
                <table class="config-table">
                    {symbol_list}
                </table>
            </div>
            """
        
        status_html = ""
        if system_status:
            status_html = f"""
            <div class="section">
                <h3>SYSTEM STATUS</h3>
                <table class="config-table">
                    <tr><td>WebSocket Port</td><td>{system_status.get('websocket_port', 'N/A')}</td></tr>
                    <tr><td>Email Notifications</td><td>{system_status.get('email_notifications', 'N/A')}</td></tr>
                    <tr><td>Log Level</td><td>{system_status.get('log_level', 'N/A')}</td></tr>
                </table>
            </div>
            """
        
        stats_html = ""
        if statistics:
            stats_html = f"""
            <div class="section">
                <h3>FINAL SYSTEM STATISTICS</h3>
                <table class="config-table">
                    <tr><td>Uptime</td><td>{statistics.get('uptime', 'N/A')}</td></tr>
                    <tr><td>Trades Executed</td><td>{statistics.get('trades_executed', 'N/A')}</td></tr>
                    <tr><td>Successful Trades</td><td>{statistics.get('successful_trades', 'N/A')}</td></tr>
                    <tr><td>Failed Trades</td><td>{statistics.get('failed_trades', 'N/A')}</td></tr>
                    <tr><td>Signals Generated</td><td>{statistics.get('signals_generated', 'N/A')}</td></tr>
                    <tr><td>WebSocket Updates</td><td>{statistics.get('websocket_updates', 'N/A')}</td></tr>
                    <tr><td>Strategy Executions</td><td>{statistics.get('strategy_executions', 'N/A')}</td></tr>
                    <tr><td>Total Errors</td><td>{statistics.get('total_errors', 'N/A')}</td></tr>
                </table>
            </div>
            """
        
        account_html = ""
        if account_summary:
            account_html = f"""
            <div class="section">
                <h3>ACCOUNT SUMMARY AT STARTUP</h3>
                <table class="config-table">
                    <tr><td>Current Balance</td><td>{account_summary.get('current_balance', 'N/A')}</td></tr>
                    <tr><td>Total P&L</td><td><span style="color: {'green' if str(account_summary.get('total_pnl', '0')).replace('$', '').replace(',', '').replace('-', '').replace('+', '') != '0' and not str(account_summary.get('total_pnl', '0')).startswith('-') else 'red'}">{account_summary.get('total_pnl', 'N/A')}</span></td></tr>
                    <tr><td>Open Positions</td><td>{account_summary.get('open_positions', 'N/A')}</td></tr>
                    <tr><td>Win Rate</td><td>{account_summary.get('win_rate', 'N/A')}</td></tr>
                    <tr><td>Daily Trades</td><td>{account_summary.get('daily_trades', 'N/A')}</td></tr>
                    <tr><td>Total Trades</td><td>{account_summary.get('total_trades', 'N/A')}</td></tr>
                </table>
            </div>
            """
        
        positions_html = ""
        if positions_summary:
            positions_html = f"""
            <div class="section">
                <h3>POSITIONS SUMMARY AT STARTUP</h3>
                <table class="config-table">
                    <tr><td>Total Open Positions</td><td>{positions_summary.get('total_open', 'N/A')}</td></tr>
                    <tr><td>Total Closed Positions</td><td>{positions_summary.get('total_closed', 'N/A')}</td></tr>
                    <tr><td>Total Unrealized P&L</td><td><span style="color: {'green' if str(positions_summary.get('total_unrealized_pnl', '$0.00')).replace('$', '').replace(',', '').replace('-', '').replace('+', '') != '0.00' and not str(positions_summary.get('total_unrealized_pnl', '$0.00')).startswith('$-') else 'red'}">{positions_summary.get('total_unrealized_pnl', 'N/A')}</span></td></tr>
                </table>
            </div>
            """
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    line-height: 1.6; 
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{ 
                    background: linear-gradient(135deg, {header_color} 0%, {header_color}dd 100%);
                    color: white; 
                    padding: 30px; 
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 300;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    opacity: 0.9;
                    font-size: 16px;
                }}
                .content {{ 
                    padding: 30px; 
                }}
                .section {{
                    margin-bottom: 30px;
                    padding: 20px;
                    background-color: #f8f9fa;
                    border-radius: 8px;
                    border-left: 4px solid {header_color};
                }}
                .section h3 {{
                    margin: 0 0 15px 0;
                    color: #333;
                    font-size: 18px;
                    font-weight: 600;
                }}
                .config-table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    background-color: white;
                    border-radius: 6px;
                    overflow: hidden;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }}
                .config-table td {{ 
                    padding: 12px 16px; 
                    border-bottom: 1px solid #e9ecef;
                    vertical-align: middle;
                }}
                .config-table td:first-child {{
                    background-color: #f8f9fa;
                    font-weight: 600;
                    color: #495057;
                    width: 50%;
                }}
                .config-table td:last-child {{
                    font-family: 'Courier New', monospace;
                    color: #212529;
                }}
                .config-table tr:last-child td {{
                    border-bottom: none;
                }}
                .footer {{ 
                    background-color: #f8f9fa;
                    padding: 20px 30px;
                    border-top: 1px solid #dee2e6;
                    text-align: center;
                    color: #6c757d; 
                    font-size: 14px; 
                }}
                .message-box {{
                    background-color: white;
                    padding: 20px;
                    border-radius: 8px;
                    border: 1px solid #dee2e6;
                    margin-bottom: 20px;
                }}
                .status-badge {{
                    display: inline-block;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-size: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }}
                .status-success {{
                    background-color: #d4edda;
                    color: #155724;
                }}
                .status-info {{
                    background-color: #cce7ff;
                    color: #004085;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{event.title}</h1>
                    <p>Professional Trading System</p>
                    <span class="status-badge {'status-success' if event.type == NotificationType.SYSTEM_STARTUP else 'status-info'}">
                        {event.type.value.replace('_', ' ').title()}
                    </span>
                </div>
                
                <div class="content">
                    <div class="message-box">
                        <h3>System Message</h3>
                        <p style="margin: 0; font-size: 16px; color: #495057;">{event.message}</p>
                    </div>
                    
                    {config_html}
                    {trading_html}
                    {strategies_html}
                    {symbols_html}
                    {status_html}
                    {stats_html}
                    {account_html}
                    {positions_html}
                </div>
                
                <div class="footer">
                    <p><strong>Timestamp:</strong> {timestamp}</p>
                    <p>This is an automated notification from your Professional Trading System.</p>
                    <p>Please do not reply to this email as it is sent from an unmonitored address.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body


class NotificationManager:
    """Advanced notification manager with async support and multiple channels"""
    
    def __init__(self, email_enabled: bool = True):
        self.settings = get_settings()
        self.logger = logging.getLogger("notifications.manager")
        self.email_enabled = email_enabled
        
        # Initialize notification channels
        self.email_notifier = EmailNotifier()
        
        # Async support
        self._notification_queue = asyncio.Queue(maxsize=1000)
        self._notification_task = None
        self._running = False
        
        # Statistics
        self._stats = {
            "total_notifications": 0,
            "emails_sent": 0,
            "emails_failed": 0,
            "last_notification": None
        }
        
        if self.email_enabled:
            self.logger.info("✅ Email notifications enabled (--emailon flag)")
        else:
            self.logger.info("📧 Email notifications disabled (default mode)")
    
    async def start(self):
        """Start notification manager"""
        try:
            if self._running:
                self.logger.info("Notification manager already running")
                return True
            
            self._running = True
            
            # Start async notification processor
            self._notification_task = asyncio.create_task(self._process_notifications())
            
            self.logger.info("Notification manager started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start notification manager: {e}")
            self._running = False
            return False
    
    async def stop(self):
        """Stop notification manager"""
        if not self._running:
            return
        
        self._running = False
        
        # Stop async task
        if self._notification_task:
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Notification manager stopped")
    
    async def send_notification(self, event: NotificationEvent) -> bool:
        """Send notification asynchronously"""
        if not self._running:
            self.logger.warning("Notification manager not running, starting it now")
            await self.start()
        
        try:
            await self._notification_queue.put(event)
            self._stats["total_notifications"] += 1
            self._stats["last_notification"] = datetime.now(timezone.utc)
            self.logger.info(f"Notification queued: {event.type.value} - {event.title}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to queue notification: {e}")
            return False
    
    # Enhanced convenience methods for common notifications
    async def notify_trade_execution(self, symbol: str, signal: str, price: float, 
                                   trade_id: str, position_id: str, quantity: float = 0.0,
                                   leverage: float = 1.0, margin_used: float = 0.0,
                                   capital_remaining: float = 0.0, investment_amount: float = 0.0,
                                   leveraged_amount: float = 0.0, trading_fee: float = 0.0,
                                   strategy_name: str = "", confidence: float = 100.0,
                                   account_balance_before: float = 0.0, account_balance_after: float = 0.0,
                                   pnl: float = 0.0, user_id: str = None) -> bool:
        """Enhanced trade execution notification with detailed position information"""
        
        # Create enhanced trade execution data
        trade_data = TradeExecutionData(
            symbol=symbol,
            signal=signal,
            price=price,
            quantity=quantity,
            leverage=leverage,
            margin_used=margin_used,
            capital_remaining=capital_remaining,
            investment_amount=investment_amount,
            leveraged_amount=leveraged_amount,
            trade_id=trade_id,
            position_id=position_id,
            strategy_name=strategy_name,
            confidence=confidence,
            trading_fee=trading_fee,
            timestamp=datetime.now(timezone.utc),
            account_balance_before=account_balance_before,
            account_balance_after=account_balance_after
        )
        
        event = NotificationEvent(
            type=NotificationType.TRADE_EXECUTION,
            priority=NotificationPriority.HIGH,
            title=f"Trade Executed: {signal} {symbol}",
            message=f"Successfully executed {signal} order for {symbol} at ${price:,.2f} with {leverage:.1f}x leverage",
            symbol=symbol,
            price=price,
            trade_id=trade_id,
            position_id=position_id,
            pnl=pnl,
            user_id=user_id,
            data={
                "trade_execution_data": trade_data.to_dict() if hasattr(trade_data, 'to_dict') else trade_data,
                "signal": signal,
                "execution_price": price,
                "quantity": quantity,
                "leverage": leverage,
                "margin_used": margin_used,
                "capital_remaining": capital_remaining,
                "investment_amount": investment_amount,
                "strategy_name": strategy_name,
                "confidence": confidence,
                "execution_time": datetime.now(timezone.utc).isoformat(),
                "order_type": signal
            }
        )
        return await self.send_notification(event)
    
    async def notify_position_close(self, symbol: str, position_id: str, 
                                  exit_price: float, pnl: float, reason: str,
                                  position_type: str = "LONG", entry_price: float = 0.0,
                                  quantity: float = 0.0, leverage: float = 1.0,
                                  pnl_percentage: float = 0.0, investment_amount: float = 0.0,
                                  leveraged_amount: float = 0.0, margin_used: float = 0.0,
                                  trading_fee: float = 0.0, exit_fee: float = 0.0,
                                  total_fees: float = 0.0, trade_duration: str = "Unknown",
                                  account_balance_before: float = 0.0, account_balance_after: float = 0.0,
                                  account_growth: float = 0.0, account_growth_percentage: float = 0.0,
                                  total_portfolio_pnl: float = 0.0, win_rate: float = 0.0,
                                  user_id: str = None) -> bool:
        """Enhanced position closure notification with comprehensive PnL and account details"""
        
        # Create enhanced position exit data
        exit_data = PositionExitData(
            symbol=symbol,
            position_type=position_type,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            leverage=leverage,
            pnl=pnl,
            pnl_percentage=pnl_percentage,
            investment_amount=investment_amount,
            leveraged_amount=leveraged_amount,
            margin_used=margin_used,
            trading_fee=trading_fee,
            exit_fee=exit_fee,
            total_fees=total_fees,
            position_id=position_id,
            trade_duration=trade_duration,
            exit_reason=reason,
            account_balance_before=account_balance_before,
            account_balance_after=account_balance_after,
            account_growth=account_growth,
            account_growth_percentage=account_growth_percentage,
            total_portfolio_pnl=total_portfolio_pnl,
            win_rate=win_rate,
            timestamp=datetime.now(timezone.utc)
        )
        
        priority = NotificationPriority.CRITICAL if pnl < -100 else NotificationPriority.HIGH
        
        event = NotificationEvent(
            type=NotificationType.POSITION_CLOSE,
            priority=priority,
            title=f"Position Closed: {symbol} | P&L: ${pnl:,.2f}",
            message=f"Position closed for {symbol} at ${exit_price:,.2f}. P&L: ${pnl:,.2f} ({pnl_percentage:.2f}%). Reason: {reason}",
            symbol=symbol,
            price=exit_price,
            position_id=position_id,
            pnl=pnl,
            user_id=user_id,
            data={
                "position_exit_data": exit_data.to_dict() if hasattr(exit_data, 'to_dict') else exit_data,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_percentage": pnl_percentage,
                "reason": reason,
                "position_type": position_type,
                "entry_price": entry_price,
                "quantity": quantity,
                "leverage": leverage,
                "account_growth": account_growth,
                "account_growth_percentage": account_growth_percentage,
                "total_portfolio_pnl": total_portfolio_pnl,
                "win_rate": win_rate,
                "close_time": datetime.now(timezone.utc).isoformat(),
                "profit_loss": "profit" if pnl > 0 else "loss"
            }
        )
        return await self.send_notification(event)
    
    async def notify_risk_alert(self, symbol: str, alert_type: str, 
                               current_price: float, risk_level: str,
                               user_id: str = None) -> bool:
        """Notify about risk alerts"""
        event = NotificationEvent(
            type=NotificationType.RISK_ALERT,
            priority=NotificationPriority.CRITICAL,
            title=f"Risk Alert: {symbol}",
            message=f"Risk alert for {symbol}: {alert_type} at ${current_price:,.2f}. Risk level: {risk_level}",
            symbol=symbol,
            price=current_price,
            user_id=user_id,
            data={
                "alert_type": alert_type,
                "risk_level": risk_level,
                "current_price": current_price,
                "alert_time": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    async def notify_system_error(self, error_message: str, component: str, 
                                 user_id: str = None) -> bool:
        """Notify about system errors"""
        event = NotificationEvent(
            type=NotificationType.SYSTEM_ERROR,
            priority=NotificationPriority.CRITICAL,
            title=f"System Error: {component}",
            message=f"System error in {component}: {error_message}",
            user_id=user_id,
            data={
                "error_message": error_message,
                "component": component,
                "error_time": datetime.now(timezone.utc).isoformat(),
                "severity": "critical"
            }
        )
        return await self.send_notification(event)
    
    async def notify_system_startup(self, system_config: dict = None, 
                                  trading_params: dict = None,
                                  active_strategies: list = None,
                                  trading_symbols: list = None,
                                  system_status: dict = None,
                                  account_summary: dict = None,
                                  positions_summary: dict = None,
                                  user_id: str = None) -> bool:
        """Send comprehensive system startup notification email"""
        try:
            from src.config import get_settings, get_trading_config, get_system_intervals
            
            # Get system configuration if not provided
            if not system_config:
                settings = get_settings()
                intervals = get_system_intervals()
                system_config = {
                    "strategy_execution_interval": f"{intervals['strategy_execution']}s ({intervals['strategy_execution']//60} minutes)",
                    "historical_data_update": f"{intervals['historical_data_update']}s ({intervals['historical_data_update']//60} minutes)",
                    "risk_check_interval": f"{intervals['risk_check']}s"
                }
            
            if not trading_params:
                trading_config = get_trading_config()
                trading_params = {
                    "initial_balance": f"${trading_config['initial_balance']:,.2f}",
                    "balance_per_trade": f"{trading_config['balance_per_trade_pct']*100:.0f}%",
                    "default_leverage": f"{trading_config['default_leverage']:.0f}x",
                    "stop_loss": f"{trading_config['stop_loss_pct']*100:.1f}%",
                    "target_profit": f"{trading_config['target_pct']*100:.1f}%",
                    "min_confidence": f"{trading_config['min_confidence']:.1f}%",
                    "daily_trade_limit": str(trading_config['daily_trades_limit'])
                }
            
            if not active_strategies:
                settings = get_settings()
                active_strategies = settings.STRATEGY_CLASSES
            
            if not trading_symbols:
                settings = get_settings()
                trading_symbols = settings.TRADING_SYMBOLS
            
            if not system_status:
                settings = get_settings()
                system_status = {
                    "websocket_port": str(settings.WEBSOCKET_PORT),
                    "email_notifications": "Enabled" if settings.EMAIL_NOTIFICATIONS_ENABLED else "Disabled",
                    "log_level": settings.LOG_LEVEL
                }
            
            # Format account summary for email display
            formatted_account_summary = None
            if account_summary:
                formatted_account_summary = {
                    "current_balance": f"${account_summary.get('current_balance', 0):,.2f}",
                    "total_pnl": f"${account_summary.get('total_pnl', 0):,.2f}",
                    "open_positions": str(account_summary.get('open_positions', 0)),
                    "win_rate": f"{account_summary.get('win_rate', 0):.1f}%",
                    "daily_trades": str(account_summary.get('daily_trades', 0)),
                    "total_trades": str(account_summary.get('total_trades', 0))
                }
            
            # Format positions summary
            formatted_positions = None
            if positions_summary:
                formatted_positions = {
                    "total_open": str(positions_summary.get('total_open', 0)),
                    "total_closed": str(positions_summary.get('total_closed', 0)),
                    "total_unrealized_pnl": f"${positions_summary.get('total_unrealized_pnl', 0):,.2f}"
                }
            
            event = NotificationEvent(
                type=NotificationType.SYSTEM_STARTUP,
                priority=NotificationPriority.HIGH,
                title="Trading System Started Successfully",
                message="Your Professional Trading System has been started and is now running with the configuration and account status shown below.",
                user_id=user_id,
                data={
                    "system_config": system_config,
                    "trading_params": trading_params,
                    "active_strategies": active_strategies,
                    "trading_symbols": trading_symbols,
                    "system_status": system_status,
                    "account_summary": formatted_account_summary,
                    "positions_summary": formatted_positions,
                    "startup_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            return await self.send_notification(event)
            
        except Exception as e:
            self.logger.error(f"Failed to send system startup notification: {e}")
            return False
    
    async def notify_system_shutdown(self, uptime_seconds: float = 0,
                                   statistics: dict = None,
                                   account_summary: dict = None,
                                   final_positions: list = None,
                                   user_id: str = None) -> bool:
        """Send comprehensive system shutdown notification email"""
        try:
            # Format uptime
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            
            if hours > 0:
                uptime_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                uptime_str = f"{minutes}m {seconds}s"
            else:
                uptime_str = f"{seconds:.1f} seconds"
            
            # Default statistics if not provided
            if not statistics:
                statistics = {
                    "uptime": uptime_str,
                    "trades_executed": "0",
                    "successful_trades": "0",
                    "failed_trades": "0",
                    "signals_generated": "0",
                    "strategy_executions": "0",
                    "total_errors": "0"
                }
            else:
                statistics["uptime"] = uptime_str
            
            # Default account summary if not provided
            if not account_summary:
                account_summary = {
                    "current_balance": "$0.00",
                    "total_pnl": "$0.00",
                    "open_positions": "0",
                    "win_rate": "0.0%",
                    "daily_trades": "0"
                }
            
            event = NotificationEvent(
                type=NotificationType.SYSTEM_SHUTDOWN,
                priority=NotificationPriority.MEDIUM,
                title="Trading System Shutdown Complete",
                message=f"Your Professional Trading System has been shutdown after running for {uptime_str}. Below is the summary of system performance and final statistics.",
                user_id=user_id,
                data={
                    "statistics": statistics,
                    "account_summary": account_summary,
                    "final_positions": final_positions or [],
                    "shutdown_time": datetime.now(timezone.utc).isoformat(),
                    "uptime_seconds": uptime_seconds
                }
            )
            
            return await self.send_notification(event)
            
        except Exception as e:
            self.logger.error(f"Failed to send system shutdown notification: {e}")
            return False
    
    
    # Private methods
    async def _process_notifications(self):
        """Process notifications asynchronously"""
        self.logger.info("Started processing notifications")
        
        while self._running:
            try:
                # Wait for notification with timeout
                try:
                    event = await asyncio.wait_for(self._notification_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                # Process notification
                await self._process_single_notification(event)
                
            except asyncio.CancelledError:
                self.logger.info("Notification processing cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")
    
    async def _process_single_notification(self, event: NotificationEvent):
        """Process a single notification asynchronously"""
        try:
            self.logger.info(f"Processing notification: {event.type.value} - {event.title}")
            
            # Send email notification and log to database
            if self.email_enabled:
                if await self.email_notifier.send_notification_email(event):
                    self._stats["emails_sent"] += 1
                    self.logger.info(f"Email notification sent successfully: {event.title}")
                else:
                    self._stats["emails_failed"] += 1
                    self.logger.warning(f"Email notification failed: {event.title}")
            else:
                # Only log to database when email is disabled
                self.logger.info(f"Email disabled - storing notification in database only: {event.title}")
                await self.email_notifier._log_notification_to_db(event, "stored_no_email", "Email disabled by --emailoff")
            
        except Exception as e:
            self.logger.error(f"Error processing notification {event.type.value}: {e}")
            self._stats["emails_failed"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return {
            **self._stats,
            "queue_size": self._notification_queue.qsize() if self._notification_queue else 0,
            "running": self._running
        }

    async def test_email_connection(self) -> bool:
        """Test email connection and settings"""
        try:
            test_event = NotificationEvent(
                type=NotificationType.SYSTEM_ERROR,
                priority=NotificationPriority.LOW,
                title="Test Email - Connection Check",
                message="This is a test email to verify the notification system is working correctly.",
                data={"test": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
            
            result = await self.email_notifier.send_notification_email(test_event)
            if result:
                self.logger.info("Test email sent successfully")
            else:
                self.logger.error("Test email failed to send")
            return result
            
        except Exception as e:
            self.logger.error(f"Test email failed with exception: {e}")
            return False