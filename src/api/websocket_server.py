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
from src.database.mongodb_client import AsyncMongoDBClient


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
    browser_fingerprint: Optional[str] = None
    tab_id: Optional[str] = None

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
        self.ip_connections: Dict[str, Set[str]] = {}  # Track connections per IP
        self.browser_sessions: Dict[str, str] = {}  # Track browser sessions
        
        # MongoDB for client tracking
        self.mongodb_client = AsyncMongoDBClient()
        
        # Message queuing for offline clients
        self.message_queue: Dict[str, List[WebSocketMessage]] = {}
        self.max_queue_size = 100
        
        # Connection limits
        self.max_connections_per_ip = 2  # Max 2 connections per IP
        self.connection_timeout = 30  # seconds
        
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
            "uptime": 0,
            "duplicate_connections_blocked": 0
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
        """Handle new client connection with enhanced deduplication"""
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        client_id = str(uuid.uuid4())
        
        try:
            # Wait for initial message to get browser fingerprint and session info
            try:
                # Wait for first message with timeout
                first_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                message_data = json.loads(first_message)
                
                browser_fingerprint = message_data.get('browserFingerprint', 'unknown')
                session_id = message_data.get('sessionId', 'unknown')
                tab_id = message_data.get('tabId', 'unknown')
                user_agent = message_data.get('userAgent', '')
                
                # Check for duplicate browser fingerprint connections
                async with self.client_lock:
                    duplicate_clients = []
                    for existing_id, existing_client in self.clients.items():
                        if (existing_client.browser_fingerprint == browser_fingerprint and 
                            existing_client.is_alive()):
                            duplicate_clients.append(existing_id)
                    
                    # Close duplicate connections from same browser
                    if duplicate_clients:
                        self.logger.warning(f"🚫 Duplicate browser connection detected. Closing {len(duplicate_clients)} existing connections.")
                        for dup_id in duplicate_clients:
                            await self._remove_client(dup_id)
                        self.stats["duplicate_connections_blocked"] += len(duplicate_clients)
                    
                    # Also check IP limit
                    if client_ip in self.ip_connections:
                        active_connections = len([
                            cid for cid in self.ip_connections[client_ip] 
                            if cid in self.clients and self.clients[cid].is_alive()
                        ])
                        
                        if active_connections >= self.max_connections_per_ip:
                            self.logger.warning(f"🚫 IP connection limit reached for {client_ip}. Closing oldest connection.")
                            # Close oldest connection from same IP
                            oldest_client_id = None
                            oldest_time = float('inf')
                            
                            for cid in self.ip_connections[client_ip]:
                                if cid in self.clients:
                                    client_time = self.clients[cid].connected_at.timestamp()
                                    if client_time < oldest_time:
                                        oldest_time = client_time
                                        oldest_client_id = cid
                            
                            if oldest_client_id:
                                await self._remove_client(oldest_client_id)
                            
                            self.stats["duplicate_connections_blocked"] += 1
                            
            except (asyncio.TimeoutError, json.JSONDecodeError) as e:
                self.logger.warning(f"🚫 Invalid initial connection from {client_ip}: {e}")
                await websocket.close(4000, "Invalid connection")
                return
            
            self.logger.info(f"🔌 Client connected: {client_id[:8]} from {client_ip} (Session: {session_id[:8]}, Tab: {tab_id[:8]}, FP: {browser_fingerprint[:8]})")
            
            # Create client connection with enhanced info
            client = ClientConnection(
                websocket=websocket,
                client_id=client_id,
                connected_at=datetime.now(timezone.utc),
                subscriptions=set(),
                last_heartbeat=time.time(),
                ip_address=client_ip,
                user_agent=user_agent,
                authenticated=False,
                browser_fingerprint=browser_fingerprint,
                tab_id=tab_id
            )
            
            # Add to clients and IP tracking
            async with self.client_lock:
                self.clients[client_id] = client
                
                if client_ip not in self.ip_connections:
                    self.ip_connections[client_ip] = set()
                self.ip_connections[client_ip].add(client_id)
                
                self.stats["total_connections"] += 1
                self.stats["active_connections"] += 1
                
                # Store in MongoDB
                await self._store_client_in_db(client)
            
            # Send welcome message
            await self._send_message_to_client(
                client_id,
                MessageType.SYSTEM_STATUS,
                {
                    "status": "connected",
                    "client_id": client_id,
                    "server_time": datetime.now(timezone.utc).isoformat(),
                    "available_subscriptions": [msg_type.value for msg_type in MessageType],
                    "session_id": session_id,
                    "tab_id": tab_id
                }
            )
            
            # Handle subscription if provided in first message
            if message_data.get('type') == 'subscribe':
                await self._handle_subscription(client, message_data.get('channels', []))
            
            # Handle client messages
            await self._handle_client_messages_with_first(client, message_data)
            
        except ConnectionClosed:
            self.logger.info(f"🔌 Client {client_id} disconnected normally")
        except Exception as e:
            self.logger.error(f"❌ Error handling client {client_id}: {e}")
        finally:
            # Clean up client
            await self._remove_client(client_id)
    
    async def _store_client_in_db(self, client: ClientConnection):
        """Store client connection in MongoDB"""
        try:
            client_doc = {
                "client_id": client.client_id,
                "ip_address": client.ip_address,
                "connected_at": client.connected_at,
                "user_agent": client.user_agent,
                "status": "connected"
            }
            await self.mongodb_client.insert_document("websocket_clients", client_doc)
        except Exception as e:
            self.logger.debug(f"Failed to store client in DB: {e}")
    
    async def _remove_client_from_db(self, client_id: str):
        """Remove client from MongoDB"""
        try:
            await self.mongodb_client.update_document(
                "websocket_clients",
                {"client_id": client_id},
                {"$set": {"status": "disconnected", "disconnected_at": datetime.now(timezone.utc)}}
            )
        except Exception as e:
            self.logger.debug(f"Failed to update client in DB: {e}")

    async def _handle_client_messages_with_first(self, client: ClientConnection, first_message_data: dict):
        """Handle messages from client with first message already processed"""
        try:
            # Continue handling messages after the first one
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
                    await self._process_client_message(client, data)
                    
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
                    await self._process_client_message(client, data)
                    
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

    async def _process_client_message(self, client: ClientConnection, data: dict):
        """Process individual client messages"""
        message_type = data.get("type")
        
        if message_type == "subscribe":
            await self._handle_subscription(client, data.get("channels", []))
        elif message_type == "unsubscribe":
            await self._handle_unsubscription(client, data.get("channels", []))
        elif message_type == "ping":
            await self._send_message_to_client(
                client.client_id,
                MessageType.HEARTBEAT,
                {"pong": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            )
        else:
            self.logger.debug(f"Unknown message type from client {client.client_id}: {message_type}")

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

    async def broadcast_positions_update(self, positions: List[Dict]):
        """Broadcast positions update to all subscribed clients"""
        await self._broadcast_to_subscribers(MessageType.POSITIONS, positions)

    async def _broadcast_to_subscribers(self, message_type: MessageType, data: Dict[str, Any]):
        """Broadcast message to all clients subscribed to the message type with reliability"""
        if not self.clients:
            return
        
        async with self.client_lock:
            # Get clients subscribed to this message type and verify they're alive
            subscribed_clients = []
            dead_clients = []
            
            for client_id, client in list(self.clients.items()):
                if message_type.value in client.subscriptions:
                    if client.is_alive():
                        subscribed_clients.append(client_id)
                    else:
                        dead_clients.append(client_id)
            
            # Clean up dead clients
            for client_id in dead_clients:
                await self._remove_client(client_id)
        
        if not subscribed_clients:
            return
        
        # Send to all subscribed clients with better error handling
        successful_sends = 0
        failed_sends = 0
        
        for client_id in subscribed_clients:
            try:
                success = await self._send_message_to_client(client_id, message_type, data)
                if success:
                    successful_sends += 1
                else:
                    failed_sends += 1
            except Exception as e:
                self.logger.debug(f"Failed to send {message_type.value} to client {client_id[:8]}: {e}")
                failed_sends += 1
        
        # Log broadcast statistics
        if failed_sends > 0:
            self.logger.warning(f"Broadcast {message_type.value}: {successful_sends} success, {failed_sends} failed")
        else:
            self.logger.debug(f"Broadcast {message_type.value}: {successful_sends} clients")

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
                current_time = time.time()
                
                # Clean up disconnected clients more aggressively
                async with self.client_lock:
                    disconnected_clients = []
                    
                    for client_id, client in list(self.clients.items()):
                        # Check multiple conditions for dead connections
                        if (not client.is_alive() or 
                            (current_time - client.last_heartbeat) > 180 or  # 3 minutes without heartbeat
                            hasattr(client.websocket, 'closed') and client.websocket.closed):
                            disconnected_clients.append(client_id)
                    
                    if disconnected_clients:
                        self.logger.info(f"🧹 Cleaning up {len(disconnected_clients)} dead connections")
                        for client_id in disconnected_clients:
                            await self._remove_client(client_id)
                
                # Clean up IP tracking for IPs with no active connections
                for ip in list(self.ip_connections.keys()):
                    active_clients = [cid for cid in self.ip_connections[ip] if cid in self.clients]
                    if not active_clients:
                        del self.ip_connections[ip]
                    else:
                        # Update the set to only include active clients
                        self.ip_connections[ip] = set(active_clients)
                
                # Clean up old rate limit data
                for client_id in list(self.rate_limits.keys()):
                    if client_id not in self.clients:
                        del self.rate_limits[client_id]
                
                # Update stats
                self.stats["uptime"] = current_time - self.start_time
                self.stats["active_connections"] = len(self.clients)
                
                # Log connection status
                if len(self.clients) > 0:
                    self.logger.debug(f"📊 Active connections: {len(self.clients)}, IPs: {len(self.ip_connections)}")
                
                await asyncio.sleep(30)  # Cleanup every 30 seconds (more frequent)
                
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
                client_ip = client.ip_address
                
                try:
                    # Check if websocket has closed attribute before accessing it
                    if hasattr(client.websocket, 'closed') and not client.websocket.closed:
                        await client.websocket.close()
                    elif hasattr(client.websocket, 'close'):
                        # Try to close regardless if we can't check status
                        await client.websocket.close()
                except Exception as e:
                    self.logger.debug(f"Error closing websocket for client {client_id}: {e}")
                
                # Remove from IP tracking
                if client_ip in self.ip_connections:
                    self.ip_connections[client_ip].discard(client_id)
                    if not self.ip_connections[client_ip]:
                        del self.ip_connections[client_ip]
                
                # Remove from MongoDB
                await self._remove_client_from_db(client_id)
                
                del self.clients[client_id]
                self.stats["active_connections"] = max(0, self.stats["active_connections"] - 1)
                self.logger.info(f"🔌 Client {client_id[:8]} removed from {client_ip}")

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