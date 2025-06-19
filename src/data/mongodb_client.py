"""
MongoDB client for storing analysis results
"""

from pymongo import MongoClient, errors
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import logging
from ..config import get_settings
from ..ui.console import ConsoleUI

class MongoDBClient:
    """MongoDB client for analysis results storage"""
    
    def __init__(self, ui: ConsoleUI):
        """Initialize MongoDB client"""
        self.ui = ui
        self.settings = get_settings()
        self.client = None
        self.db = None
        self.collection = None
        self.is_connected = False
        
    def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(
                self.settings.MONGODB_URL,
                serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT * 1000
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database and collection
            self.db = self.client[self.settings.MONGODB_DATABASE]
            self.collection = self.db[self.settings.MONGODB_COLLECTION]
            
            self.is_connected = True
            self.ui.print_success(f"Connected to MongoDB: {self.settings.MONGODB_DATABASE}.{self.settings.MONGODB_COLLECTION}")
            return True
            
        except errors.ServerSelectionTimeoutError:
            self.ui.print_error("MongoDB connection timeout. Make sure MongoDB is running.")
            return False
        except errors.ConnectionFailure:
            self.ui.print_error("MongoDB connection failed.")
            return False
        except Exception as e:
            self.ui.print_error(f"MongoDB connection error: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.is_connected = False
            self.ui.print_info("Disconnected from MongoDB")
    
    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> bool:
        """
        Save analysis result to MongoDB with datetime
        
        Args:
            analysis_data: Complete analysis results dictionary
            
        Returns:
            bool: True if saved successfully
        """
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            # Prepare document for MongoDB
            document = {
                "timestamp": datetime.now(timezone.utc),
                "analysis_data": analysis_data,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert document
            result = self.collection.insert_one(document)
            
            if result.inserted_id:
                self.ui.print_success(f"Analysis result saved to MongoDB with ID: {result.inserted_id}")
                return True
            else:
                self.ui.print_error("Failed to save analysis result to MongoDB")
                return False
                
        except Exception as e:
            self.ui.print_error(f"Error saving to MongoDB: {e}")
            return False
    
    def get_recent_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent analysis results
        
        Args:
            limit: Number of recent records to retrieve
            
        Returns:
            List of analysis results
        """
        if not self.is_connected:
            if not self.connect():
                return []
        
        try:
            cursor = self.collection.find().sort("timestamp", -1).limit(limit)
            results = list(cursor)
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                result['_id'] = str(result['_id'])
            
            return results
            
        except Exception as e:
            self.ui.print_error(f"Error retrieving from MongoDB: {e}")
            return []
    
    def test_connection(self) -> bool:
        """Test MongoDB connection"""
        try:
            if not self.is_connected:
                return self.connect()
            
            # Test with a simple query
            self.collection.count_documents({})
            return True
            
        except Exception as e:
            self.ui.print_error(f"MongoDB connection test failed: {e}")
            return False
    
    def create_indexes(self) -> bool:
        """Create useful indexes on the collection"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            # Create indexes for better query performance
            self.collection.create_index("timestamp")
            self.collection.create_index("analysis_data.symbol")
            self.collection.create_index([("timestamp", -1), ("analysis_data.symbol", 1)])
            
            self.ui.print_success("MongoDB indexes created successfully")
            return True
            
        except Exception as e:
            self.ui.print_error(f"Error creating MongoDB indexes: {e}")
            return False 