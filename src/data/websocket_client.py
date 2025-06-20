import websocket
import json
import threading
import time
from datetime import datetime
from typing import Dict, Optional, Callable
from src.config import get_settings
from src.ui.console import ConsoleUI

class WebSocketClient:
    """WebSocket client for real-time cryptocurrency price data"""
    
    def __init__(self, ui: ConsoleUI):
        """
        Initialize WebSocket client
        
        Args:
            ui (ConsoleUI): Console UI instance for output
        """
        self.settings = get_settings()
        self.ui = ui
        self.websocket_url = self.settings.WEBSOCKET_URL
        self.ws: Optional[websocket.WebSocketApp] = None
        self.latest_prices: Dict[str, Dict] = {}
        self.connected = False
        self.price_timer: Optional[threading.Timer] = None
        self._stop_event = threading.Event()
    
    def on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """Handle WebSocket errors"""
        self.ui.print_error(f"WebSocket error: {error}")
        self.connected = False
        self._attempt_reconnect()

    def on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """Handle WebSocket connection closure"""
        self.ui.print_warning(f"WebSocket closed (Status: {close_status_code} - {close_msg})")
        self.connected = False
        if not self._stop_event.is_set():
            self._attempt_reconnect()

    def on_open(self, ws: websocket.WebSocketApp) -> None:
        """Handle WebSocket connection opening"""
        self.ui.print_success("WebSocket connection established")
        self.connected = True
        
        # Subscribe to price feeds
        payload = {
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
        ws.send(json.dumps(payload))
        self.ui.print_info(f"Subscribed to price feeds: {', '.join(self.settings.DEFAULT_SYMBOLS)}")

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Handle incoming WebSocket messages"""
        try:
            message_json = json.loads(message)
            
            if message_json.get("type") == "v2/ticker" and "symbol" in message_json:
                symbol = message_json["symbol"]
                price = message_json.get("mark_price") or message_json.get("close") or message_json.get("last_price")
                
                if price and symbol in self.settings.DEFAULT_SYMBOLS:
                    self.latest_prices[symbol] = {
                        "price": float(price),
                        "timestamp": datetime.now()
                    }
                    
        except json.JSONDecodeError as e:
            self.ui.print_error(f"Failed to parse message: {e}")
        except Exception as e:
            self.ui.print_error(f"Error processing message: {e}")

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
            self.ui.print_warning(f"Attempting to reconnect ({attempts}/{max_attempts})...")
            
            try:
                if self.connect():
                    self.ws.run_forever()
                    break
            except Exception as e:
                self.ui.print_error(f"Reconnection attempt failed: {e}")
            
            if attempts < max_attempts:
                time.sleep(delay)

    def schedule_price_updates(self) -> None:
        """Schedule periodic price updates"""
        if self.connected and not self._stop_event.is_set():
            self.ui.print_live_prices(self.latest_prices)
            self.price_timer = threading.Timer(
                self.settings.PRICE_UPDATE_INTERVAL,
                self.schedule_price_updates
            )
            self.price_timer.daemon = True
            self.price_timer.start()

    def connect(self) -> bool:
        """
        Establish WebSocket connection
        
        Returns:
            bool: True if connection was established successfully
        """
        try:
            self.ws = websocket.WebSocketApp(
                self.websocket_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            return True
        except Exception as e:
            self.ui.print_error(f"Failed to create WebSocket connection: {e}")
            return False

    def start(self) -> None:
        """Start the WebSocket connection and price updates"""
        self._stop_event.clear()
        if self.connect():
            threading.Timer(3.0, self.schedule_price_updates).start()
            
            try:
                self.ws.run_forever()
            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self.ui.print_error(f"Connection error: {e}")
                self.connected = False

    def stop(self) -> None:
        """Stop the WebSocket connection and timers"""
        self._stop_event.set()
        self.connected = False
        if self.price_timer:
            self.price_timer.cancel()
        if self.ws:
            self.ws.close()

    def test_connection(self) -> bool:
        """
        Test WebSocket connection
        
        Returns:
            bool: True if connection test was successful
        """
        self.ui.print_info("Testing WebSocket connection...")
        
        test_ws = websocket.WebSocketApp(
            self.websocket_url,
            on_open=lambda ws: self.ui.print_success("Connection test successful"),
            on_error=lambda ws, error: self.ui.print_error(f"Connection test failed: {error}"),
            on_close=lambda ws, code, msg: None
        )
        
        connection_thread = threading.Thread(target=test_ws.run_forever)
        connection_thread.daemon = True
        connection_thread.start()
        
        time.sleep(self.settings.WEBSOCKET_TIMEOUT)
        test_ws.close()
        
        return True 