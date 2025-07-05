import logging
import json
import websocket
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List
from src.system.message_formatter import MessageFormatter, MessageType
from src.config import get_settings
from src.broker.position_manager import PositionManager
from src.data.technical_analysis import TechnicalAnalysis
from src.data.mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)

class WebSocketClient:
    """WebSocket client for sending data to local WebSocket server"""
    
    def __init__(self, websocket_server=None):
        """
        Initialize WebSocket client
        
        Args:
            websocket_server: WebSocket server instance for sending messages
        """
        self.logger = logging.getLogger(__name__)
        self.websocket_server = websocket_server
        self.settings = get_settings()
        self.ws = None
        self.is_connected = False
        self._stop_event = threading.Event()
        self._connection_thread = None
        
        # Initialize components
        self.mongodb_client = MongoDBClient()
        self.technical_analysis = TechnicalAnalysis(self.mongodb_client)
        self.position_manager = PositionManager(self.technical_analysis)
        
        # Track last analysis time
        self._last_analysis_time = 0
    
    def send_message(self, message: Dict):
        """Send message through WebSocket if available"""
        if self.websocket_server:
            self.websocket_server.queue_message(message)

    def check_positions(self, current_prices: Dict[str, float]) -> None:
        """Check positions and send updates"""
        try:
            # Check positions
            positions_to_close = self.position_manager.check_stop_loss_and_targets(current_prices)
            
            # Get all positions with updated PNL
            positions = self.position_manager.get_all_positions()
            
            # Create position update message
            position_data = {
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "entry_price": pos.entry_price,
                        "current_price": current_prices.get(pos.symbol),
                        "quantity": pos.quantity,
                        "side": pos.side,
                        "pnl": pos.calculate_pnl(current_prices.get(pos.symbol, 0)),
                        "stop_loss": pos.stop_loss,
                        "take_profit": pos.take_profit,
                        "liquidation_price": pos.liquidation_price,
                        "margin_ratio": pos.calculate_margin_ratio(current_prices.get(pos.symbol, 0)),
                        "status": "CLOSING" if pos.symbol in positions_to_close else "OPEN",
                        "timestamp": datetime.now().isoformat()
                    }
                    for pos in positions
                ],
                "prices": {
                    symbol: {"price": price, "timestamp": datetime.now().isoformat()}
                    for symbol, price in current_prices.items()
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Send position update
            self.send_message(
                MessageFormatter.format_message(
                    MessageType.POSITIONS,
                    position_data,
                    "trading"
                )
            )
            
        except Exception as e:
            self.logger.error(f"Error checking positions: {e}")

    def run_analysis(self, current_prices: Dict[str, float]) -> None:
        """Run technical analysis and send results"""
        try:
            # Check if it's time to run analysis (every 10 minutes)
            current_time = time.time()
            if current_time - self._last_analysis_time >= self.settings.ANALYSIS_INTERVAL:
                self._last_analysis_time = current_time
                
                # Run analysis for each symbol
                analysis_results = {}
                for symbol in current_prices:
                    try:
                        # Get analysis results
                        result = self.technical_analysis.analyze_symbol(symbol)
                        if result:
                            analysis_results[symbol] = result
                            
                    except Exception as e:
                        self.logger.error(f"Error analyzing {symbol}: {e}")
                
                if analysis_results:
                    # Send analysis results
                    self.send_message(
                        MessageFormatter.format_message(
                            MessageType.ANALYSIS,
                            {
                                "analysis": analysis_results,
                                "timestamp": datetime.now().isoformat()
                            },
                            "trading"
                        )
                    )
                    
        except Exception as e:
            self.logger.error(f"Error in technical analysis: {e}")

    def connect(self) -> bool:
        """Connect to WebSocket server"""
        try:
            self.ws = websocket.WebSocketApp(
                self.settings.WEBSOCKET_URL,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            # Start WebSocket connection in a separate thread
            self._connection_thread = threading.Thread(target=self.ws.run_forever)
            self._connection_thread.daemon = True
            self._connection_thread.start()
            
            # Wait for connection
            timeout = self.settings.WEBSOCKET_TIMEOUT
            start_time = time.time()
            while not self.is_connected and time.time() - start_time < timeout:
                time.sleep(0.1)
            
            return self.is_connected
            
        except Exception as e:
            self.logger.error(f"WebSocket connection error: {e}")
            return False

    def disconnect(self):
        """Disconnect from WebSocket server"""
        self._stop_event.set()
        if self.ws:
            self.ws.close()
        if self._connection_thread:
            self._connection_thread.join(timeout=5.0)
        self.is_connected = False

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Handle incoming WebSocket messages"""
        try:
            message_json = json.loads(message)
            
            # Forward all messages to WebSocket server
            if self.websocket_server:
                self.send_message(message_json)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """Handle WebSocket errors"""
        self.logger.error(f"WebSocket error: {error}")
        self.is_connected = False
        if not self._stop_event.is_set():
            self._attempt_reconnect()

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """Handle WebSocket connection closure"""
        self.is_connected = False
        if not self._stop_event.is_set():
            self._attempt_reconnect()

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        """Handle WebSocket connection open"""
        self.is_connected = True

    def _attempt_reconnect(self, max_attempts: int = 3, delay: int = 5) -> None:
        """
        Attempt to reconnect to WebSocket server
        
        Args:
            max_attempts (int): Maximum number of reconnection attempts
            delay (int): Delay between attempts in seconds
        """
        attempts = 0
        while attempts < max_attempts and not self._stop_event.is_set():
            attempts += 1
            try:
                if self.connect():
                    break
            except Exception as e:
                self.logger.error(f"Reconnection attempt failed: {e}")
            
            if attempts < max_attempts:
                time.sleep(delay)

    def process_market_data(self) -> None:
        """Process market data in a loop"""
        while not self._stop_event.is_set():
            try:
                # Get current prices (you need to implement this based on your data source)
                current_prices = {
                    symbol: 0.0  # Replace with actual price data
                    for symbol in self.settings.DEFAULT_SYMBOLS
                }
                
                # Check positions and send updates
                self.check_positions(current_prices)
                
                # Run technical analysis if needed
                self.run_analysis(current_prices)
                
                # Sleep for 1 second
                time.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error processing market data: {e}")
                time.sleep(1)  # Sleep on error to prevent tight loop

    def start(self) -> bool:
        """Start the WebSocket client
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        self._stop_event.clear()
        if self.connect():
            # Start market data processing in a separate thread
            processing_thread = threading.Thread(target=self.process_market_data)
            processing_thread.daemon = True
            processing_thread.start()
            return True
        return False

    def stop(self) -> None:
        """Stop the WebSocket client"""
        self._stop_event.set()
        self.disconnect()

    def test_connection(self) -> bool:
        """
        Test WebSocket connection
        
        Returns:
            bool: True if connection test was successful
        """
        try:
            test_ws = websocket.WebSocketApp(
                self.settings.WEBSOCKET_URL,
                on_open=lambda ws: None,
                on_error=lambda ws, error: None,
                on_close=lambda ws, code, msg: None
            )
            
            connection_thread = threading.Thread(target=test_ws.run_forever)
            connection_thread.daemon = True
            connection_thread.start()
            
            time.sleep(self.settings.WEBSOCKET_TIMEOUT)
            test_ws.close()
            
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False 