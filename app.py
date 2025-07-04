#!/usr/bin/env python3
"""
Crypto Price Tracker - Console Application
A WebSocket-based cryptocurrency price tracking system with technical analysis
"""

import argparse
import sys
import time
import threading
from typing import Optional, List

from src.config import get_settings
from src.ui.console import ConsoleUI
from src.data.websocket_client import WebSocketClient
from src.data.technical_analysis import TechnicalAnalysis
from src.data.mongodb_client import MongoDBClient
from src.system.health_checker import SystemHealthChecker
from src.broker.broker_client import BrokerClient

class Application:
    """Main application class"""
    
    def __init__(self, ui_enabled: bool = True):
        """Initialize application components"""
        self.settings = get_settings()
        self.ui = ConsoleUI(ui_enabled=ui_enabled)
        self.health_checker = SystemHealthChecker(self.ui)
        self.websocket_client = None  # Store WebSocket client reference
    
    def _start_websocket_client(self, websocket_client):
        """Start WebSocket client in background thread"""
        try:
            self.websocket_client = websocket_client  # Store reference
            if websocket_client.connect():
                websocket_client.ws.run_forever()
        except Exception as e:
            self.ui.print_error(f"WebSocket client error: {e}")
    
    def _get_live_price(self, symbol: str) -> Optional[float]:
        """Get live price for a symbol from WebSocket client"""
        if self.websocket_client and symbol in self.websocket_client.latest_prices:
            return self.websocket_client.latest_prices[symbol]["price"]
        return None
    
    def run_system_check(self) -> bool:
        """
        Run system health checks
        
        Returns:
            bool: True if all checks passed
        """
        self.ui.print_banner()
        return self.health_checker.run_all_checks()
    
    def run_price_monitoring(self) -> bool:
        """
        Run live price monitoring mode
        
        Returns:
            bool: True if execution was successful
        """
        try:
            self.ui.print_banner()
            
            # Create progress bar
            with self.ui.create_progress_bar("System initialization") as progress:
                # Add tasks
                system_task = progress.add_task("Running system checks...", total=100)
                websocket_task = progress.add_task("Initializing WebSocket client...", total=100)
                
                # Run system checks
                if not self.health_checker.run_all_checks():
                    self.ui.print_error("System check failed. Please resolve issues before continuing.")
                    return False
                progress.update(system_task, completed=100)
                
                # Initialize WebSocket client
                client = WebSocketClient(self.ui)
                progress.update(websocket_task, completed=50)
                
                if not client.test_connection():
                    self.ui.print_error("WebSocket connection test failed.")
                    return False
                progress.update(websocket_task, completed=100)
            
            self.ui.print_success("System initialization complete!")
            self.ui.print_info(f"Price updates will appear every {self.settings.PRICE_UPDATE_INTERVAL} seconds")
            self.ui.print_info("Press Ctrl+C to stop")
            
            # Start WebSocket client
            client.start()
            return True
            
        except KeyboardInterrupt:
            self.ui.print_warning("Application stopped by user")
            return True
        except Exception as e:
            self.ui.print_error(f"Application error: {e}")
            return False
    
    def run_technical_analysis(
        self,
        refresh_interval: Optional[int] = None,
        symbol: str = 'BTCUSD',
        resolution: str = '5m',
        days: int = 10,
        save_to_mongodb: bool = False,
        enable_broker: bool = False,
        enable_live_price: bool = True
    ) -> bool:
        """
        Run technical analysis mode
        
        Args:
            refresh_interval: Optional refresh interval in seconds
            symbol: Trading pair symbol
            resolution: Timeframe resolution
            days: Number of days of historical data
            save_to_mongodb: Whether to save results to MongoDB
            enable_broker: Whether to enable automated trading
            
        Returns:
            bool: True if execution was successful
        """
        try:
            self.ui.print_banner()
            
            # Create progress bar
            with self.ui.create_progress_bar("Analysis initialization") as progress:
                # Add tasks
                system_task = progress.add_task("Running system checks...", total=100)
                analysis_task = progress.add_task("Initializing analysis engine...", total=100)
                liveprice_task = progress.add_task("Initializing live price monitoring...", total=100)
                
                # Run system checks
                if not self.health_checker.run_all_checks():
                    self.ui.print_error("System check failed. Please resolve issues before continuing.")
                    return False
                progress.update(system_task, completed=100)
                
                # Initialize analysis engine
                analysis = TechnicalAnalysis(self.ui, symbol, resolution, days)
                progress.update(analysis_task, completed=100)
                
                # Initialize live price monitoring if enabled
                websocket_client = None
                if enable_live_price:
                    websocket_client = WebSocketClient(self.ui)
                    
                    # Modify the DEFAULT_SYMBOLS to include current symbol
                    if symbol not in self.settings.DEFAULT_SYMBOLS:
                        # Create a temporary symbols list that includes the current symbol
                        temp_symbols = list(self.settings.DEFAULT_SYMBOLS)
                        temp_symbols.append(symbol)
                        websocket_client.settings.DEFAULT_SYMBOLS = temp_symbols
                    
                    # Start WebSocket connection in a separate thread
                    websocket_thread = threading.Thread(target=self._start_websocket_client, args=(websocket_client,))
                    websocket_thread.daemon = True
                    websocket_thread.start()
                    
                    # Give WebSocket time to connect
                    time.sleep(2)
                    
                progress.update(liveprice_task, completed=100)
            
            # Initialize MongoDB client if saving is enabled
            mongodb_client = None
            if save_to_mongodb:
                mongodb_client = MongoDBClient(self.ui)
                if not mongodb_client.test_connection():
                    self.ui.print_warning("MongoDB connection failed. Analysis will continue without saving.")
                    mongodb_client = None
            
            # Initialize broker client if enabled
            broker_client = None
            if enable_broker:
                broker_client = BrokerClient(self.ui)
                if not broker_client.initialize():
                    self.ui.print_warning("Broker initialization failed. Analysis will continue without trading.")
                    broker_client = None
                else:
                    self.ui.print_success("🚀 Broker system activated! Automated trading enabled.")
            
            self.ui.print_success("Analysis initialization complete!")
            
            if enable_live_price and websocket_client:
                self.ui.print_success(f"🔴 Live price monitoring ACTIVE for {symbol} - Updates every {self.settings.PRICE_UPDATE_INTERVAL} seconds")
            
            if refresh_interval and refresh_interval > 0:
                self.ui.print_info(f"Analysis will refresh every {refresh_interval} seconds")
                if save_to_mongodb and mongodb_client:
                    self.ui.print_info("Results will be saved to MongoDB on each refresh")
                if enable_broker and broker_client:
                    self.ui.print_info("🤖 Automated trading is ACTIVE - signals will be executed automatically")
                self.ui.print_info("Press Ctrl+C to stop")
                
                while True:
                    if analysis.refresh():
                        analysis_results = analysis.get_analysis_results()
                        
                        # Update analysis results with live price if available (even without broker)
                        if enable_live_price:
                            live_price = self._get_live_price(symbol)
                            if live_price:
                                analysis_results['current_price'] = live_price
                                analysis_results['live_price_active'] = True
                            else:
                                analysis_results['live_price_active'] = False
                        
                        # Save to MongoDB first if enabled to get document ID
                        mongodb_document_id = None
                        if save_to_mongodb and mongodb_client:
                            # Save to MongoDB and get the document ID
                            saved_result = mongodb_client.save_analysis_result(analysis_results)
                            if saved_result:
                                mongodb_document_id = saved_result
                        
                        # Process trading signals if broker is enabled
                        broker_actions = {'has_actions': False}
                        
                        if enable_broker and broker_client:
                            # Get current price - prioritize live price, fallback to analysis data
                            live_price = self._get_live_price(symbol) if enable_live_price else None
                            current_price = live_price or analysis_results.get('current_price', analysis.df['close'].iloc[-1])
                            
                            # Update analysis results with live price if available
                            if live_price:
                                analysis_results['current_price'] = live_price
                                analysis_results['live_price_active'] = True
                            else:
                                analysis_results['live_price_active'] = False
                            
                            # Add MongoDB document ID to analysis_results
                            if mongodb_document_id:
                                analysis_results['_id'] = str(mongodb_document_id)
                            
                            # Process signal
                            trade_executed = broker_client.process_analysis_signal(
                                symbol, analysis_results, current_price
                            )
                            
                            # Monitor existing positions
                            closed_positions = broker_client.monitor_positions({symbol: current_price})
                            
                            # Prepare broker actions for display
                            if trade_executed or closed_positions:
                                broker_actions['has_actions'] = True
                                broker_actions['trade_executed'] = trade_executed
                                broker_actions['positions_closed'] = [f"{symbol} position" for _ in closed_positions]
                                broker_actions['monitoring_active'] = True
                            else:
                                broker_actions['monitoring_active'] = True
                            
                            # Display analysis with simple broker actions
                            self.ui.print_analysis_with_simple_broker_actions(analysis_results, symbol, broker_actions)
                        else:
                            # Display normal analysis without broker actions
                            self.ui.print_analysis_results(analysis_results, symbol)
                    
                    time.sleep(refresh_interval)
            else:
                if analysis.refresh():
                    analysis_results = analysis.get_analysis_results()
                    
                    # Update analysis results with live price if available (even without broker)
                    if enable_live_price:
                        live_price = self._get_live_price(symbol)
                        if live_price:
                            analysis_results['current_price'] = live_price
                            analysis_results['live_price_active'] = True
                        else:
                            analysis_results['live_price_active'] = False
                    
                    # Save to MongoDB first if enabled to get document ID
                    mongodb_document_id = None
                    if save_to_mongodb and mongodb_client:
                        # Save to MongoDB and get the document ID
                        saved_result = mongodb_client.save_analysis_result(analysis_results)
                        if saved_result:
                            mongodb_document_id = saved_result
                    
                    # Process trading signals if broker is enabled (one-time)
                    broker_actions = {'has_actions': False}
                    
                    if enable_broker and broker_client:
                        # Get current price - prioritize live price, fallback to analysis data
                        live_price = self._get_live_price(symbol) if enable_live_price else None
                        current_price = live_price or analysis_results.get('current_price', analysis.df['close'].iloc[-1])
                        
                        # Update analysis results with live price if available
                        if live_price:
                            analysis_results['current_price'] = live_price
                            analysis_results['live_price_active'] = True
                        else:
                            analysis_results['live_price_active'] = False
                        
                        # Add MongoDB document ID to analysis_results
                        if mongodb_document_id:
                            analysis_results['_id'] = str(mongodb_document_id)
                        
                        # Process signal
                        trade_executed = broker_client.process_analysis_signal(
                            symbol, analysis_results, current_price
                        )
                        
                        # Monitor existing positions
                        closed_positions = broker_client.monitor_positions({symbol: current_price})
                        
                        # Prepare broker actions for display
                        if trade_executed or closed_positions:
                            broker_actions['has_actions'] = True
                            broker_actions['trade_executed'] = trade_executed
                            broker_actions['positions_closed'] = [f"{symbol} position" for _ in closed_positions]
                            broker_actions['monitoring_active'] = True
                        else:
                            broker_actions['monitoring_active'] = True
                        
                        # Display analysis with simple broker actions
                        self.ui.print_analysis_with_simple_broker_actions(analysis_results, symbol, broker_actions)
                    else:
                        # Display normal analysis without broker actions
                        self.ui.print_analysis_results(analysis_results, symbol)
                    
                    return True
                return False
            
        except KeyboardInterrupt:
            self.ui.print_warning("Analysis stopped by user")
            # Disconnect WebSocket client if it was connected
            if enable_live_price and self.websocket_client:
                try:
                    self.websocket_client.stop()
                    self.ui.print_info("Live price monitoring stopped")
                except:
                    pass
            # Disconnect MongoDB if it was connected
            if save_to_mongodb and mongodb_client:
                mongodb_client.disconnect()
            # Disconnect broker if it was connected
            if enable_broker and broker_client:
                broker_client.disconnect()
            return True
        except Exception as e:
            self.ui.print_error(f"Analysis error: {e}")
            # Disconnect WebSocket client if it was connected
            if enable_live_price and self.websocket_client:
                try:
                    self.websocket_client.stop()
                    self.ui.print_info("Live price monitoring stopped")
                except:
                    pass
            # Disconnect MongoDB if it was connected
            if save_to_mongodb and mongodb_client:
                mongodb_client.disconnect()
            # Disconnect broker if it was connected
            if enable_broker and broker_client:
                broker_client.disconnect()
            return False
    
    def run_multi_symbol_analysis(
        self,
        symbols: List[str],
        refresh_interval: Optional[int] = None,
        resolution: str = '5m',
        days: int = 10,
        save_to_mongodb: bool = False,
        enable_broker: bool = False
    ) -> bool:
        """
        Run technical analysis for multiple symbols
        """
        try:
            self.ui.print_banner()
            
            # Create progress bar for initialization
            with self.ui.create_progress_bar("Multi-symbol analysis initialization") as progress:
                # Add tasks
                system_task = progress.add_task("Running system checks...", total=100)
                symbols_task = progress.add_task(f"Initializing analysis for {len(symbols)} symbols...", total=100)
                
                # Run system checks
                if not self.health_checker.run_all_checks():
                    self.ui.print_error("System check failed. Please resolve issues before continuing.")
                    return False
                progress.update(system_task, completed=100)
                
                # Initialize analysis engines for all symbols
                analysis_engines = {}
                for symbol in symbols:
                    analysis_engines[symbol] = TechnicalAnalysis(self.ui, symbol, resolution, days)
                progress.update(symbols_task, completed=100)
            
            # Initialize MongoDB client if saving is enabled
            mongodb_client = None
            if save_to_mongodb:
                mongodb_client = MongoDBClient(self.ui)
                if not mongodb_client.test_connection():
                    self.ui.print_warning("MongoDB connection failed. Analysis will continue without saving.")
                    mongodb_client = None
            
            # Initialize broker client if enabled
            broker_client = None
            if enable_broker:
                broker_client = BrokerClient(self.ui)
                if not broker_client.initialize():
                    self.ui.print_warning("Broker initialization failed. Analysis will continue without trading.")
                    broker_client = None
                else:
                    self.ui.print_success(f"🚀 Broker system activated! Automated trading enabled for {len(symbols)} symbols.")
            
            self.ui.print_success(f"Multi-symbol analysis initialization complete for: {', '.join(symbols)}")
            
            if refresh_interval and refresh_interval > 0:
                self.ui.print_info(f"Analysis will refresh every {refresh_interval} seconds for {len(symbols)} symbols")
                self.ui.print_info("Press Ctrl+C to stop")
                
                while True:
                    current_prices = {}
                    
                    # Process each symbol
                    for symbol in symbols:
                        analysis = analysis_engines[symbol]
                        
                        if analysis.refresh():
                            analysis_results = analysis.get_analysis_results()
                            current_price = analysis_results.get('current_price', analysis.df['close'].iloc[-1])
                            current_prices[symbol] = current_price
                            
                            # Save to MongoDB first if enabled
                            if save_to_mongodb and mongodb_client:
                                mongodb_client.save_analysis_result(analysis_results)
                            
                            # Process trading signals if broker is enabled
                            if enable_broker and broker_client:
                                broker_client.process_analysis_signal(symbol, analysis_results, current_price)
                            
                            # Display analysis results for this symbol
                            self.ui.print_analysis_results(analysis_results, symbol)
                            
                            # Add separator between symbols
                            if len(symbols) > 1 and symbol != symbols[-1]:
                                self.ui.print_info("─" * 80)
                    
                    # Monitor all positions if broker is enabled
                    if enable_broker and broker_client and current_prices:
                        broker_client.monitor_positions(current_prices)
                    
                    # Wait for next refresh
                    time.sleep(refresh_interval)
            else:
                # Single run for all symbols
                for symbol in symbols:
                    analysis = analysis_engines[symbol]
                    
                    if analysis.refresh():
                        analysis_results = analysis.get_analysis_results()
                        
                        # Save to MongoDB if enabled
                        if save_to_mongodb and mongodb_client:
                            mongodb_client.save_analysis_result(analysis_results)
                        
                        # Display results
                        self.ui.print_analysis_results(analysis_results, symbol)
                        
                        # Add separator between symbols
                        if len(symbols) > 1 and symbol != symbols[-1]:
                            self.ui.print_info("─" * 80)
                
                return True
            
        except KeyboardInterrupt:
            self.ui.print_warning("Multi-symbol analysis stopped by user")
            return True
        except Exception as e:
            self.ui.print_error(f"Multi-symbol analysis error: {e}")
            return False

    def run_broker_dashboard(self) -> bool:
        """
        Run broker dashboard mode - display current broker status with auto-refresh
        
        Returns:
            bool: True if execution was successful
        """
        try:
            # Initialize broker client
            broker_client = BrokerClient(self.ui)
            if not broker_client.initialize():
                self.ui.print_error("Failed to initialize broker system")
                return False
            
            refresh_interval = broker_client.settings.BROKER_UI_REFRESH_INTERVAL
            
            self.ui.print_info(f"🔄 Broker Dashboard - Auto-refreshing every {refresh_interval} seconds")
            self.ui.print_info("Press Ctrl+C to stop")
            self.ui.print_info("")
            
            # Initial display
            broker_client.display_broker_dashboard(show_last_updated=True)
            
            # Auto-refresh loop
            while True:
                time.sleep(refresh_interval)
                
                # Reload positions and account data
                broker_client.position_manager.load_positions()
                all_positions = broker_client.position_manager.positions
                broker_client.account_manager.update_statistics(all_positions)
                
                # Display updated dashboard
                broker_client.display_broker_dashboard(show_last_updated=True)
            
        except KeyboardInterrupt:
            self.ui.print_warning("Broker dashboard stopped by user")
            # Disconnect
            if 'broker_client' in locals():
                broker_client.disconnect()
            return True
            
        except Exception as e:
            self.ui.print_error(f"Broker dashboard error: {e}")
            # Disconnect
            if 'broker_client' in locals():
                broker_client.disconnect()
            return False
    
    def run_database_cleanup(self) -> bool:
        """
        Delete all data from MongoDB collections with confirmation
        
        Returns:
            bool: True if deletion was successful
        """
        try:
            self.ui.print_banner()
            self.ui.print_warning("🗑️  DATABASE CLEANUP MODE")
            self.ui.print_warning("This will permanently delete ALL data from MongoDB collections:")
            self.ui.print_warning("  • accounts")
            self.ui.print_warning("  • analysis_results") 
            self.ui.print_warning("  • positions")
            self.ui.print_warning("")
            
            # First confirmation
            confirmation1 = input("⚠️  Are you sure you want to delete ALL data? Type 'YES' to confirm: ")
            if confirmation1 != 'YES':
                self.ui.print_info("Operation cancelled by user")
                return True
            
            # Second confirmation with database name
            self.ui.print_warning("⚠️  THIS CANNOT BE UNDONE!")
            confirmation2 = input(f"💀 Type 'DELETE ALL DATA' to confirm deletion from database '{self.settings.MONGODB_DATABASE}': ")
            if confirmation2 != 'DELETE ALL DATA':
                self.ui.print_info("Operation cancelled by user")
                return True
            
            self.ui.print_info("🔌 Connecting to MongoDB...")
            
            # Initialize MongoDB client
            mongodb_client = MongoDBClient(self.ui)
            if not mongodb_client.test_connection():
                self.ui.print_error("Failed to connect to MongoDB")
                return False
            
            self.ui.print_success("✅ Connected to MongoDB")
            
            # Get database and collections
            database = mongodb_client.client[self.settings.MONGODB_DATABASE]
            collections_to_delete = ['accounts', 'analysis_results', 'positions']
            
            # Create progress bar
            with self.ui.create_progress_bar("🗑️  Deleting database collections") as progress:
                total_deleted = 0
                
                for i, collection_name in enumerate(collections_to_delete):
                    task = progress.add_task(f"Deleting {collection_name}...", total=100)
                    
                    try:
                        collection = database[collection_name]
                        
                        # Get count before deletion
                        count_before = collection.count_documents({})
                        progress.update(task, completed=30)
                        
                        if count_before > 0:
                            # Delete all documents
                            result = collection.delete_many({})
                            progress.update(task, completed=70)
                            
                            # Verify deletion
                            count_after = collection.count_documents({})
                            progress.update(task, completed=100)
                            
                            if count_after == 0:
                                self.ui.print_success(f"✅ {collection_name}: {result.deleted_count} documents deleted")
                                total_deleted += result.deleted_count
                            else:
                                self.ui.print_error(f"❌ {collection_name}: Failed to delete all documents ({count_after} remaining)")
                                return False
                        else:
                            progress.update(task, completed=100)
                            self.ui.print_info(f"ℹ️  {collection_name}: Already empty (0 documents)")
                    
                    except Exception as e:
                        self.ui.print_error(f"❌ Error deleting {collection_name}: {e}")
                        return False
            
            # Final verification
            self.ui.print_info("🔍 Verifying deletion...")
            verification_passed = True
            
            for collection_name in collections_to_delete:
                collection = database[collection_name]
                remaining_count = collection.count_documents({})
                if remaining_count > 0:
                    self.ui.print_error(f"❌ {collection_name}: {remaining_count} documents still remain!")
                    verification_passed = False
                else:
                    self.ui.print_success(f"✅ {collection_name}: Completely clean")
            
            if verification_passed:
                self.ui.print_success(f"🎉 Database cleanup completed successfully!")
                self.ui.print_success(f"📊 Total documents deleted: {total_deleted}")
                self.ui.print_info("💡 All collections are now empty and ready for fresh data")
            else:
                self.ui.print_error("❌ Database cleanup completed with errors")
                return False
            
            # Close connection
            mongodb_client.disconnect()
            return True
            
        except KeyboardInterrupt:
            self.ui.print_warning("Database cleanup cancelled by user")
            return False
        except Exception as e:
            self.ui.print_error(f"Database cleanup error: {e}")
            return False

def main():
    """Application entry point"""
    parser = argparse.ArgumentParser(
        description="Crypto Price Tracker - Monitor cryptocurrency prices and perform technical analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py --check                    Run system diagnostics
  python app.py --liveprice                Start live price monitoring
  python app.py --analysis                 Run technical analysis once (with live price)
  python app.py --analysis 5               Run technical analysis with 5-second refresh (with live price)
  python app.py --analysis --save          Run analysis and save to MongoDB (with live price)
  python app.py --analysis 5 --save        Run analysis with refresh and save to MongoDB (with live price)
  python app.py --analysis 5 --broker      Run analysis with automated trading + live price (perfect combo!)
  python app.py --analysis --noliveprice   Run analysis using only historical data (no live price)
  python app.py --brokerui                 Display detailed broker dashboard (auto-refreshes every 1 minute)
  
  ✨ NEW FEATURES:
  python app.py --analysis --symbols BTCUSD ETHUSD    Multi-symbol analysis
  python app.py --analysis 5 --symbols BTCUSD ETHUSD --broker    Multi-symbol auto-trading
  python app.py --analysis --uiOff         Run analysis with no UI output (silent mode)
  python app.py --analysis 5 --symbols BTCUSD ETHUSD --uiOff    Silent multi-symbol analysis
  
  🗑️  DATABASE MANAGEMENT:
  python app.py --delete               Delete ALL data from MongoDB (with confirmation)

  Developed by Jay Patel email: developer.jay19@gmail.com
        """
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Run system health checks'
    )
    
    parser.add_argument(
        '--liveprice',
        action='store_true',
        help='Start live price monitoring'
    )
    
    parser.add_argument(
        '--analysis',
        type=int,
        nargs='?',
        const=0,
        help='Run technical analysis with optional refresh interval in seconds'
    )
    
    parser.add_argument(
        '--symbol',
        type=str,
        default='BTCUSD',
        help='Trading pair symbol for technical analysis (default: BTCUSD)'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        nargs='+',
        help='Multiple trading pair symbols for analysis (e.g., --symbols BTCUSD ETHUSD)'
    )
    
    parser.add_argument(
        '--uiOff',
        action='store_true',
        help='Disable all UI output including tables and console messages'
    )
    
    parser.add_argument(
        '--resolution',
        type=str,
        choices=['1m', '5m', '15m', '1h', '1d'],
        default='15m',
        help='Timeframe resolution for technical analysis (default: 5m)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=10,
        help='Number of days of historical data for technical analysis (default: 10)'
    )
    
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save analysis results to MongoDB database with timestamp'
    )
    
    parser.add_argument(
        '--broker',
        action='store_true',
        help='Enable automated trading with analysis'
    )
    
    parser.add_argument(
        '--brokerui',
        action='store_true',
        help='Display detailed broker dashboard with auto-refresh (configurable interval)'
    )
    
    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete all data from MongoDB collections (accounts, analysis_results, positions)'
    )
    
    parser.add_argument(
        '--noliveprice',
        action='store_true',
        help='Disable live price monitoring during analysis (use only historical data)'
    )
    
    args = parser.parse_args()
    
    # Create application instance
    app = Application(ui_enabled=not args.uiOff)
    
    # Handle arguments
    try:
        if not any(vars(args).values()):
            parser.print_help()
            return
        
        if args.check:
            success = app.run_system_check()
            if success:
                app.ui.print_success("System check passed! Ready to run.")
            else:
                app.ui.print_error("System check failed. Please fix the issues above.")
                sys.exit(1)
        
        elif args.analysis is not None:
            # Check if multiple symbols are specified
            if args.symbols:
                # Use DEFAULT_SYMBOLS from config or provided symbols
                symbols = args.symbols
                success = app.run_multi_symbol_analysis(
                    symbols=symbols,
                    refresh_interval=args.analysis if args.analysis > 0 else None,
                    resolution=args.resolution,
                    days=args.days,
                    save_to_mongodb=args.save,
                    enable_broker=args.broker
                )
            else:
                # Single symbol analysis (existing functionality)
                success = app.run_technical_analysis(
                    refresh_interval=args.analysis if args.analysis > 0 else None,
                    symbol=args.symbol,
                    resolution=args.resolution,
                    days=args.days,
                    save_to_mongodb=args.save,
                    enable_broker=args.broker,
                    enable_live_price=not args.noliveprice  # Enable live price by default, disable with --noliveprice
                )
            if not success:
                sys.exit(1)
        
        elif args.brokerui:
            # Display broker dashboard
            success = app.run_broker_dashboard()
            if not success:
                sys.exit(1)
        
        elif args.liveprice:
            success = app.run_price_monitoring()
            if not success:
                sys.exit(1)
        
        elif args.delete:
            success = app.run_database_cleanup()
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        app.ui.print_warning("Application terminated by user")
    except Exception as e:
        app.ui.print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 