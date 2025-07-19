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

from src.config import get_settings


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
    """Email notification handler"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger("notifications.email")
        self.smtp_connection = None
        self._connection_lock = threading.Lock()
        
    def _create_smtp_connection(self) -> Optional[smtplib.SMTP]:
        """Create SMTP connection"""
        try:
            if self.settings.EMAIL_TLS:
                smtp = smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT)
                smtp.starttls(context=ssl.create_default_context())
            else:
                smtp = smtplib.SMTP_SSL(self.settings.SMTP_HOST, self.settings.SMTP_PORT)
            
            if self.settings.SMTP_USERNAME and self.settings.SMTP_PASSWORD:
                smtp.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
            
            return smtp
        except Exception as e:
            self.logger.error(f"Failed to create SMTP connection: {e}")
            return None
    
    def send_email(self, subject: str, body: str, recipients: List[str] = None) -> bool:
        """Send email notification"""
        # if not self.settings.EMAIL_NOTIFICATIONS_ENABLED:
        #     return False
        
        # if not recipients:
        #     recipients = self.settings.EMAIL_TO
        
        # if not recipients:
        #     self.logger.warning("No email recipients configured")
        #     return False
        
        try:
            # with self._connection_lock:
            #     smtp = self._create_smtp_connection()
            #     if not smtp:
            #         return False
                
            #     # Create message
            #     msg = MIMEMultipart()
            #     msg['From'] = self.settings.EMAIL_FROM
            #     msg['To'] = ', '.join(recipients)
            #     msg['Subject'] = f"[Trading Bot] {subject}"
                
            #     # Add body
            #     msg.attach(MIMEText(body, 'html'))
                
            #     # Send email
            #     smtp.send_message(msg)
            #     smtp.quit()
                
            #     self.logger.info(f"Email sent successfully to {len(recipients)} recipients")
                print(f"""---------------------------[EMAIL]---------------------------
                        Subject : {subject}
                        body :  {body}
                        recipients :  {recipients}
                        -------------------------------------------------------------""")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def send_notification_email(self, event: NotificationEvent) -> bool:
        """Send notification email based on event"""
        if not self.settings.EMAIL_NOTIFICATIONS_ENABLED:
            return False
        
        # Check if this event type should trigger email
        if not self._should_send_email_for_event(event):
            return False
        
        # Create email content
        subject = self._create_email_subject(event)
        body = self._create_email_body(event)
        
        return self.send_email(subject, body)
    
    def _should_send_email_for_event(self, event: NotificationEvent) -> bool:
        """Check if email should be sent for this event type"""
        event_settings = {
            NotificationType.TRADE_EXECUTION: self.settings.NOTIFY_ON_TRADE_EXECUTION,
            NotificationType.POSITION_CLOSE: self.settings.NOTIFY_ON_POSITION_CLOSE,
            NotificationType.RISK_ALERT: self.settings.NOTIFY_ON_RISK_ALERT,
            NotificationType.SYSTEM_ERROR: self.settings.NOTIFY_ON_SYSTEM_ERROR,
            NotificationType.ACCOUNT_UPDATE: self.settings.NOTIFY_ON_ACCOUNT_UPDATE,
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
        return f"{emoji} {event.title}"
    
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
            data_html = "<h3>Details:</h3><table border='1' style='border-collapse: collapse;'>"
            for key, value in event.data.items():
                data_html += f"<tr><td style='padding: 5px;'><strong>{key}</strong></td><td style='padding: 5px;'>{value}</td></tr>"
            data_html += "</table>"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 5px; }}
                .content {{ margin: 20px 0; }}
                .footer {{ color: #6c757d; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>{event.title}</h2>
                <p><strong>Priority:</strong> {event.priority.value.upper()}</p>
                <p><strong>Type:</strong> {event.type.value.replace('_', ' ').title()}</p>
            </div>
            
            <div class="content">
                <p>{event.message}</p>
                
                {f'<p><strong>Symbol:</strong> {event.symbol}</p>' if event.symbol else ''}
                {f'<p><strong>Price:</strong> ${event.price:.2f}</p>' if event.price else ''}
                {f'<p><strong>P&L:</strong> ${event.pnl:.2f}</p>' if event.pnl else ''}
                {f'<p><strong>Trade ID:</strong> {event.trade_id}</p>' if event.trade_id else ''}
                {f'<p><strong>Position ID:</strong> {event.position_id}</p>' if event.position_id else ''}
                
                {data_html}
            </div>
            
            <div class="footer">
                <p><strong>Timestamp:</strong> {timestamp}</p>
                <p>This is an automated notification from your Trading Bot system.</p>
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
        
        # Threading support for sync operations
        self._thread_pool = ThreadPoolExecutor(max_workers=5)
        self._sync_queue = queue.Queue(maxsize=1000)
        self._sync_thread = None
        
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
            return
        
        self._running = True
        
        # Start async notification processor
        self._notification_task = asyncio.create_task(self._process_notifications())
        
        # Start sync notification processor
        self._sync_thread = threading.Thread(target=self._process_sync_notifications, daemon=True)
        self._sync_thread.start()
        
        self.logger.info("Notification manager started")
    
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
        
        # Stop sync thread
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=True)
        
        self.logger.info("Notification manager stopped")
    
    async def send_notification(self, event: NotificationEvent) -> bool:
        """Send notification asynchronously"""
        if not self._running:
            return False
        
        try:
            await self._notification_queue.put(event)
            self._stats["total_notifications"] += 1
            self._stats["last_notification"] = datetime.now(timezone.utc)
            return True
        except asyncio.QueueFull:
            self.logger.warning("Notification queue is full, dropping notification")
            return False
    
    def send_notification_sync(self, event: NotificationEvent) -> bool:
        """Send notification synchronously"""
        try:
            self._sync_queue.put_nowait(event)
            self._stats["total_notifications"] += 1
            self._stats["last_notification"] = datetime.now(timezone.utc)
            return True
        except queue.Full:
            self.logger.warning("Sync notification queue is full, dropping notification")
            return False
    
    # Convenience methods for common notifications
    async def notify_trade_execution(self, symbol: str, signal: str, price: float, 
                                   trade_id: str, position_id: str, pnl: float = 0.0) -> bool:
        """Notify about trade execution"""
        event = NotificationEvent(
            type=NotificationType.TRADE_EXECUTION,
            priority=NotificationPriority.HIGH,
            title=f"Trade Executed: {signal} {symbol}",
            message=f"Successfully executed {signal} order for {symbol} at ${price:.2f}",
            symbol=symbol,
            price=price,
            trade_id=trade_id,
            position_id=position_id,
            pnl=pnl,
            data={
                "signal": signal,
                "execution_price": price,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    async def notify_position_close(self, symbol: str, position_id: str, 
                                  exit_price: float, pnl: float, reason: str) -> bool:
        """Notify about position closure"""
        priority = NotificationPriority.CRITICAL if pnl < -100 else NotificationPriority.HIGH
        
        event = NotificationEvent(
            type=NotificationType.POSITION_CLOSE,
            priority=priority,
            title=f"Position Closed: {symbol}",
            message=f"Position closed for {symbol} at ${exit_price:.2f}. P&L: ${pnl:.2f}. Reason: {reason}",
            symbol=symbol,
            price=exit_price,
            position_id=position_id,
            pnl=pnl,
            data={
                "exit_price": exit_price,
                "pnl": pnl,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    async def notify_risk_alert(self, symbol: str, alert_type: str, 
                               current_price: float, risk_level: str) -> bool:
        """Notify about risk alerts"""
        event = NotificationEvent(
            type=NotificationType.RISK_ALERT,
            priority=NotificationPriority.CRITICAL,
            title=f"Risk Alert: {symbol}",
            message=f"Risk alert for {symbol}: {alert_type} at ${current_price:.2f}. Risk level: {risk_level}",
            symbol=symbol,
            price=current_price,
            data={
                "alert_type": alert_type,
                "risk_level": risk_level,
                "current_price": current_price,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    async def notify_system_error(self, error_message: str, component: str) -> bool:
        """Notify about system errors"""
        event = NotificationEvent(
            type=NotificationType.SYSTEM_ERROR,
            priority=NotificationPriority.CRITICAL,
            title=f"System Error: {component}",
            message=f"System error in {component}: {error_message}",
            data={
                "error_message": error_message,
                "component": component,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    async def notify_profit_alert(self, symbol: str, pnl: float, 
                                 profit_percentage: float) -> bool:
        """Notify about significant profits"""
        event = NotificationEvent(
            type=NotificationType.PROFIT_ALERT,
            priority=NotificationPriority.MEDIUM,
            title=f"Profit Alert: {symbol}",
            message=f"Significant profit for {symbol}: ${pnl:.2f} ({profit_percentage:.1f}%)",
            symbol=symbol,
            pnl=pnl,
            data={
                "profit_percentage": profit_percentage,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    async def notify_margin_call(self, account_id: str, margin_usage: float) -> bool:
        """Notify about margin call risk"""
        event = NotificationEvent(
            type=NotificationType.MARGIN_CALL,
            priority=NotificationPriority.CRITICAL,
            title=f"Margin Call Alert: {account_id}",
            message=f"High margin usage detected: {margin_usage:.1f}%. Consider reducing positions.",
            user_id=account_id,
            data={
                "margin_usage": margin_usage,
                "account_id": account_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return await self.send_notification(event)
    
    # Private methods
    async def _process_notifications(self):
        """Process notifications asynchronously"""
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
                break
            except Exception as e:
                self.logger.error(f"Error processing notification: {e}")
    
    def _process_sync_notifications(self):
        """Process notifications synchronously"""
        while self._running:
            try:
                # Wait for notification with timeout
                try:
                    event = self._sync_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process notification
                self._process_single_notification_sync(event)
                
            except Exception as e:
                self.logger.error(f"Error processing sync notification: {e}")
    
    async def _process_single_notification(self, event: NotificationEvent):
        """Process a single notification asynchronously"""
        try:
            # Send email notification
            if self.email_notifier.send_notification_email(event):
                self._stats["emails_sent"] += 1
            else:
                self._stats["emails_failed"] += 1
            
            # Log notification
            self.logger.info(f"Notification sent: {event.type.value} - {event.title}")
            
        except Exception as e:
            self.logger.error(f"Error processing notification {event.type.value}: {e}")
    
    def _process_single_notification_sync(self, event: NotificationEvent):
        """Process a single notification synchronously"""
        try:
            # Send email notification
            if self.email_notifier.send_notification_email(event):
                self._stats["emails_sent"] += 1
            else:
                self._stats["emails_failed"] += 1
            
            # Log notification
            self.logger.info(f"Sync notification sent: {event.type.value} - {event.title}")
            
        except Exception as e:
            self.logger.error(f"Error processing sync notification {event.type.value}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return {
            **self._stats,
            "queue_size": self._notification_queue.qsize(),
            "sync_queue_size": self._sync_queue.qsize(),
            "running": self._running
        } 