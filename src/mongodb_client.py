"""
MongoDB client for storing analysis results
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pymongo import MongoClient, errors
# Removed message formatter dependency for simplified system
from src.config import get_settings

logger = logging.getLogger(__name__)

class MongoDBClient:
    """MongoDB client for analysis results storage"""
    
    def __init__(self):
        """Initialize MongoDB client"""
        self.logger = logging.getLogger("mongodb")
        self.settings = get_settings()
        self.client = None
        self.db = None
        self.is_connected = False
        
        # Collection names with text prefix to avoid conflicts
        self.accounts_collection = "accounts"
        self.positions_collection = "positions" 
        self.trades_collection = "trades"
        self.analysis_collection = "analysis"
        
    def log_message(self, message: str, level: str = "info"):
        """Send log message"""
        self.logger.log(getattr(logging, level.upper()), f"[MongoDB] {message}")

    def connect(self) -> bool:
        """Connect to MongoDB database"""
        try:
            # Connect to MongoDB
            self.client = MongoClient(
                self.settings.MONGODB_URI,
                serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT * 1000
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[self.settings.DATABASE_NAME]
            
            # # Create indexes
            # self.create_indexes()
            
            self.is_connected = True
            self.log_message("Connected to MongoDB successfully", "info")
            return True
            
        except Exception as e:
            self.log_message(f"MongoDB connection error: {e}", "error")
            return False

    def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.is_connected = False
            self.log_message("Disconnected from MongoDB", "info")

    def insert_document(self, collection: str, document: Dict) -> bool:
        """Insert a document into collection"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            result = self.db[collection].insert_one(document)
            if result.acknowledged:
                self.log_message(f"Document inserted into {collection}", "info")
                return True
            return False
        except Exception as e:
            self.log_message(f"Error inserting document: {e}", "error")
            return False

    def find_document(self, collection: str, query: Dict) -> Optional[Dict]:
        """Find a document in collection"""
        if not self.is_connected:
            if not self.connect():
                return None
        
        try:
            return self.db[collection].find_one(query)
        except Exception as e:
            self.log_message(f"Error finding document: {e}", "error")
            return None

    def update_document(self, collection: str, query: Dict, update: Dict) -> bool:
        """Update a document in collection"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            result = self.db[collection].update_one(query, {"$set": update})
            if result.modified_count > 0:
                self.log_message(f"Document updated in {collection}", "info")
                return True
            return False
        except Exception as e:
            self.log_message(f"Error updating document: {e}", "error")
            return False

    def delete_document(self, collection: str, query: Dict) -> bool:
        """Delete a document from collection"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            result = self.db[collection].delete_one(query)
            if result.deleted_count > 0:
                self.log_message(f"Document deleted from {collection}", "info")
                return True
            return False
        except Exception as e:
            self.log_message(f"Error deleting document: {e}", "error")
            return False

    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> Optional[str]:
        """
        Save analysis result to MongoDB with datetime
        
        Args:
            analysis_data: Complete analysis results dictionary
            
        Returns:
            str: MongoDB document ID if saved successfully, None otherwise
        """
        if not self.is_connected:
            if not self.connect():
                return None
        
        try:
            # Prepare document for MongoDB
            document = {
                "timestamp": datetime.now(timezone.utc),
                "analysis_data": analysis_data,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert document
            result = self.db[self.analysis_collection].insert_one(document)
            
            if result.inserted_id:
                document_id = str(result.inserted_id)
                self.log_message(f"Analysis result saved to MongoDB with ID: {document_id}", "info")
                return document_id
            else:
                self.log_message("Failed to save analysis result to MongoDB", "error")
                return None
                
        except Exception as e:
            self.log_message(f"Error saving to MongoDB: {e}", "error")
            return None
    
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
            cursor = self.db[self.analysis_collection].find().sort("timestamp", -1).limit(limit)
            results = list(cursor)
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                result['_id'] = str(result['_id'])
            
            return results
            
        except Exception as e:
            self.log_message(f"Error retrieving from MongoDB: {e}", "error")
            return []

    def get_historical_data(self, symbol: str, start_time: str, end_time: str) -> List[Dict[str, Any]]:
        """
        Get historical price data for a symbol within the specified time range
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')
            start_time: Start time in ISO format
            end_time: End time in ISO format
            
        Returns:
            List of historical price data points
        """
        if not self.is_connected:
            if not self.connect():
                return []
        
        try:
            # Get historical data collection
            historical_collection = self.db['historical_data']
            
            # Query for data within time range
            query = {
                'symbol': symbol,
                'timestamp': {
                    '$gte': start_time,
                    '$lte': end_time
                }
            }
            
            # Sort by timestamp ascending
            cursor = historical_collection.find(query).sort('timestamp', 1)
            
            # Convert cursor to list
            data = list(cursor)
            
            # Convert ObjectId to string for JSON serialization
            for item in data:
                if '_id' in item:
                    item['_id'] = str(item['_id'])
            
            if not data:
                self.log_message(f"No historical data found for {symbol} between {start_time} and {end_time}", "warning")
            else:
                self.log_message(f"Retrieved {len(data)} historical data points for {symbol}", "info")
            
            return data
            
        except Exception as e:
            self.log_message(f"Error retrieving historical data from MongoDB: {e}", "error")
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
            self.log_message(f"MongoDB connection test failed: {e}", "error")
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
            
            self.log_message("MongoDB indexes created successfully", "info")
            return True
            
        except Exception as e:
            self.log_message(f"Error creating MongoDB indexes: {e}", "error")
            return False 