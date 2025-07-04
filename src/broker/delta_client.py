import logging
import json
import websocket
import threading
import time
from datetime import datetime
from typing import Dict, Optional, List
from src.config import get_settings
from src.system.message_formatter import MessageFormatter, MessageType
from src.data.technical_analysis import TechnicalAnalysis
from src.broker.position_manager import PositionManager

logger = logging.getLogger(__name__)

class DeltaBrokerClient:
    """Delta Exchange WebSocket client for real-time cryptocurrency data"""
    
    def __init__(self, websocket_server=None, position_manager=None, technical_analysis=None):
        """
        Initialize Delta Exchange WebSocket client
        
        Args:
            websocket_server: WebSocket server instance for sending messages
            position_manager: Position manager instance
            technical_analysis: Technical analysis instance
        """
        self.logger = logging.getLogger(__name__)
        self.websocket_server = websocket_server
        self.position_manager = position_manager
        self.technical_analysis = technical_analysis
        self.settings = get_settings()
        self.ws = None
        self.is_connected = False
        self.latest_prices: Dict[str, Dict] = {}
        self._stop_event = threading.Event()
        self._connection_thread = None
        self._price_check_timer = None
        self._analysis_timer = None
        
    def send_message(self, message: Dict):
        """Send message through WebSocket if available"""
        if self.websocket_server:
            self.websocket_server.queue_message(message)

    def log_message(self, message: str, level: str = "info"):
        """Send log message"""
        self.logger.log(getattr(logging, level.upper()), message)
        if self.websocket_server:
            self.send_message(
                MessageFormatter.format_log(message, level, "delta_client")
            )

    def connect(self) -> bool:
        """Connect to Delta Exchange WebSocket server"""
        try:
            self.ws = websocket.WebSocketApp(
                self.settings.DELTA_WEBSOCKET_URL,
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
            self.log_message(f"Delta Exchange WebSocket connection error: {e}", "error")
            return False

    def disconnect(self):
        """Disconnect from Delta Exchange WebSocket server"""
        self._stop_event.set()
        if self.ws:
            self.ws.close()
        if self._connection_thread:
            self._connection_thread.join(timeout=5.0)
        if self._price_check_timer:
            self._price_check_timer.cancel()
        if self._analysis_timer:
            self._analysis_timer.cancel()
        self.is_connected = False
        self.log_message("Disconnected from Delta Exchange WebSocket server", "info")

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Handle incoming Delta Exchange WebSocket messages"""
        try:
            message_json = json.loads(message)
            
            # Handle different message types from Delta Exchange
            if isinstance(message_json, dict):
                if message_json.get("type") == "v2/ticker":
                    data = message_json.get("data", {})
                    symbol = data.get("symbol")
                    mark_price = data.get("mark_price")
                    spot_price = data.get("spot_price")
                    last_price = data.get("last_price")
                    
                    # Get the best available price
                    price = mark_price or spot_price or last_price
                    
                    if price and symbol in self.settings.DEFAULT_SYMBOLS:
                        # Update latest prices
                        self.latest_prices[symbol] = {
                            "price": float(price),
                            "timestamp": datetime.now(),
                            "mark_price": float(mark_price) if mark_price else None,
                            "spot_price": float(spot_price) if spot_price else None,
                            "last_price": float(last_price) if last_price else None
                        }
                        
                elif message_json.get("type") == "error":
                    error_msg = message_json.get("message", "Unknown error")
                    self.log_message(f"Delta Exchange error: {error_msg}", "error")
                    
        except json.JSONDecodeError as e:
            self.log_message(f"Failed to parse message: {e}", "error")
        except Exception as e:
            self.log_message(f"Error processing message: {e}", "error")

    def on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """Handle WebSocket errors"""
        self.log_message(f"Delta Exchange WebSocket error: {error}", "error")
        self.is_connected = False
        if not self._stop_event.is_set():
            self._attempt_reconnect()

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """Handle WebSocket connection closure"""
        self.log_message(f"Delta Exchange WebSocket closed (Status: {close_status_code} - {close_msg})", "warning")
        self.is_connected = False
        if not self._stop_event.is_set():
            self._attempt_reconnect()

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        """Handle WebSocket connection open"""
        self.is_connected = True
        self.log_message("Connected to Delta Exchange WebSocket server", "info")
        
        # Subscribe to required channels
        self._subscribe_to_channels()

    def _subscribe_to_channels(self) -> None:
        """Subscribe to required Delta Exchange WebSocket channels"""
        try:
            # Subscribe to v2/ticker channel for all symbols at once
            subscribe_message = {
                "type": "subscribe",
                "payload": {
                    "channels": [
                        {
                            "name": "v2/ticker",
                            "symbols": self.settings.DEFAULT_SYMBOLS
                        }
                    ]
                }
            }
            self.ws.send(json.dumps(subscribe_message))
            self.log_message(f"Subscribed to Delta Exchange tickers: {', '.join(self.settings.DEFAULT_SYMBOLS)}", "info")
                
        except Exception as e:
            self.log_message(f"Error subscribing to Delta Exchange channels: {e}", "error")

    def _attempt_reconnect(self, max_attempts: int = 3, delay: int = 5) -> None:
        """
        Attempt to reconnect to Delta Exchange WebSocket server
        
        Args:
            max_attempts (int): Maximum number of reconnection attempts
            delay (int): Delay between attempts in seconds
        """
        attempts = 0
        while attempts < max_attempts and not self._stop_event.is_set():
            attempts += 1
            self.log_message(f"Attempting to reconnect ({attempts}/{max_attempts})...", "warning")
            
            try:
                if self.connect():
                    break
            except Exception as e:
                self.log_message(f"Reconnection attempt failed: {e}", "error")
            
            if attempts < max_attempts:
                time.sleep(delay)

    def check_positions_and_prices(self) -> None:
        """Check positions and send price updates"""
        try:
            if self.latest_prices:
                # Send price updates to WebSocket server
                self.send_message(
                    MessageFormatter.format_message(
                        MessageType.LIVE_PRICE,
                        {
                            "prices": self.get_latest_prices(),
                            "timestamp": datetime.now().isoformat()
                        },
                        "delta_client"
                    )
                )
                
                # Update positions if manager is available
                if self.position_manager:
                    for symbol, price_data in self.latest_prices.items():
                        self.position_manager.check_position(symbol, price_data["price"])
                
                # Log price updates
                for symbol, price_data in self.latest_prices.items():
                    self.log_message(
                        f"Current Price - {symbol}: ${price_data['price']:.2f}",
                        "info"
                    )
            
        except Exception as e:
            self.log_message(f"Error in position and price check: {e}", "error")
            
        finally:
            # Schedule next check if not stopped
            if not self._stop_event.is_set():
                self._price_check_timer = threading.Timer(10.0, self.check_positions_and_prices)
                self._price_check_timer.daemon = True
                self._price_check_timer.start()

    def run_technical_analysis(self) -> None:
        """Run technical analysis and send results"""
        try:
            if self.technical_analysis and self.latest_prices:
                for symbol in self.latest_prices:
                    analysis_results = self.technical_analysis.analyze_symbol(symbol)
                    if analysis_results:
                        self.send_message(
                            MessageFormatter.format_message(
                                MessageType.ANALYSIS,
                                {
                                    "symbol": symbol,
                                    "analysis": analysis_results,
                                    "timestamp": datetime.now().isoformat()
                                },
                                "delta_client"
                            )
                        )
                        
        except Exception as e:
            self.log_message(f"Error in technical analysis: {e}", "error")
            
        finally:
            # Schedule next analysis if not stopped
            if not self._stop_event.is_set():
                self._analysis_timer = threading.Timer(600.0, self.run_technical_analysis)  # 10 minutes
                self._analysis_timer.daemon = True
                self._analysis_timer.start()

    def get_latest_prices(self) -> Dict[str, Dict]:
        """Get latest prices for all symbols with additional data"""
        return {
            symbol: {
                "price": data["price"],
                "mark_price": data.get("mark_price"),
                "spot_price": data.get("spot_price"),
                "last_price": data.get("last_price"),
                "timestamp": data["timestamp"].isoformat()
            }
            for symbol, data in self.latest_prices.items()
        }

    def start(self) -> bool:
        """Start the Delta Exchange WebSocket client
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        self._stop_event.clear()
        if self.connect():
            # Wait for initial prices
            timeout = self.settings.WEBSOCKET_TIMEOUT
            start_time = time.time()
            while not self.latest_prices and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            if not self.latest_prices:
                self.log_message("Timeout waiting for initial prices", "error")
                return False
                
            # Start price and position checks
            self.check_positions_and_prices()
            
            # Start technical analysis if available
            if self.technical_analysis:
                self.run_technical_analysis()
                
            return True
        else:
            self.log_message("Failed to start Delta Exchange WebSocket client", "error")
            return False

    def stop(self) -> None:
        """Stop the Delta Exchange WebSocket client"""
        self._stop_event.set()
        self.disconnect()

    def test_connection(self) -> bool:
        """
        Test Delta Exchange WebSocket connection
        
        Returns:
            bool: True if connection test was successful
        """
        self.log_message("Testing Delta Exchange WebSocket connection...", "info")
        
        test_ws = websocket.WebSocketApp(
            self.settings.DELTA_WEBSOCKET_URL,
            on_open=lambda ws: self.log_message("Connection test successful", "info"),
            on_error=lambda ws, error: self.log_message(f"Connection test failed: {error}", "error"),
            on_close=lambda ws, code, msg: None
        )
        
        connection_thread = threading.Thread(target=test_ws.run_forever)
        connection_thread.daemon = True
        connection_thread.start()
        
        time.sleep(self.settings.WEBSOCKET_TIMEOUT)
        test_ws.close()
        
        return True 