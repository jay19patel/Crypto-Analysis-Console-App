"""
Async MongoDB client using motor for trading system
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import motor.motor_asyncio
from pymongo import errors
from src.config import get_settings
from pymongo import MongoClient

logger = logging.getLogger(__name__)


class AsyncMongoDBClient:
    """Async MongoDB client using motor for trading system - Singleton pattern"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern - ensure only one instance"""
        if cls._instance is None:
            cls._instance = super(AsyncMongoDBClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize async MongoDB client - only once"""
        if self._initialized:
            return
            
        self.logger = logging.getLogger("mongodb.async")
        self.settings = get_settings()
        self.client = None
        self.db = None
        self.is_connected = False
        self.indexes_created = False  # Track if indexes have been created
        
        # Collection names
        self.accounts_collection = "accounts"
        self.positions_collection = "positions"
        self.orders_collection = "orders"
        self.liveprice = "liveprice"
        self.notifications  = "notifications"
        self.signals_collection = "signals"
        
        self._initialized = True
        
    def log_message(self, message: str, level: str = "info"):
        """Send log message"""
        self.logger.log(getattr(logging, level.upper()), f"[AsyncMongoDB] {message}")

    async def connect(self) -> bool:
        """Connect to MongoDB database asynchronously"""
        try:
            if self.is_connected or self.client:
                return True
            
            # Connect to MongoDB using motor
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                self.settings.MONGODB_URI,
                serverSelectionTimeoutMS=self.settings.MONGODB_TIMEOUT * 1000
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            # Get database
            self.db = self.client[self.settings.DATABASE_NAME]
            
            # Create indexes only if not already created
            if not self.indexes_created:
                await self.create_indexes()
                self.indexes_created = True
            
            self.is_connected = True
            self.log_message("Connected to MongoDB successfully", "info")
            return True
            
        except Exception as e:
            self.log_message(f"MongoDB connection error: {e}", "error")
            return False

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.is_connected = False
            self.indexes_created = False  # Reset indexes flag on disconnect
            self.log_message("Disconnected from MongoDB", "info")

    async def create_indexes(self) -> bool:
        """Create useful indexes on collections"""
        if self.is_connected or self.client:
            return True
        
        try:
            # Create indexes for accounts collection
            await self.db[self.accounts_collection].create_index("id", unique=True)
            await self.db[self.accounts_collection].create_index("last_trade_date")
            
            # Create indexes for positions collection
            await self.db[self.positions_collection].create_index("id", unique=True)
            await self.db[self.positions_collection].create_index("symbol")
            await self.db[self.positions_collection].create_index("status")
            await self.db[self.positions_collection].create_index("entry_time")
            
            
            # Create indexes for analysis collection
            await self.db[self.analysis_collection].create_index("timestamp")
            await self.db[self.analysis_collection].create_index("analysis_data.symbol")
            
            self.log_message("MongoDB indexes created successfully", "info")
            return True
            
        except Exception as e:
            self.log_message(f"Error creating MongoDB indexes: {e}", "error")
            return False

    async def insert_document(self, collection: str, document: Dict) -> bool:
        """Insert a document into collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        try:
            result = await self.db[collection].insert_one(document)
            if result.acknowledged:
                self.log_message(f"Document inserted into {collection}", "info")
                return True
            return False
        except Exception as e:
            self.log_message(f"Error inserting document: {e}", "error")
            return False

    async def find_document(self, collection: str, query: Dict) -> Optional[Dict]:
        """Find a document in collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return None
        
        try:
            return await self.db[collection].find_one(query)
        except Exception as e:
            self.log_message(f"Error finding document: {e}", "error")
            return None

    async def find_documents(self, collection: str, query: Dict, limit: int = 0) -> List[Dict]:
        """Find multiple documents in collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return []
        
        try:
            cursor = self.db[collection].find(query)
            if limit > 0:
                cursor = cursor.limit(limit)
            
            documents = await cursor.to_list(length=None)
            
            # Convert ObjectId to string for JSON serialization
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])
            
            return documents
        except Exception as e:
            self.log_message(f"Error finding documents: {e}", "error")
            return []

    async def update_document(self, collection: str, query: Dict, update: Dict) -> bool:
        """Update a document in collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        try:
            result = await self.db[collection].update_one(query, {"$set": update})
            if result.modified_count > 0:
                self.log_message(f"Document updated in {collection}", "info")
                return True
            return False
        except Exception as e:
            self.log_message(f"Error updating document: {e}", "error")
            return False

    async def replace_document(self, collection: str, query: Dict, document: Dict) -> bool:
        """Replace a document in collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        try:
            result = await self.db[collection].replace_one(query, document, upsert=True)
            if result.acknowledged:
                self.log_message(f"Document replaced in {collection}", "info")
                return True
            return False
        except Exception as e:
            self.log_message(f"Error replacing document: {e}", "error")
            return False

    async def delete_document(self, collection: str, query: Dict) -> bool:
        """Delete a document from collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        try:
            result = await self.db[collection].delete_one(query)
            if result.deleted_count > 0:
                self.log_message(f"Document deleted from {collection}", "info")
                return True
            return False
        except Exception as e:
            self.log_message(f"Error deleting document: {e}", "error")
            return False

    async def delete_collection(self, collection: str) -> bool:
        """Delete entire collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return False
        
        try:
            await self.db[collection].drop()
            self.log_message(f"Collection {collection} deleted", "info")
            return True
        except Exception as e:
            self.log_message(f"Error deleting collection {collection}: {e}", "error")
            return False

    async def delete_all_data(self) -> bool:
        """Delete all trading data from database"""
        if not self.is_connected:
            if not await self.connect():
                return False
        try:
            # Delete all collections
            collections = [self.accounts_collection, self.positions_collection, 
                         self.orders_collection, self.liveprice,self.notifications,self.signals_collection]
            
            for collection in collections:
                await self.delete_collection(collection)
            
            self.log_message("All trading data deleted from database", "info")
            return True
        except Exception as e:
            self.log_message(f"Error deleting all data: {e}", "error")
            return False

    # Account Management
    async def save_account(self, account_data: Dict[str, Any]) -> bool:
        """Save account data to MongoDB"""
        try:
            # Ensure account has timestamp
            if "last_updated" not in account_data:
                account_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            return await self.replace_document(
                self.accounts_collection, 
                {"id": account_data["id"]}, 
                account_data
            )
        except Exception as e:
            self.log_message(f"Error saving account: {e}", "error")
            return False

    async def load_account(self, account_id: str = "main") -> Optional[Dict[str, Any]]:
        """Load account data from MongoDB"""
        try:
            return await self.find_document(self.accounts_collection, {"id": account_id})
        except Exception as e:
            self.log_message(f"Error loading account: {e}", "error")
            return None

    # Position Management
    async def save_position(self, position_data: Dict[str, Any]) -> bool:
        """Save position data to MongoDB"""
        try:
            # Ensure position has timestamp
            if "last_updated" not in position_data:
                position_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            
            return await self.replace_document(
                self.positions_collection, 
                {"id": position_data["id"]}, 
                position_data
            )
        except Exception as e:
            self.log_message(f"Error saving position: {e}", "error")
            return False

    async def load_positions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Load positions from MongoDB"""
        try:
            query = {}
            if status:
                query["status"] = status
            
            return await self.find_documents(self.positions_collection, query)
        except Exception as e:
            self.log_message(f"Error loading positions: {e}", "error")
            return []

    async def delete_position(self, position_id: str) -> bool:
        """Delete position from MongoDB"""
        try:
            return await self.delete_document(self.positions_collection, {"id": position_id})
        except Exception as e:
            self.log_message(f"Error deleting position: {e}", "error")
            return False


    # Signal Management
    async def save_signal(self, signal_data: Dict[str, Any]) -> bool:
        """Save strategy signal data to MongoDB"""
        try:
            # Ensure signal has timestamp
            if "timestamp" not in signal_data:
                signal_data["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            return await self.insert_document(self.signals_collection, signal_data)
        except Exception as e:
            self.log_message(f"Error saving signal: {e}", "error")
            return False

    async def load_signals(self, limit: int = 100, skip: int = 0, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Load strategy signals from MongoDB with filtering"""
        try:
            if not self.is_connected:
                if not await self.connect():
                    return []
                
            # Build query filters
            query = {}
            if filters:
                if filters.get('symbol'):
                    query['symbol'] = {'$regex': filters['symbol'], '$options': 'i'}
                if filters.get('strategy'):
                    query['strategy_name'] = {'$regex': filters['strategy'], '$options': 'i'}
                if filters.get('search'):
                    search_term = filters['search']
                    query['$or'] = [
                        {'symbol': {'$regex': search_term, '$options': 'i'}},
                        {'strategy_name': {'$regex': search_term, '$options': 'i'}},
                        {'signal': {'$regex': search_term, '$options': 'i'}}
                    ]
                # Date range filter
                if filters.get('date_from') or filters.get('date_to'):
                    date_filter = {}
                    if filters.get('date_from'):
                        try:
                            date_filter['$gte'] = datetime.fromisoformat(filters['date_from'].replace('Z', '+00:00'))
                        except ValueError:
                            pass  # Skip invalid date format
                    if filters.get('date_to'):
                        try:
                            date_filter['$lte'] = datetime.fromisoformat(filters['date_to'].replace('Z', '+00:00'))
                        except ValueError:
                            pass  # Skip invalid date format
                    if date_filter:
                        query['timestamp'] = date_filter
            
            # Execute query with pagination
            cursor = self.db[self.signals_collection].find(query).sort("timestamp", -1).skip(skip).limit(limit)
            signals = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for signal in signals:
                if '_id' in signal:
                    signal['_id'] = str(signal['_id'])
            
            return signals
        except Exception as e:
            self.log_message(f"Error loading signals: {e}", "error")
            return []

    async def get_signals_count(self, filters: Dict[str, Any] = None) -> int:
        """Get total count of signals matching filters"""
        try:
            if not self.is_connected:
                if not await self.connect():
                    return 0
            
            # Build query filters (same as in load_signals)
            query = {}
            if filters:
                if filters.get('symbol'):
                    query['symbol'] = {'$regex': filters['symbol'], '$options': 'i'}
                if filters.get('strategy'):
                    query['strategy_name'] = {'$regex': filters['strategy'], '$options': 'i'}
                if filters.get('search'):
                    search_term = filters['search']
                    query['$or'] = [
                        {'symbol': {'$regex': search_term, '$options': 'i'}},
                        {'strategy_name': {'$regex': search_term, '$options': 'i'}},
                        {'signal': {'$regex': search_term, '$options': 'i'}}
                    ]
                # Date range filter
                if filters.get('date_from') or filters.get('date_to'):
                    date_filter = {}
                    if filters.get('date_from'):
                        try:
                            date_filter['$gte'] = datetime.fromisoformat(filters['date_from'].replace('Z', '+00:00'))
                        except ValueError:
                            pass  # Skip invalid date format
                    if filters.get('date_to'):
                        try:
                            date_filter['$lte'] = datetime.fromisoformat(filters['date_to'].replace('Z', '+00:00'))
                        except ValueError:
                            pass  # Skip invalid date format
                    if date_filter:
                        query['timestamp'] = date_filter
            
            return await self.db[self.signals_collection].count_documents(query)
        except Exception as e:
            self.log_message(f"Error counting signals: {e}", "error")
            return 0

    # Analysis Management
    async def save_analysis_result(self, analysis_data: Dict[str, Any]) -> Optional[str]:
        """Save analysis result to MongoDB"""
        if not self.is_connected:
            if not await self.connect():
                return None
        
        try:
            # Prepare document for MongoDB
            document = {
                "timestamp": datetime.now(timezone.utc),
                "analysis_data": analysis_data,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Insert document
            result = await self.db[self.analysis_collection].insert_one(document)
            
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

    async def get_recent_analyses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent analysis results"""
        if not self.is_connected:
            if not await self.connect():
                return []
        
        try:
            cursor = self.db[self.analysis_collection].find().sort("timestamp", -1).limit(limit)
            results = await cursor.to_list(length=None)
            
            # Convert ObjectId to string for JSON serialization
            for result in results:
                result['_id'] = str(result['_id'])
            
            return results
            
        except Exception as e:
            self.log_message(f"Error retrieving from MongoDB: {e}", "error")
            return []

    async def test_connection(self) -> bool:
        """Test MongoDB connection"""
        try:
            if not self.is_connected:
                return await self.connect()
            
            # Test with a simple query
            await self.db[self.accounts_collection].count_documents({})
            return True
            
        except Exception as e:
            self.log_message(f"MongoDB connection test failed: {e}", "error")
            return False
    
    @classmethod
    def reset_instance(cls):
        """Reset singleton instance for testing purposes"""
        if cls._instance:
            cls._instance = None
            cls._initialized = False 

    async def save_live_price_async(self, market_data):
        """Save a MarketData object (or dict) to the 'liveprice' collection asynchronously"""
        if not self.is_connected:
            if not await self.connect():
                return False
        try:
            # Convert to dict if needed
            if hasattr(market_data, '__dict__'):
                doc = dict(market_data.__dict__)
            else:
                doc = dict(market_data)
            # Convert timestamp to ISO if needed
            if 'timestamp' in doc and hasattr(doc['timestamp'], 'isoformat'):
                doc['timestamp'] = doc['timestamp'].isoformat()
            await self.db[self.liveprice].insert_one(doc)
            self.log_message(f"Live price saved for {doc.get('symbol', '?')}", "info")
            return True
        except Exception as e:
            self.log_message(f"Error saving live price: {e}", "error")
            return False 

    async def cleanup_old_data(self, days: int = 90) -> None:
        """Delete trades, positions, and notifications older than 'days' days for data retention."""
        if not self.is_connected:
            if not await self.connect():
                self.log_message("Could not connect to MongoDB for cleanup", "error")
                return
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        try:
            # Remove old positions
            result_positions = await self.db[self.positions_collection].delete_many({"exit_time": {"$lt": cutoff_iso}})
            # Remove old notifications
            result_notifications = await self.db[self.notifications].delete_many({"timestamp": {"$lt": cutoff_iso}})
            self.log_message(f"Cleanup complete: {result_positions.deleted_count} positions, {result_notifications.deleted_count} notifications deleted.", "info")
        except Exception as e:
            self.log_message(f"Error during cleanup: {e}", "error")

    # Order Management
    async def save_order(self, order_data: Dict[str, Any]) -> bool:
        """Save order data to MongoDB"""
        try:
            # Ensure order has timestamp
            if "order_time" not in order_data:
                order_data["order_time"] = datetime.now(timezone.utc).isoformat()
            
            return await self.insert_document(self.orders_collection, order_data)
        except Exception as e:
            self.log_message(f"Error saving order: {e}", "error")
            return False

    async def load_orders(self, position_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Load orders from MongoDB, optionally filtered by position_id"""
        try:
            query = {}
            if position_id:
                query["position_id"] = position_id
            
            if not self.is_connected:
                if not await self.connect():
                    return []
                    
            cursor = self.db[self.orders_collection].find(query).sort("order_time", -1).limit(limit)
            orders = await cursor.to_list(length=None)
            
            # Convert ObjectId to string
            for order in orders:
                if '_id' in order:
                    order['_id'] = str(order['_id'])
            
            return orders
        except Exception as e:
            self.log_message(f"Error loading orders: {e}", "error")
            return []

    async def load_orders_by_symbol(self, symbol: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Load orders for a specific symbol"""
        try:
            query = {"symbol": symbol}
            return await self.find_documents(self.orders_collection, query, limit=limit)
        except Exception as e:
            self.log_message(f"Error loading orders by symbol: {e}", "error")
            return [] 