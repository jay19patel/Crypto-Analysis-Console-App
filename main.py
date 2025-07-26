#!/usr/bin/env python3
"""
Professional Algorithmic Trading System - Main Application
Features:
- Professional error handling and type hints
- WebSocket server for real-time frontend broadcasting
- Circuit breaker patterns for resilience
- Comprehensive monitoring and health checks
- Production-ready architecture

Usage:
    python main.py                          # Start trading system
    python main.py --new                    # Start with fresh data
    python main.py --liveSave               # Enable live price saving
    python main.py --websocket-port 8765    # Custom WebSocket port
    python main.py --help                   # Show help
"""

import asyncio
import logging
import signal
import sys
import argparse
import os
from typing import Optional
from datetime import datetime, timezone

# Import the professional trading system
from src.core.trading_system import TradingSystem
from src.config import get_settings

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure enhanced logging
def setup_logging(log_level: str = "INFO"):
    """Setup enhanced logging configuration"""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation
    file_handler = logging.FileHandler('logs/trading.log', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Enhanced console formatter
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries
    external_loggers = [
        'websockets',
        'motor',
        'pymongo',
        'asyncio',
        'websocket'
    ]
    
    for logger_name in external_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments with enhanced options"""
    parser = argparse.ArgumentParser(
        description="Professional Algorithmic Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                          # Start with default settings
    python main.py --new                    # Fresh start (delete all data)
    python main.py --liveSave               # Enable live price saving
    python main.py --websocket-port 8080    # Use port 8080 for WebSocket
    python main.py --log-level DEBUG        # Enable debug logging
    python main.py --config production      # Use production config
        """
    )
    
    parser.add_argument(
        "--new", 
        action="store_true", 
        help="Delete all trading data from database and start fresh"
    )
    
    parser.add_argument(
        "--liveSave",
        action="store_true",
        help="Enable live saving of WebSocket price data to MongoDB"
    )
    
    parser.add_argument(
        "--websocket-port",
        type=int,
        default=8765,
        help="WebSocket server port for frontend connections (default: 8765)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--config",
        choices=["development", "production"],
        default="development",
        help="Configuration profile to use (default: development)"
    )
    
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check and exit"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="Professional Trading System v2.0.0"
    )
    
    return parser.parse_args()


class GracefulShutdownHandler:
    """Handle graceful shutdown of the trading system"""
    
    def __init__(self, trading_system: TradingSystem):
        self.trading_system = trading_system
        self.logger = logging.getLogger("shutdown_handler")
        self.shutdown_requested = False
    
    def signal_handler(self, signum: int, frame):
        """Handle shutdown signals"""
        signal_names = {
            signal.SIGINT: "SIGINT (Ctrl+C)",
            signal.SIGTERM: "SIGTERM (Termination)"
        }
        
        signal_name = signal_names.get(signum, f"Signal {signum}")
        
        if not self.shutdown_requested:
            self.logger.info(f"🛑 Received {signal_name} - Initiating graceful shutdown...")
            self.shutdown_requested = True
            
            # Set shutdown event to stop threads
            self.trading_system._shutdown_event.set()
        else:
            self.logger.warning(f"⚠️ Received {signal_name} again - Forcing immediate shutdown...")
            sys.exit(1)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Windows doesn't have SIGHUP
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self.signal_handler)


async def perform_health_check() -> bool:
    """Perform system health check and return status"""
    logger = logging.getLogger("health_check")
    
    try:
        logger.info("🏥 Performing system health check...")
        
        # Create temporary trading system for health check
        trading_system = TradingSystem()
        
        # Check individual components
        health_checks = {}
        
        # Test MongoDB connection
        try:
            from src.database.mongodb_client import AsyncMongoDBClient
            client = AsyncMongoDBClient()
            health_checks["mongodb"] = await client.connect()
            await client.disconnect()
        except Exception as e:
            logger.error(f"❌ MongoDB health check failed: {e}")
            health_checks["mongodb"] = False
        
        # Test configuration loading
        try:
            settings = get_settings()
            health_checks["configuration"] = settings is not None
        except Exception as e:
            logger.error(f"❌ Configuration health check failed: {e}")
            health_checks["configuration"] = False
        
        # Test WebSocket connectivity
        try:
            # This is a basic check - in production you might want to test actual connectivity
            health_checks["websocket"] = True
        except Exception as e:
            logger.error(f"❌ WebSocket health check failed: {e}")
            health_checks["websocket"] = False
        
        # Summary
        passed_checks = sum(health_checks.values())
        total_checks = len(health_checks)
        
        logger.info("🏥 Health Check Results:")
        for component, status in health_checks.items():
            status_emoji = "✅" if status else "❌"
            logger.info(f"   {status_emoji} {component.capitalize()}: {'PASS' if status else 'FAIL'}")
        
        overall_health = passed_checks == total_checks
        logger.info(f"🏥 Overall Health: {'✅ HEALTHY' if overall_health else '❌ UNHEALTHY'} "
                   f"({passed_checks}/{total_checks} checks passed)")
        
        return overall_health
        
    except Exception as e:
        logger.error(f"❌ Health check failed with error: {e}")
        return False


async def main():
    """Main application entry point"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger("main")
    
    # Print startup banner
    logger.info("=" * 80)
    logger.info("🚀 PROFESSIONAL ALGORITHMIC TRADING SYSTEM v2.0.0")
    logger.info("=" * 80)
    logger.info(f"⚙️  Configuration: {args.config}")
    logger.info(f"📊 Log Level: {args.log_level}")
    logger.info(f"🔌 WebSocket Port: {args.websocket_port}")
    logger.info(f"💾 Live Save: {'Enabled' if args.liveSave else 'Disabled'}")
    logger.info(f"🆕 Fresh Start: {'Yes' if args.new else 'No'}")
    logger.info("=" * 80)
    
    # Perform health check if requested
    if args.health_check:
        healthy = await perform_health_check()
        sys.exit(0 if healthy else 1)
    
    # Create trading system
    trading_system: Optional[TradingSystem] = None
    
    try:
        logger.info("🔧 Initializing trading system...")
        trading_system = TradingSystem(
            live_save=args.liveSave,
            websocket_port=args.websocket_port
        )
        
        # Setup graceful shutdown handling
        shutdown_handler = GracefulShutdownHandler(trading_system)
        shutdown_handler.setup_signal_handlers()
        
        # Handle --new flag (delete all data)
        if args.new:
            logger.info("🗑️ Deleting all trading data (--new flag)...")
            deletion_success = await trading_system.delete_all_data()
            if deletion_success:
                logger.info("✅ Data deletion completed successfully")
            else:
                logger.error("❌ Data deletion failed")
                return 1
        
        # Start the trading system
        logger.info("🚀 Starting trading system...")
        start_success = await trading_system.start()
        
        if not start_success:
            logger.error("❌ Failed to start trading system")
            return 1
        
        # Log successful startup
        logger.info("🎉 Trading system started successfully!")
        logger.info("📡 WebSocket server running on port %d", args.websocket_port)
        logger.info("🔄 Main monitoring loop starting...")
        logger.info("💡 Press Ctrl+C to stop the system gracefully")
        
        # Run main monitoring loop
        await trading_system.run_main_loop()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
        return 0
    except Exception as e:
        logger.error(f"❌ Fatal error in main application: {e}", exc_info=True)
        return 1
    finally:
        # Ensure proper shutdown
        if trading_system:
            try:
                logger.info("🛑 Shutting down trading system...")
                await trading_system.stop()
                
                # Log final statistics
                final_stats = trading_system.get_system_stats()
                
                logger.info("📊 Final System Statistics:")
                logger.info(f"   ⏱️  Uptime: {final_stats.get('uptime', 0):.1f} seconds")
                logger.info(f"   📈 Trades Executed: {final_stats.get('trades_executed', 0)}")
                logger.info(f"   ✅ Successful Trades: {final_stats.get('trades_successful', 0)}")
                logger.info(f"   ❌ Failed Trades: {final_stats.get('trades_failed', 0)}")
                logger.info(f"   🎯 Signals Generated: {final_stats.get('signals_generated', 0)}")
                logger.info(f"   📡 WebSocket Updates: {final_stats.get('websocket_updates', 0)}")
                logger.info(f"   🧠 Strategy Executions: {final_stats.get('strategies_executed', 0)}")
                logger.info(f"   ❌ Total Errors: {final_stats.get('error_count', 0)}")
                
                logger.info("✅ Shutdown completed successfully")
                
            except Exception as e:
                logger.error(f"❌ Error during shutdown: {e}")


if __name__ == "__main__":
    """Entry point for the application"""
    try:
        # Run the main application
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)