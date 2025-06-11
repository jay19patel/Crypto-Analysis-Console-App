import websocket
import json
import threading
import time
import os
from datetime import datetime
from colorama import Fore, Back, Style, init

# Initialize colorama for Windows
init()

class CryptoWebSocketClient:
    def __init__(self):
        self.websocket_url = "wss://socket.india.delta.exchange"
        self.ws = None
        self.latest_prices = {}
        self.connected = False
        self.price_update_interval = 1  # seconds
        self.price_timer = None
        
    def on_error(self, ws, error):
        print(f"{Fore.RED}Socket Error: {error}{Style.RESET_ALL}")
        self.connected = False

    def on_close(self, ws, close_status_code, close_msg):
        print(f"{Fore.YELLOW}Socket closed with status: {close_status_code} and message: {close_msg}{Style.RESET_ALL}")
        self.connected = False
        if self.price_timer:
            self.price_timer.cancel()

    def on_open(self, ws):
        print(f"{Fore.GREEN}Socket opened successfully!{Style.RESET_ALL}")
        self.connected = True
        
        # Subscribe to the v2 spot price for BTC and ETH
        payload = {
            "type": "subscribe",
            "payload": {
                "channels": [
                    {
                        "name": "v2/ticker",
                        "symbols": [
                            "BTCUSD",
                            "MARK:BTCUSD"
                        ]
                    }
                ]
            }
        }
        ws.send(json.dumps(payload))
        print(f"{Fore.CYAN}Subscribed to BTC and ETH price feeds{Style.RESET_ALL}")

    def on_message(self, ws, message):
        try:
            message_json = json.loads(message)
            
            # Check if this is a ticker update
            if message_json.get("type") == "v2/ticker" and "symbol" in message_json:
                symbol = message_json["symbol"]
                price = message_json.get("mark_price") or message_json.get("close") or message_json.get("last_price")
                
                if price:
                    self.latest_prices[symbol] = {
                        "price": float(price),
                        "timestamp": datetime.now()
                    }
                    
        except json.JSONDecodeError:
            print(f"{Fore.RED}Error parsing message: {message}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error processing message: {e}{Style.RESET_ALL}")

    def clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_prices(self):
        """Print current prices in a formatted manner"""
        if not self.latest_prices:
            print(f"{Fore.YELLOW}No price data available yet...{Style.RESET_ALL}")
            return
        
        # Clear screen to update in same place
        self.clear_screen()
        
        # Print header
        print(f"{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗")
        print(f"║                    Crypto Price Tracker                     ║")
        print(f"║                     Live Price Monitor                      ║")
        print(f"╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}{Style.RESET_ALL}")
        
        # Sort symbols for consistent display order
        sorted_symbols = sorted(self.latest_prices.keys())
        
        for symbol in sorted_symbols:
            data = self.latest_prices[symbol]
            price = data["price"]   
            timestamp = data["timestamp"]
            time_diff = (datetime.now() - timestamp).seconds
            
            # Create a more visually appealing display
            symbol_clean = symbol.replace('USD', '')
            print(f"{Fore.WHITE}🔸 {symbol_clean}/USD: {Fore.GREEN}${price:,.2f} {Style.DIM}(updated {time_diff}s ago){Style.RESET_ALL}")
        
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Style.DIM}Updates every 10 seconds • Press Ctrl+C to stop{Style.RESET_ALL}\n")

    def schedule_price_updates(self):
        """Schedule periodic price updates every 10 seconds"""
        if self.connected:
            self.print_prices()
            self.price_timer = threading.Timer(self.price_update_interval, self.schedule_price_updates)
            self.price_timer.daemon = True
            self.price_timer.start()

    def connect(self):
        """Establish WebSocket connection"""
        try:
            self.ws = websocket.WebSocketApp(
                self.websocket_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            return True
        except Exception as e:
            print(f"{Fore.RED}Failed to create WebSocket connection: {e}{Style.RESET_ALL}")
            return False

    def start_connection(self):
        """Start the WebSocket connection and price updates"""
        if self.connect():
            # Start price updates after a short delay to allow connection establishment
            threading.Timer(3.0, self.schedule_price_updates).start()
            
            try:
                self.ws.run_forever()
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Stopping application...{Style.RESET_ALL}")
                self.stop()
            except Exception as e:
                print(f"{Fore.RED}Connection error: {e}{Style.RESET_ALL}")
                self.connected = False

    def stop(self):
        """Stop the WebSocket connection and timers"""
        self.connected = False
        if self.price_timer:
            self.price_timer.cancel()
        if self.ws:
            self.ws.close()

    def test_connection(self):
        """Test WebSocket connection without starting price updates"""
        print(f"{Fore.CYAN}Testing WebSocket connection...{Style.RESET_ALL}")
        
        test_ws = websocket.WebSocketApp(
            self.websocket_url,
            on_open=lambda ws: print(f"{Fore.GREEN}✓ Connection test successful!{Style.RESET_ALL}"),
            on_error=lambda ws, error: print(f"{Fore.RED}✗ Connection test failed: {error}{Style.RESET_ALL}"),
            on_close=lambda ws, code, msg: None
        )
        
        # Test connection with timeout
        connection_thread = threading.Thread(target=test_ws.run_forever)
        connection_thread.daemon = True
        connection_thread.start()
        
        # Wait for connection test
        time.sleep(3)
        test_ws.close()
        
        return True 