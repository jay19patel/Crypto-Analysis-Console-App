#!/usr/bin/env python3
"""
Crypto Price Tracker - Console Application
A WebSocket-based cryptocurrency price tracking system
"""

import argparse
import sys
import time
import os
from tqdm import tqdm
from colorama import Fore, Back, Style, init

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from system_checker import SystemChecker
from websocket_client import CryptoWebSocketClient

# Initialize colorama for Windows
init()

def print_banner():
    """Print application banner"""
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                    Crypto Price Tracker                      ║
║           WebSocket Monitor + Technical Analysis             ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

def show_progress_bar(description, duration=3):
    """Show a progress bar for system initialization"""
    with tqdm(total=100, desc=description, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
        for i in range(100):
            time.sleep(duration / 100)
            pbar.update(1)

def check_system():
    """Run system health checks"""
    print_banner()
    print(f"{Fore.YELLOW}Running system diagnostics...{Style.RESET_ALL}\n")
    
    checker = SystemChecker()
    return checker.run_full_check()

def run_full_application():
    """Run the full application with progress bars and price monitoring"""
    print_banner()
    
    # System initialization with progress bars
    print(f"{Fore.YELLOW}Initializing Crypto Price Tracker...{Style.RESET_ALL}\n")
    
    # Step 1: System Check
    show_progress_bar(f"{Fore.CYAN}Checking system requirements{Style.RESET_ALL}", 2)
    checker = SystemChecker()
    if not checker.run_full_check():
        print(f"\n{Fore.RED}❌ System check failed. Please resolve issues before continuing.{Style.RESET_ALL}")
        return False
    
    print(f"\n{Fore.GREEN}✅ System check completed successfully!{Style.RESET_ALL}\n")
    
    # Step 2: Initializing components
    show_progress_bar(f"{Fore.CYAN}Initializing WebSocket client{Style.RESET_ALL}", 1.5)
    
    # Step 3: Establishing connection
    show_progress_bar(f"{Fore.CYAN}Establishing WebSocket connection{Style.RESET_ALL}", 2)
    
    print(f"\n{Fore.GREEN}🚀 System setup complete! Starting price monitoring...{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📊 Price updates will appear every 10 seconds{Style.RESET_ALL}")
    print(f"{Style.DIM}Press Ctrl+C to stop the application{Style.RESET_ALL}")
    
    # Wait a moment before starting to show the message
    time.sleep(2)
    
    # Start the WebSocket client
    client = CryptoWebSocketClient()
    try:
        client.start_connection()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Application stopped by user{Style.RESET_ALL}")
        client.stop()
        return True
    except Exception as e:
        print(f"\n{Fore.RED}❌ Application error: {e}{Style.RESET_ALL}")
        return False

def run_technical_analysis(refresh_interval=None, symbol='BTCUSD', resolution='5m', days=10):
    """Run technical analysis module"""
    from analysis_manager import AnalysisManager
    
    # Show banner first
    print_banner()
    
    # Show progress bar for analysis preparation
    show_progress_bar(f"{Fore.CYAN}Preparing technical analysis for {symbol}{Style.RESET_ALL}", 2)
    
    manager = AnalysisManager()
    
    print(f"\n{Fore.GREEN}🔧 Setting up technical analysis module...{Style.RESET_ALL}")
    
    # Check requirements
    if not manager.check_requirements():
        print(f"\n{Fore.RED}❌ Please install technical analysis dependencies first.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Run: pip install -r requirements.txt{Style.RESET_ALL}")
        return False
    
    try:
        if refresh_interval and refresh_interval > 0:
            time.sleep(1)  # Brief pause before starting
            
            # Run with refresh loop
            return manager.run_analysis_loop(symbol, refresh_interval, resolution, days)
        else:
            print(f"\n{Fore.GREEN}📊 Running one-time analysis for {symbol}{Style.RESET_ALL}")
            print(f"{Style.DIM}Resolution: {resolution} | History: {days} days{Style.RESET_ALL}")
            time.sleep(1)  # Brief pause before starting
            
            # Run once
            return manager.run_single_analysis(symbol, resolution, days)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Technical analysis stopped by user{Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"\n{Fore.RED}❌ Technical analysis error: {e}{Style.RESET_ALL}")
        return False

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Crypto Price Tracker - Monitor BTC and ETH prices via WebSocket + Technical Analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --check        Run system diagnostics
  python main.py --full         Start full WebSocket price monitoring
  python main.py --analysis     Run technical analysis once
  python main.py --analysis 5   Run technical analysis with 5-second refresh
        """
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Run system health checks and verify all dependencies'
    )
    
    parser.add_argument(
        '--full',
        action='store_true',
        help='Start the full application with price monitoring'
    )
    
    parser.add_argument(
        '--analysis',
        type=int,
        nargs='?',
        const=0,
        help='Run technical analysis. Optionally specify refresh interval in seconds'
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
        default='5m',
        choices=['1m', '5m', '15m', '1h', '1d'],
        help='Timeframe resolution for technical analysis (default: 5m)'
    )
    
    parser.add_argument(
        '--days',
        type=int,
        default=10,
        help='Number of days of historical data for technical analysis (default: 10)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Crypto Price Tracker v2.0.0 (with Technical Analysis)'
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any(vars(args).values()):
        print_banner()
        print(f"{Fore.YELLOW}Please specify an option:{Style.RESET_ALL}")
        print(f"  {Fore.WHITE}--check{Style.RESET_ALL}     : Run system diagnostics")
        print(f"  {Fore.WHITE}--full{Style.RESET_ALL}      : Start WebSocket price monitoring")
        print(f"  {Fore.WHITE}--analysis{Style.RESET_ALL}  : Run technical analysis")
        print(f"\n{Fore.CYAN}Use --help for more information{Style.RESET_ALL}")
        return
    
    # Handle arguments
    if args.check:
        success = check_system()
        if success:
            print(f"\n{Fore.GREEN}✅ Ready to run! Use '--full' for WebSocket or '--analysis' for technical analysis.{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}❌ Please fix the issues above before running the application.{Style.RESET_ALL}")
            sys.exit(1)
    
    elif args.analysis is not None:
        try:
            run_technical_analysis(
                refresh_interval=args.analysis if args.analysis > 0 else None,
                symbol=args.symbol,
                resolution=args.resolution,
                days=args.days
            )
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
            sys.exit(1)
    
    elif args.full:
        try:
            run_full_application()
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")
            sys.exit(1)

if __name__ == "__main__":
    main() 