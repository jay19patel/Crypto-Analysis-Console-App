#!/usr/bin/env python3
"""
Crypto Price Tracker - Console Application
A WebSocket-based cryptocurrency price tracking system with technical analysis
"""

import argparse
import sys
import time
from typing import Optional

from src.config import get_settings
from src.ui.console import ConsoleUI
from src.data.websocket_client import WebSocketClient
from src.data.technical_analysis import TechnicalAnalysis
from src.data.mongodb_client import MongoDBClient
from src.system.health_checker import SystemHealthChecker

class Application:
    """Main application class"""
    
    def __init__(self):
        """Initialize application components"""
        self.settings = get_settings()
        self.ui = ConsoleUI()
        self.health_checker = SystemHealthChecker(self.ui)
    
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
        save_to_mongodb: bool = False
    ) -> bool:
        """
        Run technical analysis mode
        
        Args:
            refresh_interval: Optional refresh interval in seconds
            symbol: Trading pair symbol
            resolution: Timeframe resolution
            days: Number of days of historical data
            save_to_mongodb: Whether to save results to MongoDB
            
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
                
                # Run system checks
                if not self.health_checker.run_all_checks():
                    self.ui.print_error("System check failed. Please resolve issues before continuing.")
                    return False
                progress.update(system_task, completed=100)
                
                # Initialize analysis engine
                analysis = TechnicalAnalysis(self.ui, symbol, resolution, days)
                progress.update(analysis_task, completed=100)
            
            # Initialize MongoDB client if saving is enabled
            mongodb_client = None
            if save_to_mongodb:
                mongodb_client = MongoDBClient(self.ui)
                if not mongodb_client.test_connection():
                    self.ui.print_warning("MongoDB connection failed. Analysis will continue without saving.")
                    mongodb_client = None
            
            self.ui.print_success("Analysis initialization complete!")
            
            if refresh_interval and refresh_interval > 0:
                self.ui.print_info(f"Analysis will refresh every {refresh_interval} seconds")
                if save_to_mongodb and mongodb_client:
                    self.ui.print_info("Results will be saved to MongoDB on each refresh")
                self.ui.print_info("Press Ctrl+C to stop")
                
                while True:
                    if analysis.refresh():
                        analysis_results = analysis.get_analysis_results()
                        self.ui.print_analysis_results(analysis_results, symbol)
                        
                        # Save to MongoDB if enabled
                        if save_to_mongodb and mongodb_client:
                            mongodb_client.save_analysis_result(analysis_results)
                    time.sleep(refresh_interval)
            else:
                if analysis.refresh():
                    analysis_results = analysis.get_analysis_results()
                    self.ui.print_analysis_results(analysis_results, symbol)
                    
                    # Save to MongoDB if enabled
                    if save_to_mongodb and mongodb_client:
                        mongodb_client.save_analysis_result(analysis_results)
                    
                    return True
                return False
            
        except KeyboardInterrupt:
            self.ui.print_warning("Analysis stopped by user")
            # Disconnect MongoDB if it was connected
            if save_to_mongodb and mongodb_client:
                mongodb_client.disconnect()
            return True
        except Exception as e:
            self.ui.print_error(f"Analysis error: {e}")
            # Disconnect MongoDB if it was connected
            if save_to_mongodb and mongodb_client:
                mongodb_client.disconnect()
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
  python app.py --analysis                 Run technical analysis once
  python app.py --analysis 5               Run technical analysis with 5-second refresh
  python app.py --analysis --save          Run analysis and save to MongoDB
  python app.py --analysis 5 --save        Run analysis with refresh and save to MongoDB

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
        '--resolution',
        type=str,
        choices=['1m', '5m', '15m', '1h', '1d'],
        default='5m',
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
    
    args = parser.parse_args()
    
    # Create application instance
    app = Application()
    
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
            success = app.run_technical_analysis(
                refresh_interval=args.analysis if args.analysis > 0 else None,
                symbol=args.symbol,
                resolution=args.resolution,
                days=args.days,
                save_to_mongodb=args.save
            )
            if not success:
                sys.exit(1)
        
        elif args.liveprice:
            success = app.run_price_monitoring()
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        app.ui.print_warning("Application terminated by user")
    except Exception as e:
        app.ui.print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 