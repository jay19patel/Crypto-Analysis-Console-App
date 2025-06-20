import sys
import socket
import ssl
import subprocess
import httpx
from typing import List, Tuple, Optional
from dataclasses import dataclass

from src.config import get_settings
from src.ui.console import ConsoleUI

@dataclass
class HealthCheckResult:
    """Data class for health check results"""
    name: str
    status: bool
    message: str

class SystemHealthChecker:
    """System health checker with comprehensive error handling"""
    
    def __init__(self, ui: ConsoleUI):
        """
        Initialize system health checker
        
        Args:
            ui (ConsoleUI): Console UI instance
        """
        self.settings = get_settings()
        self.ui = ui
        self.results: List[HealthCheckResult] = []
    
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
            "pandas-ta",
            "httpx",
            "rich",
            "colorama"
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
        self.ui.print_info("Running system health checks...")
        
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
                self.ui.print_success(f"{result.name}: {result.message}")
            else:
                self.ui.print_error(f"{result.name}: {result.message}")
        
        # Return overall status
        return all(result.status for result in self.results)
    
    def get_results(self) -> List[HealthCheckResult]:
        """
        Get health check results
        
        Returns:
            List[HealthCheckResult]: List of check results
        """
        return self.results 