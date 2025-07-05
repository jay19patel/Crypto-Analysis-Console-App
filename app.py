#!/usr/bin/env python3
"""
Cryptocurrency Trading System with AI Analysis
Simple interface: python app.py (starts everything), python app.py --save (saves to MongoDB)
"""

import argparse
import sys
import time
import threading
import signal
import os
from typing import Optional
import logging
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.live import Live
from rich.table import Table
from rich.style import Style
from rich.layout import Layout
from rich.text import Text
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.config import get_settings
from src.broker.broker_client import BrokerClient
from src.data.technical_analysis import TechnicalAnalysis
from src.data.websocket_client import WebSocketClient
from src.system.health_checker import SystemHealthChecker
from src.data.mongodb_client import MongoDBClient
from src.system.websocket_server import WebSocketServer
from src.broker.position_manager import PositionManager
from src.broker.delta_client import DeltaBrokerClient

# Initialize rich console
console = Console()

def setup_logging():
    """Setup logging configuration"""
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging to file only
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        handlers=[
            logging.FileHandler(settings.LOG_FILE)
        ]
    )
    return logging.getLogger(__name__)

class SystemStatus:
    def __init__(self):
        self.components = {
            "WebSocket Server": "Pending",
            "MongoDB Connection": "Pending", 
            "Delta WebSocket": "Pending",
            "Delta API": "Pending",
            "Technical Analysis": "Pending",
            "Position Manager": "Pending"
        }
        self.is_ready = False
        self.is_online = False
        self.processing_status = "Initializing"
        self.progress = 0  # 0-100
        self.last_activity = {
            "Live Price Update": "Never",
            "Position Check": "Never", 
            "Technical Analysis": "Never",
            "Trade Execution": "Never"
        }
        self.logs = []  # Store recent logs for display
        
    def update(self, component: str, status: str):
        """Update component status: 'Pending', 'Done', 'Failed'"""
        self.components[component] = status
        self.is_ready = all(s == "Done" for s in self.components.values())
        self.is_online = self.is_ready
        if self.is_ready:
            self.processing_status = "Online Processing"
            self.progress = 100
        else:
            done_count = sum(1 for s in self.components.values() if s == "Done")
            self.progress = int((done_count / len(self.components)) * 100)
        
    def update_activity(self, activity: str):
        self.last_activity[activity] = datetime.now().strftime("%H:%M:%S")
        
    def add_log(self, message: str, level: str = "info"):
        """Add log message to display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
        # Keep only last 10 logs
        if len(self.logs) > 10:
            self.logs = self.logs[-10:]
        
    def get_config_table(self) -> Table:
        """Get configuration table"""
        settings = get_settings()
        table = Table(title="System Configuration", show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        configs = [
            ("WebSocket Server URL", f"ws://{settings.WEBSOCKET_SERVER_HOST}:{settings.WEBSOCKET_SERVER_PORT}"),
            ("Delta WebSocket URL", settings.DELTA_WEBSOCKET_URL),
            ("MongoDB URI", settings.MONGODB_URI),
            ("Database Name", settings.DATABASE_NAME),
            ("Default Symbols", ", ".join(settings.DEFAULT_SYMBOLS)),
            ("Price Update Interval", f"{settings.POSITION_CHECK_INTERVAL}s"),
            ("Analysis Interval", f"{settings.ANALYSIS_INTERVAL}s"),
            ("System Check Timeout", f"{settings.SYSTEM_CHECK_TIMEOUT}s"),
            ("WebSocket Update Interval", f"{settings.WEBSOCKET_UPDATE_INTERVAL}s"),
            ("Default Refresh Interval", f"{settings.DEFAULT_REFRESH_INTERVAL}s"),
            ("Min Trade Confidence", f"{settings.BROKER_MIN_CONFIDENCE}%"),
            ("Risk Per Trade", f"{settings.BROKER_RISK_PER_TRADE * 100}%"),
            ("Default Leverage", f"{settings.BROKER_DEFAULT_LEVERAGE}x"),
            ("Stop Loss %", f"{settings.BROKER_STOP_LOSS_PCT * 100}%"),
            ("Target %", f"{settings.BROKER_TARGET_PCT * 100}%")
        ]
        
        for setting, value in configs:
            table.add_row(setting, str(value))
        
        return table
        
    def get_status_table(self) -> Table:
        """Get system status table with progress"""
        status_title = f"{'🟢 ONLINE' if self.is_online else '🔴 OFFLINE'} - {self.processing_status} ({self.progress}%)"
        table = Table(title=status_title, show_header=True, header_style="bold blue")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        
        for component, status in self.components.items():
            if status == "Done":
                status_text = "[green]✓ Done"
            elif status == "Failed":
                status_text = "[red]✗ Failed"
            else:
                status_text = "[yellow]⏳ Pending"
            table.add_row(component, status_text)
        
        # Add progress bar
        if self.progress < 100:
            progress_bar = "█" * (self.progress // 10) + "░" * (10 - (self.progress // 10))
            table.add_row("[bold]Progress", f"[cyan]{progress_bar}[/cyan] {self.progress}%")
        
        return table
        
    def get_activity_table(self) -> Table:
        """Get live activity table with logs"""
        table = Table(title="Live Activity & Logs", show_header=True, header_style="bold yellow")
        table.add_column("Type", style="cyan", width=15)
        table.add_column("Time", style="green", width=10)
        table.add_column("Details", style="white")
        
        current_time = datetime.now()
        
        # Add activity status
        for activity, last_time in self.last_activity.items():
            if last_time == "Never":
                status = "[red]Waiting"
            else:
                try:
                    last_dt = datetime.strptime(last_time, "%H:%M:%S").replace(
                        year=current_time.year,
                        month=current_time.month, 
                        day=current_time.day
                    )
                    diff = (current_time - last_dt).total_seconds()
                    if diff < 15:
                        status = "[green]Active"
                    elif diff < 60:
                        status = "[yellow]Recent"
                    else:
                        status = "[red]Idle"
                except:
                    status = "[red]Error"
            
            table.add_row(f"[bold]{activity}", last_time, status)
        
        # Add separator
        if self.last_activity and self.logs:
            table.add_row("─────────", "──────", "─────────────────────────")
        
        # Add recent logs
        for log in self.logs[-5:]:  # Show last 5 logs
            level_color = {
                "info": "blue",
                "warning": "yellow", 
                "error": "red",
                "success": "green"
            }.get(log["level"], "white")
            
            table.add_row(
                f"[{level_color}]LOG",
                log["timestamp"],
                f"[{level_color}]{log['message']}"
            )
        
        return table

# Initialize logger at module level
logger = setup_logging()

# Create a stop event for graceful shutdown
stop_event = threading.Event()

class ActivityMonitor:
    def __init__(self, system_status):
        self.system_status = system_status
        self._stop_event = threading.Event()
        
    def start_monitoring(self, websocket_client):
        """Start monitoring system activities"""
        def monitor():
            last_price_check = 0
            last_analysis_check = 0
            
            while not self._stop_event.is_set():
                try:
                    current_time = time.time()
                    
                    # Check if WebSocket client system is ready and update status accordingly
                    if websocket_client and hasattr(websocket_client, '_system_ready'):
                        if websocket_client._system_ready:
                            # Mark all components as Done if system is ready
                            if self.system_status.components.get("Delta WebSocket") != "Done":
                                self.system_status.update("Delta WebSocket", "Done")
                                self.system_status.add_log("Delta client confirmed online", "success")
                            if self.system_status.components.get("Delta API") != "Done":
                                self.system_status.update("Delta API", "Done")
                    
                    if websocket_client.delta_client and websocket_client.delta_client.is_connected:
                        # Check for price updates
                        if websocket_client.delta_client.latest_prices:
                            self.system_status.update_activity("Live Price Update")
                        
                        # Check for position processing
                        if current_time - last_price_check >= websocket_client.settings.POSITION_CHECK_INTERVAL:
                            last_price_check = current_time
                            self.system_status.update_activity("Position Check")
                        
                        # Check for analysis
                        if current_time - last_analysis_check >= websocket_client.settings.ANALYSIS_INTERVAL:
                            last_analysis_check = current_time
                            self.system_status.update_activity("Technical Analysis")
                    
                    # Check for activity updates from websocket server
                    if hasattr(websocket_client.websocket_server, 'last_activity_update'):
                        for activity, timestamp in websocket_client.websocket_server.last_activity_update.items():
                            self.system_status.last_activity[activity] = timestamp
                    
                    time.sleep(2)  # Check every 2 seconds for more responsive updates
                    
                except Exception as e:
                    logger.error(f"Error in activity monitor: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
    def stop(self):
        self._stop_event.set()

def run_system():
    """Run the trading system"""
    try:
        # Initialize system components
        system_status = SystemStatus()
        websocket_server = WebSocketServer()
        websocket_client = WebSocketClient(websocket_server)
        activity_monitor = ActivityMonitor(system_status)
        
        # Start components
        if not websocket_server.start():
            logger.error("Failed to start WebSocket server")
            return
        
        system_status.update("WebSocket Server", True)
        
        if not websocket_client.start():
            logger.error("Failed to start WebSocket client")
            websocket_server.stop()
            return
            
        # Wait for Delta client to be ready
        max_wait = 30  # Maximum wait time in seconds
        wait_start = time.time()
        while time.time() - wait_start < max_wait:
            if websocket_client.delta_client and websocket_client.delta_client.is_connected:
                system_status.update("Delta WebSocket", True)
                system_status.update("Delta API", True)
                system_status.update("Technical Analysis", True)
                system_status.update("Position Manager", True)
                system_status.is_ready = True
                logger.info("Trading system is ready - Delta client initialized")
                break
            time.sleep(1)
            
        if not system_status.is_ready:
            logger.error("Timeout waiting for Delta client to initialize")
            websocket_client.stop()
            websocket_server.stop()
            return
        
        # Start activity monitoring
        activity_monitor.start_monitoring(websocket_client)
        
        # Keep the main thread running
        try:
            while True:
                if not websocket_client.delta_client.is_connected:
                    logger.warning("Delta client disconnected, attempting to reconnect...")
                    if not websocket_client.delta_client.start():
                        logger.error("Failed to reconnect Delta client")
                        break
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down trading system...")
            activity_monitor.stop()
            websocket_client.stop()
            websocket_server.stop()
            logger.info("Trading system shutdown complete")
            
    except Exception as e:
        logger.error(f"Error running trading system: {e}")
        if 'websocket_client' in locals():
            websocket_client.stop()
        if 'websocket_server' in locals():
            websocket_server.stop()

def main():
    """Main application entry point"""
    try:
        # Initialize system status
        system_status = SystemStatus()
        settings = get_settings()
        
        with console.screen() as screen:
            # Create layout
            layout = Layout()
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=3)
            )
            
            layout["body"].split_row(
                Layout(name="config", ratio=1),
                Layout(name="status", ratio=1),
                Layout(name="activity", ratio=1)
            )
            
            # Header - Dynamic Online/Offline status
            def get_header():
                if system_status.is_online:
                    return Panel(
                        Text("🟢 ONLINE - Cryptocurrency Trading System", style="bold green", justify="center"),
                        style="bold green"
                    )
                else:
                    return Panel(
                        Text("🔴 OFFLINE - Cryptocurrency Trading System", style="bold red", justify="center"),
                        style="bold red"
                    )
            
            layout["header"].update(get_header())
            
            # Footer
            layout["footer"].update(
                Panel(
                    Text("Press Ctrl+C to stop the system", style="bold yellow", justify="center"),
                    style="bold red"
                )
            )
            
            def get_renderable():
                layout["header"].update(get_header())  # Update header dynamically
                layout["config"].update(Panel(system_status.get_config_table(), title="Configuration"))
                layout["status"].update(Panel(system_status.get_status_table(), title="System Status"))
                layout["activity"].update(Panel(system_status.get_activity_table(), title="Live Activity"))
                return layout
            
            with Live(get_renderable(), console=console, refresh_per_second=2) as live:
                # Initialize components in background
                def init_system():
                    try:
                        system_status.add_log("Starting system initialization...", "info")
                        
                        # Initialize MongoDB
                        system_status.add_log("Connecting to MongoDB...", "info")
                        mongodb_client = MongoDBClient()
                        if mongodb_client.test_connection():
                            system_status.update("MongoDB Connection", "Done")
                            system_status.add_log("MongoDB connected successfully", "success")
                        else:
                            system_status.update("MongoDB Connection", "Failed")
                            system_status.add_log("MongoDB connection failed - continuing anyway", "warning")
                        
                        # Initialize WebSocket server
                        system_status.add_log("Starting WebSocket server...", "info")
                        websocket_server = WebSocketServer()
                        if websocket_server.start():
                            system_status.update("WebSocket Server", "Done")
                            system_status.add_log(f"WebSocket server started on ws://{settings.WEBSOCKET_SERVER_HOST}:{settings.WEBSOCKET_SERVER_PORT}", "success")
                        else:
                            system_status.update("WebSocket Server", "Failed")
                            system_status.add_log("WebSocket server failed to start", "error")
                            return
                        
                        # Initialize WebSocket client
                        system_status.add_log("Starting WebSocket client...", "info")
                        websocket_client = WebSocketClient(websocket_server)
                        
                        # Initialize activity monitor
                        activity_monitor = ActivityMonitor(system_status)
                        
                        # Start WebSocket client (this will attempt to start Delta client)
                        if websocket_client.start():
                            system_status.add_log("WebSocket client started", "success")
                            
                            # Wait a bit for components to initialize
                            system_status.add_log("Waiting for components to initialize...", "info")
                            time.sleep(5)  # Increased wait time
                            
                            # Check Delta client status and mark all components as Done
                            if websocket_client.delta_client and websocket_client.delta_client.is_connected:
                                system_status.update("Delta WebSocket", "Done")
                                system_status.update("Delta API", "Done")
                                system_status.add_log("Delta client connected", "success")
                                # Set system ready flag
                                websocket_client.set_system_ready(True)
                                system_status.add_log("🎉 System is now ONLINE!", "success")
                            else:
                                system_status.add_log("Delta client not connected - will retry in background", "warning")
                                # Don't fail the entire system, just mark as not ready for now
                            
                            # Check technical analysis
                            if websocket_client.technical_analysis:
                                system_status.update("Technical Analysis", "Done")
                                system_status.add_log("Technical analysis ready", "success")
                            else:
                                system_status.update("Technical Analysis", "Failed")
                                system_status.add_log("Technical analysis not available", "warning")
                            
                            # Check position manager
                            if websocket_client.position_manager:
                                if websocket_client.position_manager.is_connected:
                                    system_status.update("Position Manager", "Done")
                                    system_status.add_log("Position manager ready", "success")
                                else:
                                    system_status.update("Position Manager", "Done")  # Mark as ready anyway
                                    system_status.add_log("Position manager connected with warnings", "warning")
                            else:
                                system_status.update("Position Manager", "Failed")
                                system_status.add_log("Position manager not available", "warning")
                            
                            # Start activity monitoring
                            activity_monitor.start_monitoring(websocket_client)
                            system_status.add_log("Activity monitoring started", "success")
                            
                            system_status.add_log("🎉 System initialization complete!", "success")
                            system_status.add_log("System is running - components will continue to connect in background", "info")
                            
                            # Keep running and monitor connection
                            last_delta_check = 0
                            last_status_update = 0
                            
                            while True:
                                current_time = time.time()
                                
                                # Update system status every 10 seconds
                                if current_time - last_status_update >= 10:
                                    last_status_update = current_time
                                    
                                    # Update all component statuses
                                    if websocket_server and hasattr(websocket_server, 'is_running') and websocket_server.is_running:
                                        if system_status.components["WebSocket Server"] != "Done":
                                            system_status.update("WebSocket Server", "Done")
                                    
                                    if mongodb_client and mongodb_client.test_connection():
                                        if system_status.components["MongoDB Connection"] != "Done":
                                            system_status.update("MongoDB Connection", "Done")
                                    
                                    if websocket_client.technical_analysis:
                                        if system_status.components["Technical Analysis"] != "Done":
                                            system_status.update("Technical Analysis", "Done")
                                    
                                    if websocket_client.position_manager:
                                        if system_status.components["Position Manager"] != "Done":
                                            system_status.update("Position Manager", "Done")
                                
                                # Check Delta client every 30 seconds
                                if current_time - last_delta_check >= 30:
                                    last_delta_check = current_time
                                    
                                    if websocket_client.delta_client:
                                        if websocket_client.delta_client.is_connected:
                                            if system_status.components.get("Delta WebSocket") != "Done":
                                                system_status.update("Delta WebSocket", "Done")
                                                system_status.update("Delta API", "Done")
                                                system_status.add_log("Delta client reconnected", "success")
                                                websocket_client.set_system_ready(True)
                                        else:
                                            if system_status.components.get("Delta WebSocket") == "Done":
                                                system_status.update("Delta WebSocket", "Failed")
                                                system_status.update("Delta API", "Failed")
                                                system_status.add_log("Delta client disconnected", "warning")
                                                websocket_client.set_system_ready(False)
                                
                                time.sleep(2)  # Check every 2 seconds for more responsive UI
                                
                        else:
                            system_status.add_log("WebSocket client failed to start", "error")
                            websocket_server.stop()
                            return
                                
                    except KeyboardInterrupt:
                        system_status.add_log("Shutting down system...", "warning")
                        if 'activity_monitor' in locals():
                            activity_monitor.stop()
                        if 'websocket_client' in locals():
                            websocket_client.stop()
                        if 'websocket_server' in locals():
                            websocket_server.stop()
                        system_status.add_log("System shutdown complete", "success")
                    except Exception as e:
                        system_status.add_log(f"Error in system initialization: {e}", "error")
                        logger.error(f"Error in system initialization: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                
                # Start system in background thread
                system_thread = threading.Thread(target=init_system)
                system_thread.daemon = True
                system_thread.start()
                
                # Handle graceful shutdown
                def signal_handler(signum, frame):
                    system_status.add_log("Shutting down system...", "warning")
                    stop_event.set()
                    raise KeyboardInterrupt
                
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                
                # Keep the main thread alive
                try:
                    while not stop_event.is_set():
                        time.sleep(0.1)
                except KeyboardInterrupt:
                    system_status.add_log("System shutdown complete!", "success")
                    
    except Exception as e:
        console.print(f"[bold red]Error in main: {e}[/bold red]")
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()