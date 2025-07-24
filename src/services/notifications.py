"""
Advanced Notification System for Trading Bot
Handles email notifications, async execution, and multiple notification channels
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
    """Notification types"""
    TRADE_EXECUTION = "trade_execution"
    POSITION_CLOSE = "position_close"
    RISK_ALERT = "risk_alert"
    SYSTEM_ERROR = "system_error"
    ACCOUNT_UPDATE = "account_update"
    PROFIT_ALERT = "profit_alert"
    LOSS_ALERT = "loss_alert"
    MARGIN_CALL = "margin_call"
    STRATEGY_SIGNAL = "strategy_signal"


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
    """Email notification handler using FastAPI-Mail and MongoDB logging"""
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("notifications.email")
        self.mail_config = ConnectionConfig(**get_fastapi_mail_config())
        self.fastmail = FastMail(self.mail_config)
        self.mongo_client = None
        self._mongo_initialized = False

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
            recipients = [email.strip() for email in self.settings.EMAIL_TO.split(',') if email.strip()]
            
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
        """Send notification email and log to database"""
        if not self.settings.EMAIL_NOTIFICATIONS_ENABLED:
            self.logger.info("Email notifications are disabled")
            await self._log_notification_to_db(event, "skipped", "Email notifications disabled")
            return False
            
        if not self._should_send_email_for_event(event):
            self.logger.info(f"Email notification skipped for event type: {event.type.value}")
            await self._log_notification_to_db(event, "skipped", f"Event type {event.type.value} disabled")
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
        event_settings = {
            NotificationType.TRADE_EXECUTION: getattr(self.settings, 'NOTIFY_ON_TRADE_EXECUTION', True),
            NotificationType.POSITION_CLOSE: getattr(self.settings, 'NOTIFY_ON_POSITION_CLOSE', True),
            NotificationType.RISK_ALERT: getattr(self.settings, 'NOTIFY_ON_RISK_ALERT', True),
            NotificationType.SYSTEM_ERROR: getattr(self.settings, 'NOTIFY_ON_SYSTEM_ERROR', True),
            NotificationType.ACCOUNT_UPDATE: getattr(self.settings, 'NOTIFY_ON_ACCOUNT_UPDATE', True),
            NotificationType.PROFIT_ALERT: True,
            NotificationType.LOSS_ALERT: True,
            NotificationType.MARGIN_CALL: True,
            NotificationType.STRATEGY_SIGNAL: True,
        }
        
        return event_settings.get(event.type, True)
    
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
        """Create HTML email body"""
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
                <p>Please do not reply to this email as it is sent from an unmonitored address.</p>
            </div>
        </body>
        </html>
        """
        
        return html_body


class NotificationManager:
    """Advanced notification manager with async support and multiple channels"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("notifications.manager")
        
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
    
    async def start(self):
        """Start notification manager"""
        if self._running:
            self.logger.info("Notification manager already running")
            return
        
        self._running = True
        
        # Start async notification processor
        self._notification_task = asyncio.create_task(self._process_notifications())
        
        self.logger.info("Notification manager started successfully")
    
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
    
    # Convenience methods for common notifications
    async def notify_trade_execution(self, symbol: str, signal: str, price: float, 
                                   trade_id: str, position_id: str, pnl: float = 0.0, 
                                   user_id: str = None) -> bool:
        """Notify about trade execution"""
        event = NotificationEvent(
            type=NotificationType.TRADE_EXECUTION,
            priority=NotificationPriority.HIGH,
            title=f"Trade Executed: {signal} {symbol}",
            message=f"Successfully executed {signal} order for {symbol} at ${price:,.2f}",
            symbol=symbol,
            price=price,
            trade_id=trade_id,
            position_id=position_id,
            pnl=pnl,
            user_id=user_id,
            data={
                "signal": signal,
                "execution_price": price,
                "execution_time": datetime.now(timezone.utc).isoformat(),
                "order_type": signal
            }
        )
        return await self.send_notification(event)
    
    async def notify_position_close(self, symbol: str, position_id: str, 
                                  exit_price: float, pnl: float, reason: str,
                                  user_id: str = None) -> bool:
        """Notify about position closure"""
        priority = NotificationPriority.CRITICAL if pnl < -100 else NotificationPriority.HIGH
        
        event = NotificationEvent(
            type=NotificationType.POSITION_CLOSE,
            priority=priority,
            title=f"Position Closed: {symbol}",
            message=f"Position closed for {symbol} at ${exit_price:,.2f}. P&L: ${pnl:,.2f}. Reason: {reason}",
            symbol=symbol,
            price=exit_price,
            position_id=position_id,
            pnl=pnl,
            user_id=user_id,
            data={
                "exit_price": exit_price,
                "pnl": pnl,
                "reason": reason,
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
    
    async def notify_profit_alert(self, symbol: str, pnl: float, 
                                 profit_percentage: float, user_id: str = None) -> bool:
        """Notify about significant profits"""
        event = NotificationEvent(
            type=NotificationType.PROFIT_ALERT,
            priority=NotificationPriority.MEDIUM,
            title=f"Profit Alert: {symbol}",
            message=f"Significant profit for {symbol}: ${pnl:,.2f} ({profit_percentage:.1f}%)",
            symbol=symbol,
            pnl=pnl,
            user_id=user_id,
            data={
                "profit_percentage": profit_percentage,
                "profit_amount": pnl,
                "alert_time": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    async def notify_margin_call(self, account_id: str, margin_usage: float) -> bool:
        """Notify about margin call risk"""
        event = NotificationEvent(
            type=NotificationType.MARGIN_CALL,
            priority=NotificationPriority.CRITICAL,
            title=f"Margin Call Alert",
            message=f"High margin usage detected: {margin_usage:.1f}%. Consider reducing positions immediately.",
            user_id=account_id,
            data={
                "margin_usage": margin_usage,
                "account_id": account_id,
                "alert_time": datetime.now(timezone.utc).isoformat(),
                "recommendation": "Reduce positions or add funds"
            }
        )
        return await self.send_notification(event)
    
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
            if await self.email_notifier.send_notification_email(event):
                self._stats["emails_sent"] += 1
                self.logger.info(f"Email notification sent successfully: {event.title}")
            else:
                self._stats["emails_failed"] += 1
                self.logger.warning(f"Email notification failed: {event.title}")
            
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