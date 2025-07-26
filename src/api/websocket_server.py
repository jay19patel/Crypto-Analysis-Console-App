"""
Real-time WebSocket Server for Trading System Frontend Integration
Broadcasts live prices, positions, notifications, and strategy signals to connected clients
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import weakref

import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed, ConnectionClosedError, ConnectionClosedOK

from src.config import get_settings
from src.database.schemas import MarketData, TradingSignal


class MessageType(Enum):
    """WebSocket message types"""
    LIVE_PRICES = "live_prices"
    POSITIONS = "positions"
    NOTIFICATIONS = "notifications"
    STRATEGY_SIGNALS = "strategy_signals"
    ACCOUNT_SUMMARY = "account_summary"
    SYSTEM_STATUS = "system_status"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    SUBSCRIPTION = "subscription"
    UNSUBSCRIPTION = "unsubscription"


@dataclass
class WebSocketMessage:
    """WebSocket message structure"""
    type: str
    data: Dict[str, Any]
    timestamp: str
    message_id: str

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(asdict(self), default=str)


@dataclass
class ClientConnection:
    """Client connection management"""
    websocket: WebSocketServerProtocol
    client_id: str
    connected_at: datetime
    subscriptions: Set[str]
    last_heartbeat: float
    ip_address: str
    user_agent: Optional[str] = None
    authenticated: bool = False

    def is_alive(self) -> bool:
        """Check if connection is still alive"""
        try:
            # Check if websocket has closed attribute
            if hasattr(self.websocket, 'closed'):
                websocket_alive = not self.websocket.closed
            elif hasattr(self.websocket, 'open'):
                # Fallback for different websocket types  
                websocket_alive = self.websocket.open
            else:
                # If neither closed nor open attribute exists, check connection state
                websocket_alive = True
            
            # Check heartbeat timeout (increase timeout to 120 seconds for better stability)
            heartbeat_alive = (time.time() - self.last_heartbeat) < 120
            
            return websocket_alive and heartbeat_alive
            
        except (AttributeError, Exception) as e:
            # Log the specific error for debugging
            logger = logging.getLogger("websocket_server")
            logger.debug(f"Connection check failed for websocket {type(self.websocket)}: {e}")
            # If any error occurs, consider connection dead
            return False


class WebSocketServer:
    """Real-time WebSocket server for trading system frontend integration"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        """Initialize WebSocket server"""
        self.host = host
        self.port = port
        self.settings = get_settings()
        self.logger = logging.getLogger("websocket_server")
        
        # Client connection management
        self.clients: Dict[str, ClientConnection] = {}
        self.client_lock = asyncio.Lock()
        
        # Message queuing for offline clients
        self.message_queue: Dict[str, List[WebSocketMessage]] = {}
        self.max_queue_size = 100
        
        # Server state
        self.server = None
        self.running = False
        self.start_time = time.time()
        
        # Rate limiting
        self.rate_limits: Dict[str, Dict[str, float]] = {}
        self.max_messages_per_minute = 60
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "uptime": 0
        }
        
        # Heartbeat task
        self.heartbeat_task = None
        self.cleanup_task = None
        
        self.logger.info(f"WebSocket server initialized on {host}:{port}")

    async def start(self) -> bool:
        """Start WebSocket server"""
        try:
            self.logger.info(f"🚀 Starting WebSocket server on {self.host}:{self.port}")
            
            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_client_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
                max_size=1024 * 1024,  # 1MB max message size
                max_queue=32,
                compression=None  # Disable compression for better performance
            )
            
            self.running = True
            
            # Start background tasks
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.logger.info("✅ WebSocket server started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start WebSocket server: {e}")
            return False

    async def stop(self):
        """Stop WebSocket server"""
        try:
            self.logger.info("🛑 Stopping WebSocket server")
            self.running = False
            
            # Cancel background tasks
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
            if self.cleanup_task:
                self.cleanup_task.cancel()
            
            # Close all client connections
            await self._close_all_clients()
            
            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            self.logger.info("✅ WebSocket server stopped")
            
        except Exception as e:
            self.logger.error(f"❌ Error stopping WebSocket server: {e}")

    async def _handle_client_connection(self, websocket: WebSocketServerProtocol, path: str = "/"):
        """Handle new client connection"""
        client_id = str(uuid.uuid4())
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        
        try:
            self.logger.info(f"🔌 New client connected: {client_id} from {client_ip}")
            
            # Create client connection
            client = ClientConnection(
                websocket=websocket,
                client_id=client_id,
                connected_at=datetime.now(timezone.utc),
                subscriptions=set(),
                last_heartbeat=time.time(),
                ip_address=client_ip,
                authenticated=False  # Implement authentication if needed
            )
            
            # Add to clients
            async with self.client_lock:
                self.clients[client_id] = client
                self.stats["total_connections"] += 1
                self.stats["active_connections"] += 1
            
            # Send welcome message
            await self._send_message_to_client(
                client_id,
                MessageType.SYSTEM_STATUS,
                {
                    "status": "connected",
                    "client_id": client_id,
                    "server_time": datetime.now(timezone.utc).isoformat(),
                    "available_subscriptions": [msg_type.value for msg_type in MessageType]
                }
            )
            
            # Handle client messages
            await self._handle_client_messages(client)
            
        except ConnectionClosed:
            self.logger.info(f"🔌 Client {client_id} disconnected normally")
        except Exception as e:
            self.logger.error(f"❌ Error handling client {client_id}: {e}")
        finally:
            # Clean up client
            await self._remove_client(client_id)

    async def _handle_client_messages(self, client: ClientConnection):
        """Handle messages from client"""
        try:
            async for message in client.websocket:
                try:
                    # Update heartbeat
                    client.last_heartbeat = time.time()
                    
                    # Rate limiting check
                    if not self._check_rate_limit(client.client_id):
                        await self._send_error_to_client(
                            client.client_id,
                            "rate_limit_exceeded",
                            "Too many messages per minute"
                        )
                        continue
                    
                    # Parse message
                    data = json.loads(message)
                    
                    # Handle different message types
                    if data.get("type") == "subscribe":
                        await self._handle_subscription(client, data.get("channels", []))
                    elif data.get("type") == "unsubscribe":
                        await self._handle_unsubscription(client, data.get("channels", []))
                    elif data.get("type") == "ping":
                        await self._send_message_to_client(
                            client.client_id,
                            MessageType.HEARTBEAT,
                            {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}
                        )
                    else:
                        self.logger.warning(f"Unknown message type from client {client.client_id}: {data.get('type')}")
                    
                except json.JSONDecodeError:
                    await self._send_error_to_client(
                        client.client_id,
                        "invalid_json",
                        "Invalid JSON message format"
                    )
                except Exception as e:
                    self.logger.error(f"Error processing message from client {client.client_id}: {e}")
                    await self._send_error_to_client(
                        client.client_id,
                        "processing_error",
                        str(e)
                    )
                    
        except ConnectionClosed:
            pass  # Normal disconnection
        except Exception as e:
            self.logger.error(f"Error in client message handler: {e}")

    async def _handle_subscription(self, client: ClientConnection, channels: List[str]):
        """Handle client subscription to channels"""
        valid_channels = {msg_type.value for msg_type in MessageType}
        
        for channel in channels:
            if channel in valid_channels:
                client.subscriptions.add(channel)
                self.logger.info(f"Client {client.client_id} subscribed to {channel}")
            else:
                await self._send_error_to_client(
                    client.client_id,
                    "invalid_channel",
                    f"Channel '{channel}' does not exist"
                )
        
        # Send subscription confirmation
        await self._send_message_to_client(
            client.client_id,
            MessageType.SUBSCRIPTION,
            {
                "subscribed_channels": list(client.subscriptions),
                "available_channels": list(valid_channels)
            }
        )

    async def _handle_unsubscription(self, client: ClientConnection, channels: List[str]):
        """Handle client unsubscription from channels"""
        for channel in channels:
            client.subscriptions.discard(channel)
            self.logger.info(f"Client {client.client_id} unsubscribed from {channel}")
        
        # Send unsubscription confirmation
        await self._send_message_to_client(
            client.client_id,
            MessageType.UNSUBSCRIPTION,
            {
                "unsubscribed_channels": channels,
                "remaining_subscriptions": list(client.subscriptions)
            }
        )

    async def _send_message_to_client(self, client_id: str, message_type: MessageType, data: Dict[str, Any]):
        """Send message to specific client"""
        try:
            client = self.clients.get(client_id)
            if not client:
                return False
            
            # Check if websocket is closed safely
            try:
                if hasattr(client.websocket, 'closed') and client.websocket.closed:
                    return False
            except AttributeError:
                # Websocket object doesn't have closed attribute, assume it's alive for now
                pass
            
            # Check if client is subscribed to this message type
            if message_type.value not in client.subscriptions and message_type not in [
                MessageType.SYSTEM_STATUS, MessageType.ERROR, MessageType.HEARTBEAT,
                MessageType.SUBSCRIPTION, MessageType.UNSUBSCRIPTION
            ]:
                return False
            
            message = WebSocketMessage(
                type=message_type.value,
                data=data,
                timestamp=datetime.now(timezone.utc).isoformat(),
                message_id=str(uuid.uuid4())
            )
            
            await client.websocket.send(message.to_json())
            self.stats["messages_sent"] += 1
            return True
            
        except (ConnectionClosed, ConnectionClosedError, ConnectionClosedOK):
            # Client disconnected
            await self._remove_client(client_id)
            return False
        except Exception as e:
            self.logger.error(f"Error sending message to client {client_id}: {e}")
            self.stats["messages_failed"] += 1
            return False

    async def _send_error_to_client(self, client_id: str, error_code: str, error_message: str):
        """Send error message to client"""
        await self._send_message_to_client(
            client_id,
            MessageType.ERROR,
            {
                "error_code": error_code,
                "error_message": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

    async def broadcast_live_prices(self, live_prices: Dict[str, Dict]):
        """Broadcast live price updates to all subscribed clients"""
        if not live_prices:
            return
        
        formatted_data = {}
        for symbol, price_data in live_prices.items():
            formatted_data[symbol] = {
                "price": price_data.get("price", 0.0),
                "timestamp": price_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "volume": price_data.get("volume", 0.0),
                "change_24h": price_data.get("mark_change_24h", 0.0)
            }
        
        await self._broadcast_to_subscribers(MessageType.LIVE_PRICES, formatted_data)

    async def broadcast_positions_update(self, positions: List[Dict]):
        """Broadcast position updates to all subscribed clients"""
        formatted_positions = {}
        
        for position in positions:
            if position.get("status") == "open":
                formatted_positions[position["id"]] = {
                    "symbol": position["symbol"],
                    "side": position["position_type"],
                    "size": position["quantity"],
                    "entry_price": position["entry_price"],
                    "current_price": position.get("current_price", position["entry_price"]),
                    "pnl": position["pnl"],
                    "pnl_percentage": position["pnl_percentage"],
                    "unrealized_pnl": position["pnl"]
                }
        
        await self._broadcast_to_subscribers(MessageType.POSITIONS, formatted_positions)

    async def broadcast_notification(self, notification_id: str, message: str, level: str = "info"):
        """Broadcast notification to all subscribed clients"""
        notification_data = {
            "id": notification_id,
            "message": message,
            "level": level,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._broadcast_to_subscribers(MessageType.NOTIFICATIONS, notification_data)

    async def broadcast_strategy_signal(self, signal: TradingSignal):
        """Broadcast strategy signal to all subscribed clients"""
        signal_data = {
            "strategy_name": signal.strategy_name,
            "symbol": signal.symbol,
            "signal": signal.signal.value if hasattr(signal.signal, 'value') else str(signal.signal),
            "confidence": signal.confidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._broadcast_to_subscribers(MessageType.STRATEGY_SIGNALS, signal_data)

    async def broadcast_account_summary(self, account_summary: Dict):
        """Broadcast account summary to all subscribed clients"""
        await self._broadcast_to_subscribers(MessageType.ACCOUNT_SUMMARY, account_summary)

    async def _broadcast_to_subscribers(self, message_type: MessageType, data: Dict[str, Any]):
        """Broadcast message to all clients subscribed to the message type"""
        if not self.clients:
            return
        
        # Get clients subscribed to this message type
        subscribed_clients = [
            client_id for client_id, client in self.clients.items()
            if message_type.value in client.subscriptions and client.is_alive()
        ]
        
        if not subscribed_clients:
            return
        
        # Send to all subscribed clients concurrently
        tasks = [
            self._send_message_to_client(client_id, message_type, data)
            for client_id in subscribed_clients
        ]
        
        # Execute all sends concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log failed sends
        failed_count = sum(1 for result in results if isinstance(result, Exception) or result is False)
        if failed_count > 0:
            self.logger.warning(f"Failed to send {message_type.value} to {failed_count} clients")

    async def _heartbeat_loop(self):
        """Background heartbeat loop"""
        while self.running:
            try:
                # Send heartbeat to all connected clients
                current_time = time.time()
                
                async with self.client_lock:
                    for client_id, client in list(self.clients.items()):
                        if not client.is_alive():
                            self.logger.info(f"Client {client_id} failed heartbeat check")
                            await self._remove_client(client_id)
                        elif MessageType.HEARTBEAT.value in client.subscriptions:
                            await self._send_message_to_client(
                                client_id,
                                MessageType.HEARTBEAT,
                                {
                                    "server_time": datetime.now(timezone.utc).isoformat(),
                                    "uptime": current_time - self.start_time
                                }
                            )
                
                await asyncio.sleep(30)  # Heartbeat every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while self.running:
            try:
                # Clean up disconnected clients
                async with self.client_lock:
                    disconnected_clients = [
                        client_id for client_id, client in self.clients.items()
                        if not client.is_alive()
                    ]
                    
                    for client_id in disconnected_clients:
                        await self._remove_client(client_id)
                
                # Clean up old rate limit data
                current_time = time.time()
                for client_id in list(self.rate_limits.keys()):
                    if client_id not in self.clients:
                        del self.rate_limits[client_id]
                
                # Update stats
                self.stats["uptime"] = current_time - self.start_time
                self.stats["active_connections"] = len(self.clients)
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(10)

    async def _remove_client(self, client_id: str):
        """Remove client from active connections"""
        async with self.client_lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                try:
                    # Check if websocket has closed attribute before accessing it
                    if hasattr(client.websocket, 'closed') and not client.websocket.closed:
                        await client.websocket.close()
                    elif hasattr(client.websocket, 'close'):
                        # Try to close regardless if we can't check status
                        await client.websocket.close()
                except Exception as e:
                    self.logger.debug(f"Error closing websocket for client {client_id}: {e}")
                
                del self.clients[client_id]
                self.stats["active_connections"] = max(0, self.stats["active_connections"] - 1)
                self.logger.info(f"🔌 Client {client_id} removed")

    async def _close_all_clients(self):
        """Close all client connections"""
        async with self.client_lock:
            for client_id in list(self.clients.keys()):
                await self._remove_client(client_id)

    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if client is within rate limits"""
        current_time = time.time()
        
        if client_id not in self.rate_limits:
            self.rate_limits[client_id] = {"count": 0, "window_start": current_time}
        
        client_limits = self.rate_limits[client_id]
        
        # Reset window if more than 1 minute has passed
        if current_time - client_limits["window_start"] >= 60:
            client_limits["count"] = 0
            client_limits["window_start"] = current_time
        
        # Check limit
        if client_limits["count"] >= self.max_messages_per_minute:
            return False
        
        client_limits["count"] += 1
        return True

    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            **self.stats,
            "connected_clients": len(self.clients),
            "server_running": self.running,
            "host": self.host,
            "port": self.port
        }

    def get_client_info(self) -> List[Dict[str, Any]]:
        """Get information about connected clients"""
        return [
            {
                "client_id": client.client_id,
                "connected_at": client.connected_at.isoformat(),
                "ip_address": client.ip_address,
                "subscriptions": list(client.subscriptions),
                "last_heartbeat": client.last_heartbeat,
                "is_alive": client.is_alive()
            }
            for client in self.clients.values()
        ]


# Global WebSocket server instance
_websocket_server: Optional[WebSocketServer] = None


def get_websocket_server() -> WebSocketServer:
    """Get the global WebSocket server instance"""
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = WebSocketServer()
    return _websocket_server


async def start_websocket_server(host: str = "localhost", port: int = 8765) -> WebSocketServer:
    """Start the WebSocket server"""
    server = get_websocket_server()
    server.host = host
    server.port = port
    
    if await server.start():
        return server
    else:
        raise RuntimeError("Failed to start WebSocket server")


async def stop_websocket_server():
    """Stop the WebSocket server"""
    global _websocket_server
    if _websocket_server:
        await _websocket_server.stop()
        _websocket_server = None