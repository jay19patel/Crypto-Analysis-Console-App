import json
import time
import logging
import threading
import websocket
from datetime import datetime
from typing import Dict, Optional

from src.config import get_settings
from src.system.message_formatter import MessageFormatter, MessageType
from src.data.technical_analysis import TechnicalAnalysis
from src.data.mongodb_client import MongoDBClient
from src.broker.delta_client import DeltaBrokerClient
from src.broker.position_manager import PositionManager

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
        self._system_ready = False  # Track if all components are ready
        
        # Initialize components
        self.mongodb_client = MongoDBClient()
        
        # Initialize technical analysis with websocket_server, not mongodb_client
        self.technical_analysis = TechnicalAnalysis(
            websocket_server=websocket_server,
            mongodb_client=self.mongodb_client
        )
        
        # Initialize Delta client with components
        self.delta_client = DeltaBrokerClient(
            websocket_server=websocket_server,
            technical_analysis=self.technical_analysis
        )
        
        # Initialize position manager with correct parameters
        self.position_manager = PositionManager(
            broker_client=self.delta_client,
            websocket_server=websocket_server,
            technical_analysis=self.technical_analysis
        )
        
        # Set position manager in Delta client
        self.delta_client.position_manager = self.position_manager
        
        # Track last analysis time
        self._last_analysis_time = 0
        self._analysis_interval = self.settings.ANALYSIS_INTERVAL
        self._last_price_check = 0
        self._price_check_interval = self.settings.POSITION_CHECK_INTERVAL
        self.current_prices = {}  # Store latest prices
    
    def send_message(self, message: Dict):
        """Send message through WebSocket if available"""
        if self.websocket_server:
            self.websocket_server.queue_message(message)

    def log_message(self, message: str, level: str = "info"):
        """Send log message"""
        self.logger.log(getattr(logging, level.upper()), message)
        if self.websocket_server:
            from src.system.message_formatter import MessageFormatter
            # Send log to WebSocket clients
            self.send_message(
                MessageFormatter.format_log(message, level, "websocket_client")
            )

    def set_system_ready(self, ready: bool):
        """Set system ready status"""
        self._system_ready = ready
        if ready:
            self.log_message("All components ready - starting periodic tasks", "info")
        else:
            self.log_message("System not ready - waiting for all components", "warning")

    def connect(self) -> bool:
        """Connect to WebSocket server
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        try:
            self.log_message("Initializing WebSocket client components...", "info")
            
            # First ensure MongoDB connection
            if not self.mongodb_client.test_connection():
                self.log_message("MongoDB connection failed", "warning")
            else:
                self.log_message("MongoDB connection verified", "info")
            
            # Initialize technical analysis
            if self.technical_analysis:
                self.log_message("Technical analysis component ready", "info")
            else:
                self.log_message("Technical analysis not available", "warning")
            
            # Start Delta client
            self.log_message("Starting Delta Exchange client...", "info")
            if not self.delta_client.start():
                self.log_message("Delta client failed to start", "error")
                self.log_message("Continuing without Delta client - some features may be limited", "warning")
            else:
                self.log_message("Delta client started successfully", "info")
            
            # Connect position manager to MongoDB
            if self.position_manager:
                self.log_message("Connecting Position Manager...", "info")
                if not self.position_manager.connect():
                    self.log_message("Position Manager connection failed", "warning")
                else:
                    self.log_message("Position Manager connected successfully", "info")
                    try:
                        self.position_manager.load_positions()
                        self.log_message("Existing positions loaded", "info")
                    except Exception as e:
                        self.log_message(f"Error loading positions: {e}", "warning")
            
            # Send system status update
            if self.websocket_server:
                self.send_message(
                    MessageFormatter.format_system_status(
                        "WebSocket Client",
                        "ready",
                        "WebSocket client initialized",
                        "websocket_client"
                    )
                )
            
            self.is_connected = True
            self.log_message("WebSocket client connected successfully", "info")
            return True
            
        except Exception as e:
            self.log_message(f"Error connecting WebSocket client: {e}", "error")
            self.logger.error(f"Error connecting to WebSocket: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from WebSocket server"""
        try:
            if self.delta_client:
                self.delta_client.stop()
            if self.position_manager:
                self.position_manager.disconnect()
            self.is_connected = False
            
            # Send system status update
            if self.websocket_server:
                self.send_message(
                    MessageFormatter.format_system_status(
                        "WebSocket Client",
                        "disconnected",
                        "WebSocket client disconnected",
                        "websocket_client"
                    )
                )
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")

    def check_positions(self):
        """Check positions and send updates using latest prices"""
        if not self._system_ready:
            return
            
        try:
            if not self.delta_client.latest_prices:
                return
                
            if self.position_manager and self.delta_client.is_connected:
                # Get current prices
                current_prices = {
                    symbol: data["price"] 
                    for symbol, data in self.delta_client.latest_prices.items()
                }
                
                # Update positions PnL
                self.position_manager.update_positions_pnl(current_prices)
                
                # Check for stop loss and target hits
                closed_positions = self.position_manager.check_stop_loss_and_targets(current_prices)
                
                # Check for expired positions
                expired_positions = self.position_manager.check_and_close_expired_positions(current_prices)
                
                # Get all open positions and send updates
                open_positions = self.position_manager.get_open_positions()
                for position in open_positions:
                    current_price = current_prices.get(position.symbol)
                    if current_price:
                        # Send position update with current price
                        position_data = position.to_dict()
                        position_data['current_price'] = current_price
                        position_data['unrealized_pnl'] = position.unrealized_pnl
                        
                        self.send_message(
                            MessageFormatter.format_position_update(position_data, "position_manager")
                        )
                
                # Log any closed positions
                if closed_positions:
                    for pos_id in closed_positions:
                        self.log_message(f"Position {pos_id} closed due to stop-loss/target", "info")
                
                if expired_positions:
                    for pos_id in expired_positions:
                        self.log_message(f"Position {pos_id} closed due to time expiry", "warning")
                        
        except Exception as e:
            self.logger.error(f"Error checking positions: {e}")

    def run_analysis(self):
        """Run technical analysis and execute trades"""
        if not self._system_ready:
            return
            
        try:
            if self.delta_client.is_connected and self.technical_analysis:
                # Get current prices from delta client if available
                current_prices = None
                if self.delta_client.latest_prices:
                    current_prices = {
                        symbol: data["price"] 
                        for symbol, data in self.delta_client.latest_prices.items()
                    }
                
                # Run technical analysis (with or without current prices)
                analysis_results = self.technical_analysis.analyze_all(current_prices)
                
                if analysis_results:
                    # Send analysis results with enhanced data
                    enhanced_analysis = {
                        "timestamp": datetime.now().isoformat(),
                        "analysis_type": "technical_analysis",
                        "symbols_analyzed": len(analysis_results),
                        "results": analysis_results
                    }
                    
                    from src.system.message_formatter import MessageFormatter
                    self.send_message(
                        MessageFormatter.format_analysis(enhanced_analysis, "technical_analysis")
                    )
                    
                    self.log_message(f"Technical analysis completed for {len(analysis_results)} symbols", "info")
                    
                    # Check for trade signals and execute trades
                    for symbol, analysis in analysis_results.items():
                        # Extract signal from analysis results
                        signal = "WAIT"
                        confidence = 0
                        current_price = analysis.get('current_price', 0)
                        
                        # Check strategy results for signals
                        strategies = analysis.get('strategies', [])
                        if strategies:
                            # Get the strongest signal from strategies
                            buy_signals = [s for s in strategies if s.get('signal') == 'BUY']
                            sell_signals = [s for s in strategies if s.get('signal') == 'SELL']
                            
                            if buy_signals:
                                signal = 'BUY'
                                confidence = max([s.get('confidence', 0) for s in buy_signals])
                            elif sell_signals:
                                signal = 'SELL'
                                confidence = max([s.get('confidence', 0) for s in sell_signals])
                        
                        if signal in ['BUY', 'SELL'] and confidence >= self.settings.BROKER_MIN_CONFIDENCE:
                            try:
                                if current_price > 0:
                                    # Calculate position size based on risk management
                                    risk_amount = self.settings.BROKER_INITIAL_BALANCE * self.settings.BROKER_RISK_PER_TRADE
                                    quantity = risk_amount / current_price
                                    invested_amount = min(risk_amount, self.settings.BROKER_MAX_POSITION_SIZE)
                                    
                                    # Calculate stop loss and target
                                    if signal == 'BUY':
                                        stop_loss = current_price * (1 - self.settings.BROKER_STOP_LOSS_PCT)
                                        target = current_price * (1 + self.settings.BROKER_TARGET_PCT)
                                    else:  # SELL
                                        stop_loss = current_price * (1 + self.settings.BROKER_STOP_LOSS_PCT)
                                        target = current_price * (1 - self.settings.BROKER_TARGET_PCT)
                                    
                                    # Create position
                                    from src.broker.models import PositionType
                                    pos_type = PositionType.LONG if signal == 'BUY' else PositionType.SHORT
                                    
                                    position = self.position_manager.create_position(
                                        symbol=symbol,
                                        position_type=pos_type,
                                        entry_price=current_price,
                                        quantity=quantity,
                                        invested_amount=invested_amount,
                                        strategy_name=f"AI_Analysis_{confidence}%",
                                        stop_loss=stop_loss,
                                        target=target,
                                        leverage=self.settings.BROKER_DEFAULT_LEVERAGE,
                                        analysis_id=analysis.get('analysis_id', '')
                                    )
                                    
                                    if position:
                                        self.send_message(
                                            MessageFormatter.format_trade_log(
                                                f"Trade executed: {signal} {symbol} at ${current_price:.2f} with {confidence}% confidence",
                                                signal,
                                                position.id,
                                                "position_manager"
                                            )
                                        )
                                        self.log_message(f"Trade executed: {signal} {symbol} at ${current_price:.2f}", "info")
                                        
                                        # Update activity status for trade execution
                                        if self.websocket_server:
                                            if not hasattr(self.websocket_server, 'last_activity_update'):
                                                self.websocket_server.last_activity_update = {}
                                            self.websocket_server.last_activity_update["Trade Execution"] = datetime.now().strftime("%H:%M:%S")
                                    
                            except Exception as e:
                                self.log_message(f"Error executing trade for {symbol}: {e}", "error")
                                
                    self.log_message("Technical analysis completed", "info")
        except Exception as e:
            self.logger.error(f"Error running analysis: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            # Implementation depends on your data source
            # This is just a placeholder
            return 0.0  # Replace with actual price data
        except Exception as e:
            self.logger.error(f"Error getting price for {symbol}: {e}")
            return None

    def on_message(self, ws: websocket.WebSocketApp, message: str) -> None:
        """Handle incoming WebSocket messages"""
        try:
            message_json = json.loads(message)
            
            # Handle market data updates
            if message_json.get("type") == "market_data":
                data = message_json.get("data", {})
                prices = data.get("prices", {})
                
                # Update current prices
                for symbol, price_data in prices.items():
                    self.current_prices[symbol] = price_data["price"]
                    
                    # Update Delta client with latest prices
                    if self.delta_client:
                        self.delta_client.update_market_data(symbol, price_data)
                
                # Forward message to WebSocket server
                if self.websocket_server:
                    self.send_message(message_json)
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def process_periodic_tasks(self):
        """Process periodic tasks - only runs when system is ready"""
        while not self._stop_event.is_set():
            try:
                # Only process tasks if system is ready and Delta client is connected
                if self._system_ready and self.delta_client and self.delta_client.is_connected:
                    current_time = time.time()
                    
                    # Send live prices every 10 seconds
                    if current_time - self._last_price_check >= self._price_check_interval:
                        self._last_price_check = current_time
                        
                        # Send live price update
                        if self.delta_client.latest_prices:
                            self.send_message({
                                "type": MessageType.LIVE_PRICE.value,
                                "data": self.delta_client.latest_prices,
                                "timestamp": datetime.now().isoformat()
                            })
                            
                            # Update activity status
                            if self.websocket_server:
                                if not hasattr(self.websocket_server, 'last_activity_update'):
                                    self.websocket_server.last_activity_update = {}
                                self.websocket_server.last_activity_update["Live Price Update"] = datetime.now().strftime("%H:%M:%S")
                        
                        # Check positions and send position updates
                        self.check_positions()
                        
                        # Send enhanced position details with live PnL via WebSocket
                        if self.position_manager:
                            current_prices = {
                                symbol: data["price"] 
                                for symbol, data in self.delta_client.latest_prices.items()
                            } if self.delta_client.latest_prices else {}
                            
                            # Get positions with live PnL calculation
                            position_data = self.position_manager.get_positions_with_live_pnl(current_prices)
                            
                            from src.system.message_formatter import MessageFormatter, MessageType
                            self.send_message(
                                MessageFormatter.format_message(
                                    MessageType.POSITIONS,
                                    position_data,
                                    source="position_manager"
                                )
                            )
                            
                            # Log position summary if there are open positions
                            summary = position_data.get("summary", {})
                            open_count = len(position_data.get("open_positions", []))
                            if open_count > 0:
                                total_pnl = summary.get("total_unrealized_pnl", 0)
                                self.log_message(
                                    f"Position Update: {open_count} open | Total PnL: ${total_pnl:.2f}", 
                                    "info"
                                )
                        
                        # Update activity status
                        if self.websocket_server:
                            if not hasattr(self.websocket_server, 'last_activity_update'):
                                self.websocket_server.last_activity_update = {}
                            self.websocket_server.last_activity_update["Position Check"] = datetime.now().strftime("%H:%M:%S")
                    
                    # Run analysis every 10 minutes
                    if current_time - self._last_analysis_time >= self._analysis_interval:
                        self._last_analysis_time = current_time
                        self.run_analysis()
                        
                        # Update activity status
                        if self.websocket_server:
                            if not hasattr(self.websocket_server, 'last_activity_update'):
                                self.websocket_server.last_activity_update = {}
                            self.websocket_server.last_activity_update["Technical Analysis"] = datetime.now().strftime("%H:%M:%S")
                
                time.sleep(1)  # Sleep to prevent tight loop
                
            except Exception as e:
                self.logger.error(f"Error in periodic tasks: {e}")
                time.sleep(1)  # Sleep on error

    def start(self) -> bool:
        """Start the WebSocket client
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        self._stop_event.clear()
        if self.connect():
            # Start periodic tasks in a separate thread
            tasks_thread = threading.Thread(target=self.process_periodic_tasks)
            tasks_thread.daemon = True
            tasks_thread.start()
            
            self.log_message("WebSocket client started successfully", "info")
            return True
        return False

    def stop(self) -> None:
        """Stop the WebSocket client"""
        self._stop_event.set()
        self.disconnect()
        self.log_message("WebSocket client stopped", "info")

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