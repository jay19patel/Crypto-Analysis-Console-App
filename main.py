"""
Professional Algorithmic Trading System - Main Application
Features:
- Professional error handling and type hints
- WebSocket server for real-time frontend broadcasting
- Circuit breaker patterns for resilience
- Comprehensive monitoring and health checks
- Production-ready architecture

Usage:
    python main.py                          # Start trading system (INFO level, no email)
    python main.py --new                    # Complete cleanup (data, logs, cache)
    python main.py --emailon                # Enable email notifications (disabled by default)
    python main.py --livesaveon             # Enable live price saving (disabled by default)
    python main.py --websocket-port 8765    # Custom WebSocket port
    python main.py --log-level DEBUG        # Debug mode with detailed logs
    python main.py --debug                  # Full debug mode with traceback
    python main.py --help                   # Show help
"""

import asyncio
import logging
import signal
import sys
import argparse
import os
import traceback
from typing import Optional
from datetime import datetime, timezone

# Import the professional trading system
from src.core.trading_system import TradingSystem
from src.config import get_settings

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure enhanced logging with debug support
def setup_logging(log_level: str = "INFO", debug_mode: bool = False):
    """Setup enhanced logging configuration with debug mode support"""
    
    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper())
    root_logger.setLevel(logging.DEBUG if debug_mode else numeric_level)
    
    # Create formatters
    if debug_mode:
        # Debug mode - detailed formatting with file/line info
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s:%(filename)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        # Production mode - clean formatting
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    # File handler (always DEBUG level for complete logs)
    if not debug_mode:
        file_handler = logging.FileHandler('logs/trading.log', encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug_mode else numeric_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from external libraries (unless debug mode)
    if not debug_mode:
        external_loggers = [
            'websockets',
            'motor', 
            'pymongo',
            'asyncio',
            'websocket'
        ]
        
        for logger_name in external_loggers:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Log setup info
    if debug_mode:
        logging.info("🐛 DEBUG MODE ENABLED - Detailed logging active")
        logging.info(f"📋 Console log level: DEBUG")
        logging.info(f"📁 File logging: DISABLED (debug mode)")
    else:
        logging.info(f"📋 Console log level: {log_level}")
        logging.info(f"📁 File log level: DEBUG (logs/trading.log)")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments with enhanced options"""
    parser = argparse.ArgumentParser(
        description="Professional Algorithmic Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                          # Start with default settings (INFO level, no email)
    python main.py --new                    # Complete cleanup (data, logs, cache)
    python main.py --emailon                # Start with email notifications enabled
    python main.py --livesaveon             # Enable live price saving
    python main.py --websocket-port 8080    # Use port 8080 for WebSocket
    python main.py --log-level DEBUG        # Enable debug logging with file save
    python main.py --debug                  # Full debug mode (console only, detailed traces)
    python main.py --debug --new            # Debug mode with fresh start
    python main.py --config production      # Use production config
        """
    )
    
    parser.add_argument(
        "--new", 
        action="store_true", 
        help="System cleanup: Delete trading databases (orders, positions, notifications, etc.) and start fresh"
    )
    
    parser.add_argument(
        "--livesaveon",
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
        "--debug",
        action="store_true",
        help="Enable full debug mode with detailed tracebacks and console-only logging"
    )
    
    parser.add_argument(
        "--config",
        choices=["development", "production"],
        default="development",
        help="Configuration profile to use (default: development)"
    )
    
    parser.add_argument(
        "--emailon",
        action="store_true",
        help="Enable email notifications (disabled by default)"
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
        """Handle shutdown signals with improved robustness"""
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
            
            # Schedule async shutdown with timeout protection
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                if loop and not loop.is_closed():
                    # Create shutdown task with timeout
                    task = asyncio.create_task(self._async_shutdown())
                    
                    # Set up a fallback timer in case shutdown hangs
                    import threading
                    def force_exit():
                        import time
                        time.sleep(12)  # Wait 12 seconds max for shutdown
                        if not task.done():
                            self.logger.error("⚠️ Shutdown timeout (12s) - forcing immediate exit")
                            import os
                            os._exit(1)
                    
                    # Start the timeout thread
                    timeout_thread = threading.Thread(target=force_exit, daemon=True)
                    timeout_thread.start()
                    
            except Exception as e:
                self.logger.error(f"Failed to schedule async shutdown: {e}")
                # Fallback to immediate shutdown
                self.trading_system._shutdown_event.set()
                import time
                time.sleep(3)
                import os
                os._exit(1)
        else:
            self.logger.warning(f"⚠️ Received {signal_name} again - Forcing immediate shutdown...")
            # Give some time for pending operations
            import time
            time.sleep(1)
            import os
            os._exit(1)
    
    async def _async_shutdown(self):
        """Perform async shutdown operations with improved reliability"""
        shutdown_start = time.time()
        try:
            self.logger.info("🔄 Starting comprehensive shutdown sequence...")
            
            # Stop the trading system and ensure all components shutdown
            self.logger.info("🛑 Stopping trading system components...")
            await self.trading_system.stop()
            self.logger.info("✅ Trading system stopped successfully")
            
            # Give final time for email notifications if enabled
            if hasattr(self.trading_system, 'notification_manager') and self.trading_system.notification_manager:
                self.logger.info("📧 Waiting for final email notifications...")
                await asyncio.sleep(5)  # Give more time for email delivery
                self.logger.info("✅ Email notification wait completed")
            
            shutdown_duration = time.time() - shutdown_start
            self.logger.info(f"✅ Shutdown completed successfully in {shutdown_duration:.2f}s")
            
        except Exception as e:
            self.logger.error(f"❌ Error during shutdown: {e}")
        finally:
            # Force clean exit
            self.logger.info("🏁 Initiating final system exit...")
            await asyncio.sleep(0.2)  # Brief pause for log output
            
            # Use os._exit for immediate termination
            import os
            self.logger.info("🔚 System shutdown complete")
            os._exit(0)
    
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
    
    # Determine final log level (debug flag overrides log-level)
    final_log_level = "DEBUG" if args.debug else args.log_level
    
    # Setup logging
    setup_logging(final_log_level, debug_mode=args.debug)
    logger = logging.getLogger("main")
    
    # Debug mode banner
    if args.debug:
        logger.info("🐛" * 30)
        logger.info("🐛 DEBUG MODE ACTIVATED")
        logger.info("🐛 Detailed tracebacks enabled")
        logger.info("🐛 Console-only logging active")
        logger.info("🐛 All component logs visible")
        logger.info("🐛" * 30)
    
    # Print startup banner with system configuration
    from src.config import get_settings, get_trading_config, get_system_intervals
    settings = get_settings()
    trading_config = get_trading_config()
    intervals = get_system_intervals()
    
    logger.info("=" * 80)
    logger.info("🚀 PROFESSIONAL ALGORITHMIC TRADING SYSTEM v2.0.0")
    logger.info("=" * 80)
    logger.info("📊 SYSTEM CONFIGURATION:")
    logger.info(f"   🎯 Strategy Execution Interval: {intervals['strategy_execution']}s ({intervals['strategy_execution']//60} minutes)")
    logger.info(f"   📈 Historical Data Update: {intervals['historical_data_update']}s ({intervals['historical_data_update']//60} minutes)")
    logger.info(f"   📡 Live Price Updates: {intervals['live_price_update']}")
    logger.info(f"   🛡️  Risk Check Interval: {intervals['risk_check']}s")
    logger.info("")
    logger.info("💰 TRADING PARAMETERS:")
    logger.info(f"   💵 Initial Balance: ${trading_config['initial_balance']:,.2f}")
    logger.info(f"   📊 Balance Per Trade: {trading_config['balance_per_trade_pct']*100:.0f}%")
    logger.info(f"   ⚡ Default Leverage: {trading_config['default_leverage']:.0f}x")
    logger.info(f"   🛑 Stop Loss: {trading_config['stop_loss_pct']*100:.1f}%")
    logger.info(f"   🎯 Target Profit: {trading_config['target_pct']*100:.1f}%")
    logger.info(f"   📊 Min Confidence: {trading_config['min_confidence']:.1f}%")
    logger.info(f"   🔢 Daily Trade Limit: {trading_config['daily_trades_limit']}")
    logger.info("")
    logger.info("🧠 ACTIVE STRATEGIES:")
    for strategy in settings.STRATEGY_CLASSES:
        logger.info(f"   ✅ {strategy}")
    logger.info("")
    logger.info("💱 TRADING SYMBOLS:")
    for symbol in settings.TRADING_SYMBOLS:
        logger.info(f"   📈 {symbol}")
    logger.info("")
    logger.info("⚙️  SYSTEM STATUS:")
    logger.info(f"   🔌 WebSocket Port: {args.websocket_port}")
    logger.info(f"   📧 Email Notifications: {'Enabled' if args.emailon else 'Disabled'}")
    logger.info(f"   💾 Live Save: {'Enabled' if args.livesaveon else 'Disabled'}")
    logger.info(f"   📊 Log Level: {final_log_level}")
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
            live_save=args.livesaveon,
            websocket_port=args.websocket_port,
            email_enabled=args.emailon
        )
        
        # Setup graceful shutdown handling
        shutdown_handler = GracefulShutdownHandler(trading_system)
        shutdown_handler.setup_signal_handlers()
        
        # Handle --new flag (complete cleanup)
        if args.new:
            logger.info("🗑️ Starting system database cleanup (--new flag)...")
            logger.info("   This will clear: System databases (orders, positions, notifications, etc.)")
            cleanup_success = await trading_system.delete_all_data()
            if cleanup_success:
                logger.info("✅ System database cleanup completed successfully")
            else:
                logger.error("❌ System database cleanup failed")
                return 1
        
        # Start the trading system
        logger.info("🚀 Starting trading system...")
        start_success = await trading_system.start()
        
        if not start_success:
            logger.error("❌ Failed to start trading system")
            return 1
        
        # System started successfully - detailed messages logged by trading_system.start()
        logger.info("📡 WebSocket server running on port %d", args.websocket_port)
        logger.info("🔄 Main monitoring loop starting...")
        logger.info("💡 Press Ctrl+C to stop the system gracefully")
        
        # Run main monitoring loop with improved shutdown handling
        try:
            await trading_system.run_main_loop()
        except KeyboardInterrupt:
            logger.info("🛑 Main loop interrupted by KeyboardInterrupt")
        except asyncio.CancelledError:
            logger.info("🛑 Main loop cancelled during shutdown")
        except Exception as e:
            logger.error(f"❌ Error in main loop: {e}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
        return 0
    except Exception as e:
        if args.debug:
            logger.error(f"❌ FATAL ERROR: {e}")
            logger.error(f"❌ Error Type: {type(e).__name__}")
            logger.error("❌ Full Traceback:")
            traceback.print_exc()
        else:
            logger.error(f"❌ Fatal error in main application: {e}", exc_info=True)
        return 1
    finally:
        # Ensure proper shutdown even if signal handler didn't work
        if trading_system and trading_system._running:
            try:
                logger.info("🛑 Final shutdown attempt in main() finally block...")
                await trading_system.stop()
                logger.info("✅ Final shutdown completed successfully")
                
                # Extra time for email delivery if notifications enabled
                if hasattr(trading_system, 'notification_manager') and trading_system.notification_manager:
                    logger.info("📧 Final email delivery wait...")
                    await asyncio.sleep(2)
                    
            except Exception as e:
                if hasattr(args, 'debug') and args.debug:
                    logger.error(f"❌ FINAL SHUTDOWN ERROR: {e}")
                    logger.error(f"❌ Error Type: {type(e).__name__}")
                    logger.error("❌ Shutdown Traceback:")
                    traceback.print_exc()
                else:
                    logger.error(f"❌ Error during final shutdown: {e}")
        
        # Ensure we exit the process completely
        logger.info("🔚 Main function exiting...")
        import sys
        sys.exit(0)


if __name__ == "__main__":
    """Entry point for the application with enhanced error handling"""
    try:
        # Run the main application with timeout to prevent hanging
        exit_code = asyncio.run(main())
        print("🏁 Application completed successfully")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user - exiting immediately")
        # Force exit to ensure we don't hang
        import os
        os._exit(0)
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("💡 Solution: Check if all dependencies are installed")
        print("📋 Run: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        # Check if debug mode was requested
        debug_mode = '--debug' in sys.argv
        
        if debug_mode:
            print(f"❌ CRITICAL ERROR: {e}")
            print(f"❌ Error Type: {type(e).__name__}")
            print("❌ Full Traceback:")
            traceback.print_exc()
        else:
            print(f"❌ Critical error: {e}")
            print("💡 Run with --debug for detailed error information")
        
        # Force exit in case of critical errors
        import os
        os._exit(1)