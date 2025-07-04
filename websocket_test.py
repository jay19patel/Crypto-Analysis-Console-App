#!/usr/bin/env python3
"""
WebSocket Test Client
Usage: python websocket_test.py
"""

import asyncio
import websockets
import json
import logging
import signal
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketTestClient:
    def __init__(self):
        self.uri = "ws://localhost:8765"
        self.websocket = None
        self.running = True
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
    
    def handle_signal(self, signum, frame):
        """Handle system signals"""
        logger.info(f"Received signal {signum}")
        self.running = False
    
    async def receive_messages(self):
        """Receive and print messages"""
        try:
            async with websockets.connect(
                self.uri,
                ping_interval=20,
                ping_timeout=10
            ) as websocket:
                self.websocket = websocket
                logger.info("Connected to WebSocket server")
                
                while self.running:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        
                        # Pretty print different message types
                        msg_type = data.get("type", "unknown")
                        if msg_type == "liveprice":
                            self._print_price_update(data)
                        elif msg_type == "tradelogs":
                            self._print_trade_log(data)
                        elif msg_type == "analysis":
                            self._print_analysis(data)
                        elif msg_type == "positions":
                            self._print_positions(data)
                        else:
                            logger.info(f"Received: {json.dumps(data, indent=2)}")
                            
                    except websockets.exceptions.ConnectionClosed:
                        logger.error("Connection closed")
                        break
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Connection error: {e}")
    
    def _print_price_update(self, data):
        """Pretty print price updates"""
        price_data = data.get("data", {})
        logger.info(f"💰 Price Update - {price_data.get('symbol')}: ${price_data.get('price', 0):.2f}")
    
    def _print_trade_log(self, data):
        """Pretty print trade logs"""
        trade_data = data.get("data", {})
        logger.info(f"📊 Trade Log: {trade_data.get('message')}")
    
    def _print_analysis(self, data):
        """Pretty print analysis results"""
        analysis_data = data.get("data", {})
        logger.info(f"📈 Analysis - {analysis_data.get('symbol')}")
    
    def _print_positions(self, data):
        """Pretty print position updates"""
        positions = data.get("data", {}).get("positions", [])
        logger.info(f"📍 Positions Update - Count: {len(positions)}")

async def main():
    """Main entry point"""
    client = WebSocketTestClient()
    try:
        await client.receive_messages()
    except KeyboardInterrupt:
        logger.info("Test client stopped")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test client stopped") 