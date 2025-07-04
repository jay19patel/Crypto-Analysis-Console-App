import asyncio
import json
import logging
import websockets
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.config import Settings

# Create global config instance
Config = Settings()

class WebSocketServer:
    def __init__(self):
        self.clients: Dict[str, List[websockets.WebSocketServerProtocol]] = {
            'analysis': [],
            'liveprice': [],
            'broker': [],
            'logs': []
        }
        self.latest_data: Dict[str, Any] = {
            'analysis': None,
            'liveprice': None,
            'broker': None,
            'logs': []
        }
        self.server = None
        self.running = False
        self.logger = logging.getLogger(__name__)
        
    async def register_client(self, websocket, channel: str):
        """Register a client for a specific channel"""
        if channel in self.clients:
            self.clients[channel].append(websocket)
            self.logger.info(f"Client registered for {channel} channel. Total clients: {len(self.clients[channel])}")
            
            # Send latest data to new client
            if self.latest_data[channel] is not None:
                await self.send_to_client(websocket, {
                    'type': channel,
                    'data': self.latest_data[channel],
                    'timestamp': datetime.now().isoformat()
                })
    
    async def unregister_client(self, websocket, channel: str):
        """Unregister a client from a specific channel"""
        if channel in self.clients and websocket in self.clients[channel]:
            self.clients[channel].remove(websocket)
            self.logger.info(f"Client unregistered from {channel} channel. Total clients: {len(self.clients[channel])}")
    
    async def send_to_client(self, websocket, data: Dict):
        """Send data to a specific client"""
        try:
            await websocket.send(json.dumps(data))
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self.logger.error(f"Error sending data to client: {e}")
    
    async def broadcast_to_channel(self, channel: str, data: Any):
        """Broadcast data to all clients in a channel"""
        if channel not in self.clients:
            return
            
        # Store latest data
        if channel == 'logs':
            # For logs, append to list (keep last 100 entries)
            if not isinstance(self.latest_data['logs'], list):
                self.latest_data['logs'] = []
            self.latest_data['logs'].append(data)
            if len(self.latest_data['logs']) > 100:
                self.latest_data['logs'] = self.latest_data['logs'][-100:]
        else:
            self.latest_data[channel] = data
        
        # Broadcast to all clients
        message = {
            'type': channel,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        disconnected_clients = []
        for client in self.clients[channel]:
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(client)
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.append(client)
        
        # Remove disconnected clients
        for client in disconnected_clients:
            self.clients[channel].remove(client)
    
    async def handle_client(self, websocket, path):
        """Handle client connections"""
        try:
            # Extract channel from path
            channel = path.strip('/')
            if channel not in self.clients:
                await websocket.send(json.dumps({
                    'type': 'error',
                    'message': f'Invalid channel: {channel}. Available channels: {list(self.clients.keys())}'
                }))
                return
            
            await self.register_client(websocket, channel)
            
            # Keep connection alive
            async for message in websocket:
                try:
                    data = json.loads(message)
                    # Handle ping/pong for connection health
                    if data.get('type') == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                except json.JSONDecodeError:
                    pass
                    
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:
            # Unregister client from all channels
            for channel in self.clients:
                await self.unregister_client(websocket, channel)
    
    async def start_server(self):
        """Start WebSocket server"""
        try:
            self.server = await websockets.serve(
                self.handle_client,
                Config.WEBSOCKET_SERVER_HOST,
                Config.WEBSOCKET_SERVER_PORT
            )
            self.running = True
            self.logger.info(f"WebSocket server started on ws://{Config.WEBSOCKET_SERVER_HOST}:{Config.WEBSOCKET_SERVER_PORT}")
            
            # Keep server running
            await self.server.wait_closed()
        except Exception as e:
            self.logger.error(f"Error starting WebSocket server: {e}")
            self.running = False
    
    def start_in_background(self):
        """Start WebSocket server in background thread"""
        def run_server():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_server())
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread
    
    def stop_server(self):
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            self.running = False
    
    # Methods to send data from different components
    def send_analysis_data(self, data: Dict):
        """Send analysis data to WebSocket clients"""
        if self.running:
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_channel('analysis', data),
                asyncio.get_event_loop()
            )
    
    def send_live_price_data(self, data: Dict):
        """Send live price data to WebSocket clients"""
        if self.running:
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_channel('liveprice', data),
                asyncio.get_event_loop()
            )
    
    def send_broker_data(self, data: Dict):
        """Send broker data to WebSocket clients"""
        if self.running:
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_channel('broker', data),
                asyncio.get_event_loop()
            )
    
    def send_log_data(self, log_type: str, message: str, level: str = "INFO"):
        """Send log data to WebSocket clients"""
        if self.running:
            log_data = {
                'type': log_type,
                'message': message,
                'level': level,
                'timestamp': datetime.now().isoformat()
            }
            asyncio.run_coroutine_threadsafe(
                self.broadcast_to_channel('logs', log_data),
                asyncio.get_event_loop()
            )

# Global WebSocket server instance
websocket_server = WebSocketServer() 