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

def setup_logging():
    """Setup logging configuration"""
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(settings.LOG_FILE)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format=settings.LOG_FORMAT,
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

# Initialize logger at module level
logger = setup_logging()

# Create a stop event for graceful shutdown
stop_event = threading.Event()

def main():
    """Main application entry point"""
    try:
        logger.info("Starting trading bot...")
        
        # Initialize components
        settings = get_settings()
        mongodb_client = MongoDBClient()
        websocket_server = WebSocketServer()
        technical_analysis = TechnicalAnalysis(mongodb_client)
        position_manager = PositionManager(technical_analysis)
        
        # Initialize WebSocket client (which also creates DeltaClient)
        websocket_client = WebSocketClient(websocket_server)
        
        # Setup signal handlers
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal. Starting graceful shutdown...")
            
            # Set stop event first to prevent new operations
            stop_event.set()
            
            try:
                # Stop WebSocket client first (includes DeltaClient)
                logger.info("Stopping WebSocket client...")
                websocket_client.stop()
                
                # Stop WebSocket server
                logger.info("Stopping WebSocket server...")
                websocket_server.stop()
                
                # Close MongoDB connection
                logger.info("Closing MongoDB connection...")
                mongodb_client.disconnect()
                
                logger.info("Graceful shutdown completed.")
                sys.exit(0)
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
                sys.exit(1)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start WebSocket server first
        if not websocket_server.start():
            logger.error("Failed to start WebSocket server")
            return
            
        # Start WebSocket client (which will also start DeltaClient)
        if not websocket_client.start():
            logger.error("Failed to start WebSocket client")
            websocket_server.stop()
            return
            
        logger.info("Trading bot started successfully")
        
        # Keep main thread alive using threading.Event instead of signal.pause()
        while not stop_event.is_set():
            time.sleep(1)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()