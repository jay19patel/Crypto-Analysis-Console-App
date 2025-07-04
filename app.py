#!/usr/bin/env python3
"""
Cryptocurrency Trading System with AI Analysis
Simple interface: python app.py (starts everything), python app.py --save (saves to MongoDB)
"""

import argparse
import sys
import time
import threading
import signal
import os
from typing import Optional

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from config import Settings

# Create global config instance
Config = Settings()

from broker.broker_client import BrokerClient
from data.technical_analysis import TechnicalAnalysis
from data.websocket_client import WebSocketClient
from system.health_checker import SystemHealthChecker as HealthChecker
from ui.console import ConsoleUI as Console
from data.mongodb_client import MongoDBClient
from system.websocket_server import websocket_server

class TradingSystem:
    """Main trading system class"""
    
    def __init__(self, save_to_mongodb: bool = False):
        """Initialize trading system"""
        self.save_to_mongodb = save_to_mongodb
        self.console = Console()
        self.health_checker = HealthChecker(self.console)
        self.websocket_client = None
        self.mongodb_client = None
        self.broker_client = None
        self.analysis = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.console.print_warning('Shutting down trading system...')
        self.running = False
        
        # Stop WebSocket server
        if websocket_server.running:
            websocket_server.stop_server()
        
        # Cleanup other components
        if self.websocket_client:
            self.websocket_client.close()
        
        sys.exit(0)
    
    def _start_websocket_client(self, websocket_client):
        """Start WebSocket client in background thread"""
        try:
            self.websocket_client = websocket_client
            if websocket_client.connect():
                websocket_client.ws.run_forever()
        except Exception as e:
            self.console.print_error(f'WebSocket client error: {e}')
            websocket_server.send_log_data('WEBSOCKET', f'WebSocket client error: {e}', 'ERROR')
    
    def _get_live_price(self, symbol: str) -> Optional[float]:
        """Get live price for a symbol from WebSocket client"""
        if self.websocket_client and symbol in self.websocket_client.latest_prices:
            return self.websocket_client.latest_prices[symbol]['price']
        return None
    
    def initialize_components(self) -> bool:
        """Initialize all system components"""
        self.console.print_banner()
        
        # Progress tracking
        with self.console.create_progress_bar('System initialization') as progress:
            # System checks
            system_task = progress.add_task('Running system checks...', total=100)
            if not self.health_checker.run_all_checks():
                self.console.print_error('System check failed. Please resolve issues before continuing.')
                return False
            progress.update(system_task, completed=100)
            
            # WebSocket server
            websocket_task = progress.add_task('Starting WebSocket server...', total=100)
            websocket_server.start_in_background()
            websocket_server.send_log_data('SYSTEM', 'WebSocket server started', 'SUCCESS')
            progress.update(websocket_task, completed=100)
            
            # Technical analysis
            analysis_task = progress.add_task('Initializing analysis engine...', total=100)
            self.analysis = TechnicalAnalysis(
                self.console,
                Config.DEFAULT_SYMBOL,
                Config.DEFAULT_RESOLUTION,
                Config.DEFAULT_HISTORY_DAYS
            )
            progress.update(analysis_task, completed=100)
            
            # Live price monitoring
            liveprice_task = progress.add_task('Initializing live price monitoring...', total=100)
            if Config.DEFAULT_ENABLE_LIVE_PRICE:
                self.websocket_client = WebSocketClient(self.console)
                
                # Add current symbol to monitoring
                if Config.DEFAULT_SYMBOL not in Config.DEFAULT_SYMBOLS:
                    temp_symbols = list(Config.DEFAULT_SYMBOLS)
                    temp_symbols.append(Config.DEFAULT_SYMBOL)
                    self.websocket_client.settings.DEFAULT_SYMBOLS = temp_symbols
                
                # Start WebSocket connection in background
                websocket_thread = threading.Thread(
                    target=self._start_websocket_client,
                    args=(self.websocket_client,)
                )
                websocket_thread.daemon = True
                websocket_thread.start()
                
                # Give WebSocket time to connect
                time.sleep(2)
                
                websocket_server.send_log_data('SYSTEM', f'Live price monitoring started for {Config.DEFAULT_SYMBOL}', 'SUCCESS')
            progress.update(liveprice_task, completed=100)
            
            # MongoDB client (if saving enabled)
            mongodb_task = progress.add_task('Initializing MongoDB (if enabled)...', total=100)
            if self.save_to_mongodb:
                self.mongodb_client = MongoDBClient(self.console)
                if not self.mongodb_client.test_connection():
                    self.console.print_warning('MongoDB connection failed. Analysis will continue without saving.')
                    self.mongodb_client = None
                    websocket_server.send_log_data('MONGODB', 'MongoDB connection failed', 'WARNING')
                else:
                    websocket_server.send_log_data('MONGODB', 'MongoDB connection successful', 'SUCCESS')
            progress.update(mongodb_task, completed=100)
            
            # Broker client
            broker_task = progress.add_task('Initializing broker system...', total=100)
            if Config.DEFAULT_ENABLE_BROKER:
                self.broker_client = BrokerClient(self.console)
                if not self.broker_client.initialize():
                    self.console.print_warning('Broker initialization failed. Analysis will continue without trading.')
                    self.broker_client = None
                    websocket_server.send_log_data('BROKER', 'Broker initialization failed', 'WARNING')
                else:
                    self.console.print_success('🚀 Broker system activated! Automated trading enabled.')
                    websocket_server.send_log_data('BROKER', 'Broker system activated - automated trading enabled', 'SUCCESS')
            progress.update(broker_task, completed=100)
        
        return True
    
    def run_analysis_cycle(self):
        """Run single analysis cycle"""
        try:
            # Get live price if available
            live_price = None
            if self.websocket_client and Config.DEFAULT_ENABLE_LIVE_PRICE:
                live_price = self._get_live_price(Config.DEFAULT_SYMBOL)
            
            # Run analysis
            if self.analysis.refresh():
                # Get analysis results
                results = self.analysis.get_analysis_results()
                
                # Add current price information
                if live_price:
                    results['current_price'] = live_price
                    results['live_price_active'] = True
                    self.console.print_success(f'🔴 Live Price: ${live_price:.2f} (Real-time)')
                else:
                    results['live_price_active'] = False
                    self.console.print_info(f'📈 Current Price: ${results.get("current_price", 0):.2f} (Historical)')
                
                # Send to WebSocket server
                websocket_server.send_analysis_data(results)
                
                # Send live price data if available
                if live_price:
                    live_price_data = {
                        'symbol': Config.DEFAULT_SYMBOL,
                        'price': live_price,
                        'timestamp': time.time(),
                        'change': 0,  # Could be calculated from previous price
                        'volume': 0   # Could be added from WebSocket data
                    }
                    websocket_server.send_live_price_data(live_price_data)
                
                # Send broker data if available
                if self.broker_client:
                    try:
                        broker_data = {
                            'balance': self.broker_client.get_account_balance(),
                            'equity': self.broker_client.get_equity(),
                            'margin': self.broker_client.get_margin_info().get('margin_used', 0),
                            'free_margin': self.broker_client.get_margin_info().get('margin_free', 0),
                            'positions': self.broker_client.get_positions()
                        }
                        websocket_server.send_broker_data(broker_data)
                    except Exception as e:
                        websocket_server.send_log_data('BROKER', f'Error getting broker data: {e}', 'ERROR')
                
                # Save to MongoDB if enabled
                if self.save_to_mongodb and self.mongodb_client:
                    try:
                        self.mongodb_client.save_analysis_result(results)
                        websocket_server.send_log_data('MONGODB', f'Analysis results saved for {Config.DEFAULT_SYMBOL}', 'SUCCESS')
                    except Exception as e:
                        websocket_server.send_log_data('MONGODB', f'Error saving to MongoDB: {e}', 'ERROR')
                
                # Execute trades if broker is enabled
                if self.broker_client and results.get('signal'):
                    try:
                        signal = results['signal']
                        if signal in ['BUY', 'SELL']:
                            # Execute trade (this would need to be implemented in broker_client)
                            websocket_server.send_log_data('TRADING', f'Executing {signal} signal for {Config.DEFAULT_SYMBOL}', 'INFO')
                    except Exception as e:
                        websocket_server.send_log_data('TRADING', f'Error executing trade: {e}', 'ERROR')
                
                return True
            else:
                websocket_server.send_log_data('ANALYSIS', 'Analysis refresh failed', 'ERROR')
                return False
                
        except Exception as e:
            self.console.print_error(f'Analysis cycle error: {e}')
            websocket_server.send_log_data('ANALYSIS', f'Analysis cycle error: {e}', 'ERROR')
            return False
    
    def run(self):
        """Main run loop"""
        if not self.initialize_components():
            return False
        
        self.console.print_success('🚀 Trading System Started Successfully!')
        self.console.print_info(f'📊 Symbol: {Config.DEFAULT_SYMBOL}')
        self.console.print_info(f'📈 Resolution: {Config.DEFAULT_RESOLUTION}')
        self.console.print_info(f'🔄 Analysis Interval: {Config.DEFAULT_REFRESH_INTERVAL} seconds')
        self.console.print_info(f'💾 Save to MongoDB: {"✅" if self.save_to_mongodb else "❌"}')
        self.console.print_info(f'🏦 Broker Trading: {"✅" if Config.DEFAULT_ENABLE_BROKER else "❌"}')
        self.console.print_info(f'🔴 Live Price: {"✅" if Config.DEFAULT_ENABLE_LIVE_PRICE else "❌"}')
        self.console.print_info(f'🌐 WebSocket Server: ws://{Config.WEBSOCKET_SERVER_HOST}:{Config.WEBSOCKET_SERVER_PORT}')
        self.console.print_info('🖥️  Web Viewers:')
        self.console.print_info('   python view.py --analysis   (View AI analysis)')
        self.console.print_info('   python view.py --liveprice  (View live prices)')
        self.console.print_info('   python view.py --broker     (View broker dashboard)')
        self.console.print_info('   python view.py --logs       (View system logs)')
        self.console.print_info('Press Ctrl+C to stop')
        
        websocket_server.send_log_data('SYSTEM', 'Trading system fully operational', 'SUCCESS')
        
        self.running = True
        
        try:
            while self.running:
                # Run analysis cycle
                self.run_analysis_cycle()
                
                # Wait for next cycle
                time.sleep(Config.DEFAULT_REFRESH_INTERVAL)
                
        except KeyboardInterrupt:
            self.console.print_warning('Trading system stopped by user')
        except Exception as e:
            self.console.print_error(f'System error: {e}')
            websocket_server.send_log_data('SYSTEM', f'System error: {e}', 'ERROR')
        finally:
            self.running = False
            websocket_server.send_log_data('SYSTEM', 'Trading system shutdown', 'INFO')
        
        return True

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Cryptocurrency Trading System')
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save analysis results to MongoDB database'
    )
    
    args = parser.parse_args()
    
    # Create and run trading system
    system = TradingSystem(save_to_mongodb=args.save)
    
    try:
        system.run()
    except KeyboardInterrupt:
        print('\nTrading system stopped by user')
    except Exception as e:
        print(f'System error: {e}')

if __name__ == '__main__':
    main()