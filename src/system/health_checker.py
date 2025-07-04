import sys
import socket
import ssl
import subprocess
import httpx
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging
from datetime import datetime
import threading
import time

from src.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    """Data class for health check results"""
    name: str
    status: bool
    message: str

class SystemHealthChecker:
    """System health checker with comprehensive error handling"""
    
    def __init__(self, websocket_server=None):
        """Initialize health checker
        
        Args:
            websocket_server: WebSocket server instance for sending messages
        """
        self.logger = logging.getLogger(__name__)
        self.websocket_server = websocket_server
        self.last_check = {}
        self.settings = get_settings()
        self.results: List[HealthCheckResult] = []
        self.is_running = False
        self.check_thread = None
        self._stop_event = threading.Event()
    
    def check_python_version(self) -> HealthCheckResult:
        """
        Check Python version compatibility
        
        Returns:
            HealthCheckResult: Check result
        """
        try:
            version = sys.version_info
            min_version = (3, 7)
            
            if version >= min_version:
                return HealthCheckResult(
                    name="Python Version",
                    status=True,
                    message=f"Python {version.major}.{version.minor}.{version.micro}"
                )
            else:
                return HealthCheckResult(
                    name="Python Version",
                    status=False,
                    message=f"Python {version.major}.{version.minor}.{version.micro} (Required: >= {min_version[0]}.{min_version[1]})"
                )
        except Exception as e:
            return HealthCheckResult(
                name="Python Version",
                status=False,
                message=f"Error checking Python version: {e}"
            )
    
    def check_internet_connectivity(self) -> HealthCheckResult:
        """
        Check internet connectivity
        
        Returns:
            HealthCheckResult: Check result
        """
        try:
            # Try to connect to a reliable host
            socket.create_connection(("8.8.8.8", 53), timeout=self.settings.SYSTEM_CHECK_TIMEOUT)
            return HealthCheckResult(
                name="Internet Connectivity",
                status=True,
                message="Connected to internet"
            )
        except OSError as e:
            return HealthCheckResult(
                name="Internet Connectivity",
                status=False,
                message=f"No internet connection: {e}"
            )
        except Exception as e:
            return HealthCheckResult(
                name="Internet Connectivity",
                status=False,
                message=f"Error checking internet connectivity: {e}"
            )
    
    def check_websocket_server(self) -> HealthCheckResult:
        """
        Check WebSocket server connectivity
        
        Returns:
            HealthCheckResult: Check result
        """
        try:
            # Parse URL to get hostname
            hostname = self.settings.WEBSOCKET_URL.split("://")[1].split("/")[0]
            port = 443 if self.settings.WEBSOCKET_URL.startswith("wss") else 80
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=self.settings.SYSTEM_CHECK_TIMEOUT) as sock:
                if port == 443:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        return HealthCheckResult(
                            name="WebSocket Server",
                            status=True,
                            message=f"Connected to {hostname}"
                        )
                else:
                    return HealthCheckResult(
                        name="WebSocket Server",
                        status=True,
                        message=f"Connected to {hostname}"
                    )
        except Exception as e:
            return HealthCheckResult(
                name="WebSocket Server",
                status=False,
                message=f"Failed to connect to WebSocket server: {e}"
            )
    
    def check_dependencies(self) -> HealthCheckResult:
        """
        Check required Python dependencies
        
        Returns:
            HealthCheckResult: Check result
        """
        required_packages = [
            "websocket-client",
            "pandas",
            "numpy",
            "httpx",
            "rich",
            "colorama",
            "pymongo",
            "websockets"
        ]
        
        try:
            import pkg_resources
            
            missing = []
            for package in required_packages:
                try:
                    pkg_resources.require(package)
                except pkg_resources.DistributionNotFound:
                    missing.append(package)
            
            if not missing:
                return HealthCheckResult(
                    name="Dependencies",
                    status=True,
                    message="All required packages are installed"
                )
            else:
                return HealthCheckResult(
                    name="Dependencies",
                    status=False,
                    message=f"Missing packages: {', '.join(missing)}"
                )
        except Exception as e:
            return HealthCheckResult(
                name="Dependencies",
                status=False,
                message=f"Error checking dependencies: {e}"
            )
    
    def check_api_access(self) -> HealthCheckResult:
        """
        Check API endpoint accessibility
        
        Returns:
            HealthCheckResult: Check result
        """
        try:
            client = httpx.Client(timeout=self.settings.SYSTEM_CHECK_TIMEOUT)
            response = client.get(f"{self.settings.WEBSOCKET_URL}/health")
            response.raise_for_status()
            
            return HealthCheckResult(
                name="API Access",
                status=True,
                message="API endpoint is accessible"
            )
        except httpx.RequestError as e:
            return HealthCheckResult(
                name="API Access",
                status=False,
                message=f"Failed to access API: {e}"
            )
        except Exception as e:
            return HealthCheckResult(
                name="API Access",
                status=False,
                message=f"Error checking API access: {e}"
            )
    
    def run_all_checks(self) -> bool:
        """
        Run all system health checks
        
        Returns:
            bool: True if all checks passed
        """
        self.logger.info("Running system health checks...")
        
        # Run all checks
        checks = [
            self.check_python_version(),
            self.check_internet_connectivity(),
            self.check_websocket_server(),
            self.check_dependencies(),
            self.check_api_access()
        ]
        
        # Store results
        self.results = checks
        
        # Print results
        for result in self.results:
            if result.status:
                self.logger.info(f"{result.name}: {result.message}")
            else:
                self.logger.error(f"{result.name}: {result.message}")
        
        # Return overall status
        return all(result.status for result in self.results)
    
    def get_results(self) -> List[HealthCheckResult]:
        """
        Get health check results
        
        Returns:
            List[HealthCheckResult]: List of check results
        """
        return self.results
    
    def start(self) -> None:
        """Start health checker"""
        if self.is_running:
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        def run_checks():
            while not self._stop_event.is_set():
                try:
                    self.run_all_checks()
                except Exception as e:
                    self.logger.error(f"Error running health checks: {e}")
                
                # Wait for next check interval
                time.sleep(self.settings.SYSTEM_CHECK_TIMEOUT)
        
        self.check_thread = threading.Thread(target=run_checks)
        self.check_thread.daemon = True
        self.check_thread.start()
    
    def stop(self) -> None:
        """Stop health checker"""
        self.is_running = False
        self._stop_event.set()
        
        if self.check_thread:
            try:
                self.check_thread.join(timeout=5.0)
            except Exception as e:
                self.logger.error(f"Error stopping health checker thread: {e}")
            self.check_thread = None

    def check_all_systems(self) -> Dict[str, Any]:
        """Check health of all system components
        
        Returns:
            Dict containing health status of each component
        """
        status = {}
        
        # Check broker connection
        broker_status = self._check_broker()
        status["Broker"] = broker_status
        
        # Check database connection
        db_status = self._check_database()
        status["Database"] = db_status
        
        # Check position manager
        pos_status = self._check_position_manager()
        status["Position Manager"] = pos_status
        
        # Log overall status
        healthy = all(s["status"] == "healthy" for s in status.values())
        if not healthy:
            self.logger.warning("System health check failed")
            for component, stat in status.items():
                if stat["status"] != "healthy":
                    self.logger.error(f"{component}: {stat['details']}")
        
        return status

    def _check_broker(self) -> Dict[str, Any]:
        """Check broker connection health"""
        try:
            if not self.websocket_server.is_initialized:
                return {
                    "status": "unhealthy",
                    "details": "WebSocket server not initialized"
                }
            return {
                "status": "healthy",
                "details": "Connected"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "details": f"Error checking broker: {str(e)}"
            }

    def _check_database(self) -> Dict[str, Any]:
        """Check database connection health"""
        try:
            if not self.websocket_server.is_connected:
                return {
                    "status": "unhealthy",
                    "details": "WebSocket server not connected"
                }
            return {
                "status": "healthy",
                "details": "Connected"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "details": f"Error checking database: {str(e)}"
            }

    def _check_position_manager(self) -> Dict[str, Any]:
        """Check position manager health"""
        try:
            positions = self.websocket_server.get_all_positions()
            return {
                "status": "healthy",
                "details": f"Managing {len(positions)} positions"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "details": f"Error checking positions: {str(e)}"
            } 