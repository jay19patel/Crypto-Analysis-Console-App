import subprocess
import sys
import importlib
import socket
import ssl
import time
from colorama import Fore, Back, Style, init

# Initialize colorama for Windows
init()

class SystemChecker:
    def __init__(self):
        self.required_packages = [
            'websocket',
            'tqdm',
            'colorama',
            'requests'
        ]
        
    def check_python_version(self):
        """Check if Python version is compatible"""
        print(f"{Fore.CYAN}Checking Python version...{Style.RESET_ALL}")
        
        version = sys.version_info
        if version.major >= 3 and version.minor >= 7:
            print(f"  {Fore.GREEN}✓ Python {version.major}.{version.minor}.{version.micro} - Compatible{Style.RESET_ALL}")
            return True
        else:
            print(f"  {Fore.RED}✗ Python {version.major}.{version.minor}.{version.micro} - Requires Python 3.7+{Style.RESET_ALL}")
            return False
    
    def check_dependencies(self):
        """Check if all required packages are installed"""
        print(f"{Fore.CYAN}Checking dependencies...{Style.RESET_ALL}")
        
        missing_packages = []
        installed_packages = []
        
        for package in self.required_packages:
            try:
                # Special handling for websocket-client
                if package == 'websocket':
                    import websocket
                    installed_packages.append(package)
                    print(f"  {Fore.GREEN}✓ {package} - Installed{Style.RESET_ALL}")
                else:
                    importlib.import_module(package)
                    installed_packages.append(package)
                    print(f"  {Fore.GREEN}✓ {package} - Installed{Style.RESET_ALL}")
            except ImportError:
                missing_packages.append(package)
                print(f"  {Fore.RED}✗ {package} - Not installed{Style.RESET_ALL}")
        
        if missing_packages:
            print(f"\n{Fore.YELLOW}Missing packages: {', '.join(missing_packages)}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}To install missing packages, run:{Style.RESET_ALL}")
            print(f"  {Fore.WHITE}pip install -r requirements.txt{Style.RESET_ALL}")
            return False
        else:
            print(f"\n{Fore.GREEN}✓ All dependencies are installed!{Style.RESET_ALL}")
            return True
    
    def check_internet_connectivity(self):
        """Check internet connectivity"""
        print(f"{Fore.CYAN}Checking internet connectivity...{Style.RESET_ALL}")
        
        try:
            # Try to connect to Google DNS
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            print(f"  {Fore.GREEN}✓ Internet connection - Available{Style.RESET_ALL}")
            return True
        except OSError:
            print(f"  {Fore.RED}✗ Internet connection - Not available{Style.RESET_ALL}")
            return False
    
    def check_websocket_connectivity(self):
        """Check WebSocket server connectivity"""
        print(f"{Fore.CYAN}Checking WebSocket server connectivity...{Style.RESET_ALL}")
        
        try:
            # Test SSL connection to the WebSocket server
            hostname = "socket.india.delta.exchange"
            port = 443
            
            context = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    print(f"  {Fore.GREEN}✓ WebSocket server - Reachable{Style.RESET_ALL}")
                    return True
        except Exception as e:
            print(f"  {Fore.RED}✗ WebSocket server - Not reachable ({str(e)}){Style.RESET_ALL}")
            return False
    
    def check_pip_installation(self):
        """Check if pip is working properly"""
        print(f"{Fore.CYAN}Checking pip installation...{Style.RESET_ALL}")
        
        try:
            result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"  {Fore.GREEN}✓ pip - Working properly{Style.RESET_ALL}")
                return True
            else:
                print(f"  {Fore.RED}✗ pip - Not working properly{Style.RESET_ALL}")
                return False
        except Exception as e:
            print(f"  {Fore.RED}✗ pip - Error: {str(e)}{Style.RESET_ALL}")
            return False
    
    def run_full_check(self):
        """Run all system checks"""
        print(f"{Fore.YELLOW}{'='*60}")
        print(f"System Health Check")
        print(f"{'='*60}{Style.RESET_ALL}\n")
        
        checks = [
            ("Python Version", self.check_python_version),
            ("Pip Installation", self.check_pip_installation),
            ("Dependencies", self.check_dependencies),
            ("Internet Connectivity", self.check_internet_connectivity),
            ("WebSocket Server", self.check_websocket_connectivity)
        ]
        
        results = []
        for check_name, check_func in checks:
            try:
                result = check_func()
                results.append((check_name, result))
            except Exception as e:
                print(f"  {Fore.RED}✗ {check_name} - Error: {str(e)}{Style.RESET_ALL}")
                results.append((check_name, False))
            print()  # Add spacing between checks
        
        # Summary
        print(f"{Fore.YELLOW}{'='*60}")
        print(f"Check Summary")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for check_name, result in results:
            status = f"{Fore.GREEN}PASS{Style.RESET_ALL}" if result else f"{Fore.RED}FAIL{Style.RESET_ALL}"
            print(f"  {check_name}: {status}")
        
        print(f"\n{Fore.CYAN}Overall: {passed}/{total} checks passed{Style.RESET_ALL}")
        
        if passed == total:
            print(f"{Fore.GREEN}🎉 System is ready to run!{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}⚠️  Please fix the failing checks before running the application.{Style.RESET_ALL}")
            return False 