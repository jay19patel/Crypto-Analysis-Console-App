#!/usr/bin/env python3
"""
Real-time Market Data Client with Delta Exchange WebSocket Integration
Provides live market data with execution time tracking and proper logging
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Callable, List
import random
import os

# Import websocket-client library
import websocket
from websocket import WebSocketApp

from src.config import get_settings

class RealTimeMarketData:
    """Real-time Market Data Client with Delta Exchange WebSocket Integration"""
    
    def __init__(self, price_callback: Optional[Callable] = None):
        """Initialize market data client"""
        # Initialize logger
        self.logger = logging.getLogger("market_data")
        self.price_callback = price_callback
        self.settings = get_settings()
        
        # Real-time price storage with thread safety
        self.live_prices: Dict[str, Dict] = {}
        self.price_lock = threading.Lock()
                
        # WebSocket connection management
        self.ws = None
        self.is_connected = False
        self.connection_attempts = 0
        self.max_connection_attempts = 5  # Default retry attempts
        self.reconnect_delay = 5  # Default reconnect delay in seconds
        self.connection_timeout = self.settings.WEBSOCKET_TIMEOUT
        
        # Threading control
        self._price_thread = None
        self._websocket_thread = None
        self._stop_event = threading.Event()
        
        # Performance tracking
        self._update_count = 0
        self._start_time = time.time()
        self._last_heartbeat = time.time()
        self._heartbeat_interval = 30  # seconds

    def start(self) -> bool:
        """Start real-time market data system"""
        try:
            start_time = time.time()
            self.logger.info("INFO - [MarketData] System | Starting Real-time Market Data System")
            
            # Reset state
            self._stop_event.clear()
            self._start_time = time.time()
            self._last_heartbeat = time.time()
            self.connection_attempts = 0
            
            # Start WebSocket connection
            self._start_websocket_connection()
            
            # Wait for initial connection with timeout
            timeout = self.connection_timeout
            while not self.is_connected and timeout > 0:
                if self.connection_attempts >= self.max_connection_attempts:
                    self.logger.error("ERROR - [MarketData] Connection | Max connection attempts reached")
                    return False
                time.sleep(0.5)
                timeout -= 0.5
            
            execution_time = time.time() - start_time
            if self.is_connected:
                self.logger.info(f"INFO - [MarketData] Connection | WebSocket connected successfully (Time: {execution_time:.3f}s)")
                return True
            else:
                self.logger.error(f"ERROR - [MarketData] Connection | Failed to establish WebSocket connection (Time: {execution_time:.3f}s)")
                return False
                
        except Exception as e:
            self.logger.error(f"ERROR - [MarketData] System | Startup failed: {str(e)}")
            return False
    
    def stop(self) -> None:
        """Stop market data system"""
        try:
            start_time = time.time()
            self.logger.info("INFO - [MarketData] System | Stopping Market Data System")
            
            self._stop_event.set()
            
            if self.ws:
                self.ws.close()
            
            # Wait for threads
            for thread in [self._price_thread, self._websocket_thread]:
                if thread and thread.is_alive():
                    thread.join(timeout=2.0)
            
            self.is_connected = False
            execution_time = time.time() - start_time
            self.logger.info(f"INFO - [MarketData] System | System stopped successfully (Time: {execution_time:.3f}s)")
            
        except Exception as e:
            self.logger.error(f"ERROR - [MarketData] System | Shutdown failed: {str(e)}")

    def get_live_prices(self) -> Dict[str, Dict]:
        """Get current live prices (thread-safe)"""
        with self.price_lock:
            return self.live_prices.copy()
    
    def get_price(self, symbol: str) -> float:
        """Get current price for specific symbol"""
        with self.price_lock:
            return self.live_prices.get(symbol, {}).get("price", 0.0)
    
    def get_performance_stats(self) -> Dict[str, any]:
        """Get real-time performance statistics"""
        uptime = time.time() - self._start_time
        return {
            "status": "connected" if self.is_connected else "disconnected",
            "uptime_seconds": round(uptime, 2),
            "update_count": self._update_count,
            "updates_per_second": round(self._update_count / uptime, 2) if uptime > 0 else 0,
            "active_symbols": len(self.live_prices),
            "last_update": datetime.now(timezone.utc).isoformat()
        }

    def _start_websocket_connection(self) -> None:
        """Start WebSocket connection in separate thread"""
        self._websocket_thread = threading.Thread(target=self._websocket_connection_loop, daemon=True)
        self._websocket_thread.start()

    def _websocket_connection_loop(self) -> None:
        """WebSocket connection management loop"""
        while not self._stop_event.is_set():
            try:
                start_time = time.time()
                self.logger.info("INFO - [MarketData] WebSocket | Establishing connection")
                
                # Initialize WebSocket connection with proper error handling
                websocket.enableTrace(False)  # Disable debug tracing
                self.ws = WebSocketApp(
                    "wss://socket.india.delta.exchange",  # Delta Exchange WebSocket URL
                    on_open=self._on_websocket_open,
                    on_message=self._on_websocket_message,
                    on_error=self._on_websocket_error,
                    on_close=self._on_websocket_close,
                    on_ping=self._on_websocket_ping,
                    on_pong=self._on_websocket_pong
                )
                
                # Connect with timeout and heartbeat
                self.ws.run_forever(
                    ping_interval=self._heartbeat_interval,
                    ping_timeout=10,
                    reconnect=3  # Auto-reconnect up to 3 times
                )
                
                if self._stop_event.is_set():
                    break
                
                # Connection lost - attempt reconnect
                self.is_connected = False
                self.connection_attempts += 1
                
                execution_time = time.time() - start_time
                self.logger.warning(
                    f"WARN - [MarketData] WebSocket | Connection lost, attempt {self.connection_attempts} "
                    f"of {self.max_connection_attempts} (Time: {execution_time:.3f}s)"
                )
                
                if self.connection_attempts >= self.max_connection_attempts:
                    self.logger.error("ERROR - [MarketData] WebSocket | Max reconnection attempts reached")
                    break
                    
                time.sleep(self.reconnect_delay)
                
            except Exception as e:
                self.logger.error(f"ERROR - [MarketData] WebSocket | Connection error: {str(e)}")
                time.sleep(self.reconnect_delay)
    
    def _on_websocket_open(self, ws: WebSocketApp) -> None:
        """Handle WebSocket connection open"""
        try:
            start_time = time.time()
            self.logger.info("INFO - [MarketData] WebSocket | Connection established")
            
            # Reset connection attempts on successful connection
            self.connection_attempts = 0
            self._last_heartbeat = time.time()
            
            # Subscribe to market data using Delta Exchange format
            subscribe_msg = {
                "type": "subscribe",
                "payload": {
                    "channels": [
                        {
                            "name": "v2/ticker",
                            "symbols": [
                                "BTCUSD",
                                "ETHUSD"
                            ]
                        }
                    ]
                }
            }
            
            self.logger.info(f"INFO - [MarketData] WebSocket | Sending subscription message: {json.dumps(subscribe_msg)}")
            ws.send(json.dumps(subscribe_msg))
            self.is_connected = True
            
            execution_time = time.time() - start_time
            self.logger.info(
                f"INFO - [MarketData] WebSocket | Subscribed to market data for ['BTCUSD', 'ETHUSD'] "
                f"(Time: {execution_time:.3f}s)"
            )
                
        except Exception as e:
            self.logger.error(f"ERROR - [MarketData] WebSocket | Subscription failed: {str(e)}")
            ws.close()
    
    def _on_websocket_message(self, ws: WebSocketApp, message: str) -> None:
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            
            # Debug logging to see what data we're receiving
            self.logger.debug(f"DEBUG - [MarketData] WebSocket | Received message: {data}")
            
            # Update heartbeat time for any valid message
            self._last_heartbeat = time.time()
            
            # Process market data (Delta Exchange format)
            if "type" in data and data["type"] == "v2/ticker":
                # Keep the original symbol format (BTCUSD, ETHUSD) to match strategy expectations
                symbol = data["symbol"]  # Use original format from Delta Exchange
                self.logger.info(f"📊 Received ticker data for {symbol} - Price: {data.get('mark_price', 'N/A')}")
                with self.price_lock:
                    # Extract all available fields from the message
                    price_update = {
                        # Basic price information
                        "price": float(data.get("mark_price", 0)),
                        "mark_price": float(data.get("mark_price", 0)),
                        "spot_price": float(data.get("spot_price", 0)) if data.get("spot_price") else None,
                        
                        # Volume and turnover
                        "volume": float(data.get("volume", 0)),
                        "turnover": float(data.get("turnover", 0)),
                        "turnover_usd": float(data.get("turnover_usd", 0)),
                        
                        # Price levels
                        "high": float(data.get("high", 0)),
                        "low": float(data.get("low", 0)),
                        "open": float(data.get("open", 0)),
                        "close": float(data.get("close", 0)),
                        
                        # Open Interest
                        "open_interest": float(data.get("oi", 0)),
                        "oi_value": float(data.get("oi_value", 0)),
                        "oi_contracts": float(data.get("oi_contracts", 0)),
                        "oi_value_usd": float(data.get("oi_value_usd", 0)),
                        "oi_change_usd_6h": float(data.get("oi_change_usd_6h", 0)),
                        
                        # Funding and basis
                        "funding_rate": float(data.get("funding_rate", 0)) if data.get("funding_rate") else None,
                        "mark_basis": float(data.get("mark_basis", 0)) if data.get("mark_basis") else None,
                        
                        # Price changes
                        "mark_change_24h": float(data.get("mark_change_24h", 0)),
                        
                        # Contract details
                        "contract_type": data.get("contract_type"),
                        "underlying_asset_symbol": data.get("underlying_asset_symbol"),
                        "turnover_symbol": data.get("turnover_symbol"),
                        "oi_value_symbol": data.get("oi_value_symbol"),
                        "description": data.get("description"),
                        "product_id": data.get("product_id"),
                        
                        # Margin and tick size
                        "initial_margin": float(data.get("initial_margin", 0)) if data.get("initial_margin") else None,
                        "tick_size": float(data.get("tick_size", 0)) if data.get("tick_size") else None,
                        
                        # Price bands
                        "price_band_lower": float(data.get("price_band", {}).get("lower_limit", 0)) if data.get("price_band") else None,
                        "price_band_upper": float(data.get("price_band", {}).get("upper_limit", 0)) if data.get("price_band") else None,
                        
                        # Quotes (order book data)
                        "best_bid": float(data.get("quotes", {}).get("best_bid", 0)) if data.get("quotes") else None,
                        "best_ask": float(data.get("quotes", {}).get("best_ask", 0)) if data.get("quotes") else None,
                        "bid_size": float(data.get("quotes", {}).get("bid_size", 0)) if data.get("quotes") else None,
                        "ask_size": float(data.get("quotes", {}).get("ask_size", 0)) if data.get("quotes") else None,
                        "mark_iv": float(data.get("quotes", {}).get("mark_iv", 0)) if data.get("quotes") else None,
                        
                        # Metadata
                        "size": float(data.get("size", 0)),
                        "tags": data.get("tags", []),
                        "time": data.get("time"),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        
                        # Greeks (if available)
                        "greeks": data.get("greeks")
                    }
                    self.live_prices[symbol] = price_update
                    self._update_count += 1
                    
                    self.logger.debug(f"✅ Price update stored for {symbol}: ${price_update['price']:.2f}")
                    
                    # Notify callback with current prices
                    if self.price_callback:
                        try:
                            self.price_callback(self.live_prices)
                            self.logger.debug(f"📡 Price callback executed successfully for {symbol}")
                        except Exception as callback_error:
                            self.logger.error(f"❌ Error in price callback: {callback_error}")
                    else:
                        self.logger.warning("⚠️ No price callback registered")
                
        except json.JSONDecodeError as e:
            self.logger.warning(f"WARN - [MarketData] WebSocket | Invalid message format: {str(e)}")
        except Exception as e:
            self.logger.error(f"ERROR - [MarketData] WebSocket | Message processing error: {str(e)}")
            # Add more detailed error information
            self.logger.error(f"ERROR - [MarketData] WebSocket | Message content: {message[:200]}...")
    
    def _on_websocket_error(self, ws: WebSocketApp, error: Exception) -> None:
        """Handle WebSocket errors"""
        self.logger.error(f"ERROR - [MarketData] WebSocket | Error occurred: {str(error)}")
        
    def _on_websocket_close(self, ws: WebSocketApp, close_status_code: int, close_msg: str) -> None:
        """Handle WebSocket connection close"""
        self.logger.warning(f"WARN - [MarketData] WebSocket | Connection closed: {close_status_code} - {close_msg}")
        self.is_connected = False
        
    def _on_websocket_ping(self, ws: WebSocketApp, message: bytes) -> None:
        """Handle WebSocket ping"""
        self._last_heartbeat = time.time()
        
    def _on_websocket_pong(self, ws: WebSocketApp, message: bytes) -> None:
        """Handle WebSocket pong"""
        self._last_heartbeat = time.time()

    def _format_symbol(self, symbol: str) -> str:
        """Format symbol for Delta Exchange WebSocket subscription"""
        # Convert BTC-USD to BTCUSD
        return symbol.replace("-", "").replace("USD", "")
