#!/usr/bin/env python3
"""
Simple run script for Trading System
Usage: python run.py
"""

import os
import sys
import subprocess

def check_dependencies():
    """Check if all dependencies are installed"""
    try:
        import motor
        import pymongo
        import pydantic
        import websockets
        import pandas
        import numpy
        import aiohttp
        import psutil
        print("✅ All dependencies installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def check_mongodb():
    """Check if MongoDB is running"""
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.server_info()
        print("✅ MongoDB is running")
        return True
    except:
        print("❌ MongoDB not running")
        print("Start MongoDB:")
        print("  Linux: sudo systemctl start mongod")
        print("  Mac: brew services start mongodb-community")
        print("  Windows: net start MongoDB")
        return False

def check_config():
    """Check if .env file exists"""
    if os.path.exists(".env"):
        print("✅ Configuration file found")
        return True
    else:
        if os.path.exists(".env.example"):
            print("⚠️ Creating .env from .env.example")
            subprocess.run(["cp", ".env.example", ".env"])
            print("✅ Please edit .env file with your settings")
            return True
        else:
            print("❌ No configuration file found")
            return False

def main():
    print("🚀 Trading System Startup Check")
    print("=" * 40)
    
    # Check all prerequisites
    deps_ok = check_dependencies()
    mongodb_ok = check_mongodb()
    config_ok = check_config()
    
    if deps_ok and mongodb_ok and config_ok:
        print("\n✅ All checks passed! Starting trading system...")
        print("=" * 40)
        
        # Start the main application
        try:
            subprocess.run([sys.executable, "main.py"] + sys.argv[1:])
        except KeyboardInterrupt:
            print("\n🛑 Trading system stopped by user")
    else:
        print("\n❌ Please fix the issues above before running")
        return 1

if __name__ == "__main__":
    main()