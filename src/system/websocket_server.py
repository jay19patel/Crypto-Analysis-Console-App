import asyncio
import json
import logging
import websockets
import threading
import queue
from datetime import datetime
from typing import Dict, Any, Optional
from src.config import get_settings
from src.broker.position_manager import PositionManager
from src.broker.models import Position
from src.data.technical_analysis import TechnicalAnalysis
from src.strategies.strategy_manager import StrategyManager
from .message_formatter import MessageFormatter, MessageType
import time

logger = logging.getLogger(__name__)

class WebSocketServer:
    """WebSocket server for broadcasting messages to web clients"""
    
    def __init__(self):
        """Initialize WebSocket server"""
        self.logger = logging.getLogger(__name__)
        self.clients = set()
        self.message_queue = queue.Queue()
        self.server = None
        self.server_thread = None
        self.is_running = False
        self.settings = get_settings()
    
    async def register(self, websocket):
        """Register a new client"""
        try:
            self.clients.add(websocket)
            self.logger.info(f"Client connected. Total clients: {len(self.clients)}")
        except Exception as e:
            self.logger.error(f"Error registering client: {e}")
    
    async def unregister(self, websocket):
        """Unregister a client"""
        try:
            self.clients.discard(websocket)  # Using discard instead of remove to avoid KeyError
            self.logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
        except Exception as e:
            self.logger.error(f"Error unregistering client: {e}")
    
    def queue_message(self, message: Dict[str, Any]):
        """Add message to queue for broadcasting"""
        try:
            if self.is_running and message:
                self.message_queue.put(message)
        except Exception as e:
            self.logger.error(f"Error queueing message: {e}")
    
    async def broadcast_messages(self):
        """Broadcast messages from queue to all clients"""
        while self.is_running:
            try:
                # Get message from queue with timeout
                try:
                    message = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    await asyncio.sleep(0.1)
                    continue
                
                # Remove disconnected clients
                disconnected = set()
                for client in self.clients:
                    try:
                        # Ping to check if client is still connected
                        pong_waiter = await client.ping()
                        await asyncio.wait_for(pong_waiter, timeout=1.0)
                    except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
                        disconnected.add(client)
                    except Exception:
                        disconnected.add(client)
                
                for client in disconnected:
                    await self.unregister(client)
                
                # Broadcast to all remaining clients
                if self.clients:
                    message_str = json.dumps(message)
                    for client in self.clients:
                        try:
                            await client.send(message_str)
                        except websockets.exceptions.ConnectionClosed:
                            await self.unregister(client)
                        except Exception as e:
                            self.logger.error(f"Error sending message to client: {e}")
                            await self.unregister(client)
                
                self.message_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error broadcasting message: {e}")
                await asyncio.sleep(0.1)
    
    async def handle_client(self, websocket):
        """Handle client connection"""
        await self.register(websocket)
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Handle client messages if needed
                    self.logger.debug(f"Received message from client: {data}")
                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON received: {message}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)
    
    async def start_server(self):
        """Start WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_client,
                self.settings.WEBSOCKET_HOST,
                self.settings.WEBSOCKET_PORT,
                ping_interval=20,  # Send ping every 20 seconds
                ping_timeout=10    # Wait 10 seconds for pong response
            )
            self.logger.info(f"WebSocket server started on ws://{self.settings.WEBSOCKET_HOST}:{self.settings.WEBSOCKET_PORT}")
            
            # Start message broadcaster
            asyncio.create_task(self.broadcast_messages())
            
            # Keep server running
            await self.server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"Error starting WebSocket server: {e}")
            self.is_running = False
    
    def start(self):
        """Start WebSocket server in a separate thread"""
        if self.is_running:
            return True
        
        self.is_running = True
        
        def run_server():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.start_server())
            except Exception as e:
                self.logger.error(f"Error in WebSocket server thread: {e}")
                self.is_running = False
            finally:
                try:
                    loop.close()
                except Exception as e:
                    self.logger.error(f"Error closing event loop: {e}")
        
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Wait for server to start
        timeout = 5.0
        start_time = time.time()
        while not self.server and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if not self.server:
            self.logger.error("Failed to start WebSocket server")
            self.is_running = False
            return False
        
        return True
    
    def stop(self):
        """Stop WebSocket server"""
        self.is_running = False
        
        if self.server:
            try:
                # Close the server using the existing event loop
                if self.server_thread and self.server_thread.is_alive():
                    async def close_server():
                        await self.server.close()
                    asyncio.run_coroutine_threadsafe(close_server(), asyncio.get_event_loop())
                self.server = None
            except Exception as e:
                self.logger.error(f"Error closing WebSocket server: {e}")
        
        if self.server_thread:
            try:
                self.server_thread.join(timeout=5.0)
            except Exception as e:
                self.logger.error(f"Error stopping WebSocket server thread: {e}")
            self.server_thread = None
        
        # Clear all clients and message queue
        self.clients.clear()
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break
        
        self.logger.info("WebSocket server stopped")

# Global WebSocket server instance
websocket_server = WebSocketServer() 