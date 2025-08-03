"""
REST API Server for Trading Dashboard
Provides API endpoints for historical data, closed positions, notifications, and strategies
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from src.config import get_settings
from src.database.mongodb_client import AsyncMongoDBClient
from src.database.schemas import NotificationLog


class FilterRequest(BaseModel):
    """Request model for filtering data"""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    symbol: Optional[str] = None
    strategy: Optional[str] = None
    status: Optional[str] = None
    position_type: Optional[str] = None
    page: Optional[int] = 1
    limit: Optional[int] = 50
    search: Optional[str] = None


class NotificationFilter(BaseModel):
    """Request model for filtering notifications"""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    level: Optional[str] = None
    type: Optional[str] = None
    page: Optional[int] = 1
    limit: Optional[int] = 50
    search: Optional[str] = None


class TradingRestAPI:
    """REST API server for trading dashboard"""
    
    def __init__(self, host: str = "localhost", port: int = 8766):
        self.host = host
        self.port = port
        self.settings = get_settings()
        self.logger = logging.getLogger("rest_api")
        self.mongodb_client = AsyncMongoDBClient()
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Trading Dashboard API",
            description="REST API for trading dashboard data",
            version="1.0.0"
        )
        
        # Setup templates with absolute path
        import os
        template_dir = os.path.join(os.getcwd(), "templates")
        self.templates = Jinja2Templates(directory=template_dir)
        
        # Add CORS middleware with proper configuration
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["*"]
        )
        
        # Setup routes
        self._setup_routes()
        
        # SSE connections tracking
        self.sse_connections: Dict[str, asyncio.Queue] = {}
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/")
        async def root():
            return {"message": "Trading Dashboard API", "version": "1.0.0", "dashboard_url": "/dashboard"}
        
        @self.app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard(request: Request):
            """Serve the trading dashboard"""
            return self.templates.TemplateResponse("dash.html", {"request": request})

        @self.app.get("/README.md")
        async def get_readme():
            """Serve the README.md file"""
            try:
                readme_path = "README.md"
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="README.md not found")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error reading README.md: {str(e)}")
        
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "api_version": "1.0.0"
            }
        
        @self.app.options("/{path:path}")
        async def options_handler(path: str):
            """Handle preflight CORS requests"""
            return JSONResponse(
                content={},
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400"
                }
            )
        
        # Closed Positions Endpoints
        @self.app.get("/api/positions/closed")
        async def get_closed_positions(
            date_from: Optional[str] = Query(None),
            date_to: Optional[str] = Query(None),
            symbol: Optional[str] = Query(None),
            strategy: Optional[str] = Query(None),
            position_type: Optional[str] = Query(None),
            page: int = Query(1, ge=1),
            limit: int = Query(50, ge=1, le=200),
            search: Optional[str] = Query(None)
        ):
            """Get closed positions with filters and pagination"""
            try:
                filters = {}
                
                # Add status filter for closed positions
                filters["status"] = "CLOSED"
                
                # Date range filter
                if date_from or date_to:
                    date_filter = {}
                    if date_from:
                        date_filter["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                    if date_to:
                        date_filter["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                    filters["exit_time"] = date_filter
                
                # Symbol filter
                if symbol:
                    filters["symbol"] = {"$regex": symbol, "$options": "i"}
                
                # Strategy filter
                if strategy:
                    filters["strategy_name"] = {"$regex": strategy, "$options": "i"}
                
                # Position type filter
                if position_type:
                    filters["position_type"] = position_type.upper()
                
                # Search filter
                if search:
                    search_filter = {
                        "$or": [
                            {"symbol": {"$regex": search, "$options": "i"}},
                            {"strategy_name": {"$regex": search, "$options": "i"}},
                            {"notes": {"$regex": search, "$options": "i"}}
                        ]
                    }
                    filters.update(search_filter)
                
                # Calculate skip for pagination
                skip = (page - 1) * limit
                
                # Get positions from database using available methods
                if not await self.mongodb_client.connect():
                    raise HTTPException(status_code=500, detail="Database connection failed")
                
                positions_collection = self.mongodb_client.db["positions"]
                positions_cursor = positions_collection.find(filters).sort("exit_time", -1).skip(skip).limit(limit)
                positions = await positions_cursor.to_list(length=limit)
                
                # Get total count for pagination
                total_count = await positions_collection.count_documents(filters)
                
                # Enhanced position data
                enhanced_positions = []
                for position in positions:
                    enhanced_position = self._enhance_closed_position_api(position)
                    enhanced_positions.append(enhanced_position)
                
                return {
                    "positions": enhanced_positions,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_count,
                        "pages": (total_count + limit - 1) // limit
                    },
                    "filters_applied": {
                        "date_from": date_from,
                        "date_to": date_to,
                        "symbol": symbol,
                        "strategy": strategy,
                        "position_type": position_type,
                        "search": search
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching closed positions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/positions/closed/{position_id}")
        async def get_closed_position(position_id: str):
            """Get specific closed position by ID"""
            try:
                if not await self.mongodb_client.connect():
                    raise HTTPException(status_code=500, detail="Database connection failed")
                    
                position = await self.mongodb_client.find_document("positions", {"id": position_id, "status": "CLOSED"})
                if not position:
                    raise HTTPException(status_code=404, detail="Position not found")
                
                enhanced_position = self._enhance_closed_position_api(position)
                return {
                    "position": enhanced_position,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Error fetching position {position_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Open Positions Endpoints
        @self.app.get("/api/positions/open")
        async def get_open_positions():
            """Get all open positions"""
            try:
                if not await self.mongodb_client.connect():
                    raise HTTPException(status_code=500, detail="Database connection failed")
                
                # Get open positions from MongoDB
                positions_collection = self.mongodb_client.db["positions"]
                positions_cursor = positions_collection.find({"status": "OPEN"})
                positions = await positions_cursor.to_list(length=None)
                
                # Get all positions for total count
                all_positions_cursor = positions_collection.find({"status": "CLOSED"})
                all_closed_positions = await all_positions_cursor.to_list(length=None)
                
                # Process and enhance positions
                enhanced_positions = []
                for position in positions:
                    enhanced_position = self._enhance_open_position_api(position)
                    enhanced_positions.append(enhanced_position)
                
                # Sort by entry time (newest first)
                enhanced_positions.sort(key=lambda x: x.get("entry_time", ""), reverse=True)
                
                return {
                    "positions": enhanced_positions,
                    "total_open": len(enhanced_positions),
                    "total_closed": len(all_closed_positions),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching open positions: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        
        # Helper method to get current price
        async def _get_current_price(self, symbol: str) -> Optional[float]:
            """Get current price for a symbol from live prices"""
            try:
                if not await self.mongodb_client.connect():
                    return None
                
                # Try to get from recent market data
                recent_data = await self.mongodb_client.find_documents("market_data", {"symbol": symbol}, limit=1)
                if recent_data:
                    return recent_data[0].get("price")
                
                # Fallback: try to get from live prices collection if available
                live_price = await self.mongodb_client.find_document("live_prices", {"symbol": symbol})
                if live_price:
                    return live_price.get("price")
                
                return None
            except Exception as e:
                self.logger.error(f"Error getting current price for {symbol}: {e}")
                return None
        
        # Notifications Endpoints
        @self.app.get("/api/notifications")
        async def get_notifications(
            date_from: Optional[str] = Query(None),
            date_to: Optional[str] = Query(None),
            level: Optional[str] = Query(None),
            notification_type: Optional[str] = Query(None),
            page: int = Query(1, ge=1),
            limit: int = Query(50, ge=1, le=200),
            search: Optional[str] = Query(None)
        ):
            """Get notifications with filters and pagination"""
            try:
                filters = {}
                
                # Date range filter
                if date_from or date_to:
                    date_filter = {}
                    if date_from:
                        date_filter["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                    if date_to:
                        date_filter["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                    filters["timestamp"] = date_filter
                
                # Level filter
                if level:
                    filters["priority"] = level.lower()
                
                # Type filter
                if notification_type:
                    filters["type"] = {"$regex": notification_type, "$options": "i"}
                
                # Search filter
                if search:
                    search_filter = {
                        "$or": [
                            {"title": {"$regex": search, "$options": "i"}},
                            {"message": {"$regex": search, "$options": "i"}},
                            {"symbol": {"$regex": search, "$options": "i"}}
                        ]
                    }
                    filters.update(search_filter)
                
                # Calculate skip for pagination
                skip = (page - 1) * limit
                
                # Get notifications from database
                if not await self.mongodb_client.connect():
                    raise HTTPException(status_code=500, detail="Database connection failed")
                
                notifications_collection = self.mongodb_client.db["notifications"]
                notifications_cursor = notifications_collection.find(filters).sort("timestamp", -1).skip(skip).limit(limit)
                notifications = await notifications_cursor.to_list(length=limit)
                
                # Get total count for pagination
                total_count = await notifications_collection.count_documents(filters)
                
                # Format notifications
                formatted_notifications = []
                for notification in notifications:
                    formatted_notification = {
                        "id": str(notification.get("_id", "")),
                        "type": notification.get("type", "info"),
                        "level": notification.get("priority", "info"),
                        "title": notification.get("title", ""),
                        "message": notification.get("message", ""),
                        "symbol": notification.get("symbol"),
                        "timestamp": notification.get("timestamp", datetime.now(timezone.utc)).isoformat(),
                        "data": notification.get("data", {}),
                        "status": notification.get("status", "sent")
                    }
                    formatted_notifications.append(formatted_notification)
                
                return {
                    "notifications": formatted_notifications,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_count,
                        "pages": (total_count + limit - 1) // limit
                    },
                    "filters_applied": {
                        "date_from": date_from,
                        "date_to": date_to,
                        "level": level,
                        "type": notification_type,
                        "search": search
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching notifications: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        
        # Trades Endpoints
        @self.app.get("/api/trades")
        async def get_trades(
            date_from: Optional[str] = Query(None),
            date_to: Optional[str] = Query(None),
            symbol: Optional[str] = Query(None),
            strategy: Optional[str] = Query(None),
            position_type: Optional[str] = Query(None),
            page: int = Query(1, ge=1),
            limit: int = Query(50, ge=1, le=200),
            search: Optional[str] = Query(None)
        ):
            """Get all trades (closed positions) with filters and pagination"""
            try:
                filters = {}
                
                # Add status filter for closed positions
                filters["status"] = "CLOSED"
                
                # Date range filter
                if date_from or date_to:
                    date_filter = {}
                    if date_from:
                        date_filter["$gte"] = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                    if date_to:
                        date_filter["$lte"] = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                    filters["exit_time"] = date_filter
                
                # Symbol filter
                if symbol:
                    filters["symbol"] = {"$regex": symbol, "$options": "i"}
                
                # Strategy filter
                if strategy:
                    filters["strategy_name"] = {"$regex": strategy, "$options": "i"}
                
                # Position type filter
                if position_type:
                    filters["position_type"] = position_type.upper()
                
                # Search filter
                if search:
                    search_filter = {
                        "$or": [
                            {"symbol": {"$regex": search, "$options": "i"}},
                            {"strategy_name": {"$regex": search, "$options": "i"}},
                            {"notes": {"$regex": search, "$options": "i"}}
                        ]
                    }
                    filters.update(search_filter)
                
                # Calculate skip for pagination
                skip = (page - 1) * limit
                
                # Get trades from database using available methods
                if not await self.mongodb_client.connect():
                    raise HTTPException(status_code=500, detail="Database connection failed")
                
                positions_collection = self.mongodb_client.db["positions"]
                positions_cursor = positions_collection.find(filters).sort("exit_time", -1).skip(skip).limit(limit)
                trades = await positions_cursor.to_list(length=limit)
                
                # Get total count for pagination
                total_count = await positions_collection.count_documents(filters)
                
                # Enhanced trade data
                enhanced_trades = []
                for trade in trades:
                    enhanced_trade = self._enhance_closed_position_api(trade)
                    enhanced_trades.append(enhanced_trade)
                
                return {
                    "trades": enhanced_trades,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_count,
                        "pages": (total_count + limit - 1) // limit
                    },
                    "filters_applied": {
                        "date_from": date_from,
                        "date_to": date_to,
                        "symbol": symbol,
                        "strategy": strategy,
                        "position_type": position_type,
                        "search": search
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching trades: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # Signals Endpoints
        @self.app.get("/api/signals")
        async def get_signals(
            page: int = Query(1, ge=1),
            limit: int = Query(50, ge=1, le=200),
            strategy: Optional[str] = Query(None),
            symbol: Optional[str] = Query(None),
            search: Optional[str] = Query(None),
            date_from: Optional[str] = Query(None),
            date_to: Optional[str] = Query(None)
        ):
            """Get trading signals with filters and pagination"""
            try:
                if not await self.mongodb_client.connect():
                    raise HTTPException(status_code=500, detail="Database connection failed")
                
                # Build filters
                filters = {}
                if strategy:
                    filters['strategy'] = strategy
                if symbol:
                    filters['symbol'] = symbol
                if search:
                    filters['search'] = search
                if date_from:
                    filters['date_from'] = date_from
                if date_to:
                    filters['date_to'] = date_to
                
                # Calculate skip for pagination
                skip = (page - 1) * limit
                
                # Get signals from database using new methods
                signals = await self.mongodb_client.load_signals(limit=limit, skip=skip, filters=filters)
                total_count = await self.mongodb_client.get_signals_count(filters=filters)
                
                # Format signals
                formatted_signals = []
                for signal in signals:
                    formatted_signal = {
                        "id": str(signal.get("_id", "")),
                        "strategy_name": signal.get("strategy_name", ""),
                        "symbol": signal.get("symbol", ""),
                        "signal": signal.get("signal", ""),
                        "confidence": signal.get("confidence", 0.0),
                        "price": signal.get("price", 0.0),
                        "timestamp": signal.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        "indicators": signal.get("indicators", {}),
                        "data": signal.get("data", {})
                    }
                    formatted_signals.append(formatted_signal)
                
                return {
                    "signals": formatted_signals,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_count,
                        "pages": (total_count + limit - 1) // limit
                    },
                    "filters_applied": {
                        "strategy": strategy,
                        "symbol": symbol,
                        "date_from": date_from,
                        "date_to": date_to
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching signals: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        
        # Server-Sent Events endpoint for real-time updates
        @self.app.get("/api/events/stream")
        async def stream_events():
            """SSE endpoint for real-time updates"""
            async def event_stream():
                client_id = f"sse_{datetime.now().timestamp()}"
                queue = asyncio.Queue()
                self.sse_connections[client_id] = queue
                
                try:
                    # Send initial connection event
                    yield f"data: {json.dumps({'type': 'connected', 'client_id': client_id, 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                    
                    while True:
                        # Wait for new events
                        try:
                            event = await asyncio.wait_for(queue.get(), timeout=30.0)
                            yield f"data: {json.dumps(event)}\n\n"
                        except asyncio.TimeoutError:
                            # Send heartbeat
                            yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.now(timezone.utc).isoformat()})}\n\n"
                        except asyncio.CancelledError:
                            break
                finally:
                    # Clean up connection
                    if client_id in self.sse_connections:
                        del self.sse_connections[client_id]
            
            return StreamingResponse(
                event_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Cache-Control"
                }
            )
        
        # Analytics Endpoints
        @self.app.get("/api/analytics/summary")
        async def get_analytics_summary():
            """Get trading analytics summary"""
            try:
                # Get date range (last 30 days)
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=30)
                
                # Get closed positions in date range
                if not await self.mongodb_client.connect():
                    raise HTTPException(status_code=500, detail="Database connection failed")
                
                positions_collection = self.mongodb_client.db["positions"]
                positions_cursor = positions_collection.find({
                    "status": "CLOSED",
                    "exit_time": {"$gte": start_date, "$lte": end_date}
                })
                positions = await positions_cursor.to_list(length=None)
                
                # Calculate analytics
                total_trades = len(positions)
                profitable_trades = len([p for p in positions if p.get("pnl", 0) > 0])
                total_pnl = sum(p.get("pnl", 0) for p in positions)
                total_fees = sum(p.get("trading_fee", 0) for p in positions)
                
                # Strategy breakdown
                strategy_stats = {}
                for position in positions:
                    strategy = position.get("strategy_name", "Unknown")
                    if strategy not in strategy_stats:
                        strategy_stats[strategy] = {"trades": 0, "pnl": 0.0, "wins": 0}
                    strategy_stats[strategy]["trades"] += 1
                    strategy_stats[strategy]["pnl"] += position.get("pnl", 0)
                    if position.get("pnl", 0) > 0:
                        strategy_stats[strategy]["wins"] += 1
                
                # Calculate win rates for strategies
                for strategy in strategy_stats:
                    trades = strategy_stats[strategy]["trades"]
                    wins = strategy_stats[strategy]["wins"]
                    strategy_stats[strategy]["win_rate"] = (wins / trades * 100) if trades > 0 else 0
                
                return {
                    "period": {
                        "start_date": start_date.isoformat(),
                        "end_date": end_date.isoformat(),
                        "days": 30
                    },
                    "trading_summary": {
                        "total_trades": total_trades,
                        "profitable_trades": profitable_trades,
                        "win_rate": (profitable_trades / total_trades * 100) if total_trades > 0 else 0,
                        "total_pnl": total_pnl,
                        "total_fees": total_fees,
                        "net_pnl": total_pnl - total_fees,
                        "avg_pnl_per_trade": total_pnl / total_trades if total_trades > 0 else 0
                    },
                    "strategy_breakdown": strategy_stats,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                self.logger.error(f"Error fetching analytics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _enhance_closed_position_api(self, position: Dict) -> Dict:
        """Enhance closed position data for API response"""
        entry_time = position.get('entry_time')
        exit_time = position.get('exit_time')
        
        # Calculate holding time
        holding_time = None
        holding_seconds = None
        if entry_time and exit_time:
            if isinstance(entry_time, str):
                entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            else:
                entry_dt = entry_time
            
            if isinstance(exit_time, str):
                exit_dt = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
            else:
                exit_dt = exit_time
            
            duration = exit_dt - entry_dt
            holding_seconds = duration.total_seconds()
            
            days = duration.days
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                holding_time = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                holding_time = f"{hours}h {minutes}m"
            else:
                holding_time = f"{minutes}m"
        
        # Calculate total investment
        margin_used = position.get('margin_used', 0.0)
        leverage = position.get('leverage', 1.0)
        total_investment = margin_used * leverage
        
        return {
            'id': position.get('id'),
            'symbol': position.get('symbol'),
            'type': position.get('position_type', 'LONG'),
            'entry_price': position.get('entry_price', 0.0),
            'exit_price': position.get('exit_price', 0.0),
            'entry_time': entry_time.isoformat() if isinstance(entry_time, datetime) else entry_time,
            'exit_time': exit_time.isoformat() if isinstance(exit_time, datetime) else exit_time,
            'entry_datetime': entry_time.isoformat() if isinstance(entry_time, datetime) else entry_time,  # Alias for compatibility
            'exit_datetime': exit_time.isoformat() if isinstance(exit_time, datetime) else exit_time,  # Alias for compatibility
            'quantity': position.get('quantity', 0.0),
            'leverage': leverage,
            'margin_used': margin_used,
            'total_investment': total_investment,
            'pnl': position.get('pnl', 0.0),
            'realized_pnl': position.get('pnl', 0.0),  # Alias for frontend compatibility
            'pnl_percentage': position.get('pnl_percentage', 0.0),
            'strategy': position.get('strategy_name', 'Unknown'),
            'side': position.get('position_type', 'LONG'),  # Alias for frontend compatibility
            'holding_time': holding_time,
            'holding_seconds': holding_seconds,
            'trading_fee': position.get('trading_fee', 0.0),
            'net_pnl': position.get('pnl', 0.0) - position.get('trading_fee', 0.0),
            'close_reason': position.get('notes', 'Manual Close'),
            'stop_loss': position.get('stop_loss'),
            'target': position.get('target'),
            'status': position.get('status', 'CLOSED')
        }
    
    def _enhance_open_position_api(self, position: Dict) -> Dict:
        """Enhance open position data for API response"""
        entry_time = position.get('entry_time')
        
        # Calculate holding time (since entry)
        holding_time = None
        holding_seconds = None
        if entry_time:
            if isinstance(entry_time, str):
                entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            else:
                entry_dt = entry_time
            
            current_dt = datetime.now(timezone.utc)
            duration = current_dt - entry_dt
            holding_seconds = duration.total_seconds()
            
            days = duration.days
            hours, remainder = divmod(duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                holding_time = f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                holding_time = f"{hours}h {minutes}m"
            else:
                holding_time = f"{minutes}m"
        
        # Calculate total investment
        margin_used = position.get('margin_used', 0.0)
        leverage = position.get('leverage', 1.0)
        total_investment = margin_used * leverage
        
        return {
            'id': position.get('id'),
            'symbol': position.get('symbol'),
            'type': position.get('position_type', 'LONG'),
            'entry_price': position.get('entry_price', 0.0),
            'current_price': position.get('current_price', position.get('entry_price', 0.0)),
            'entry_time': entry_time.isoformat() if isinstance(entry_time, datetime) else entry_time,
            'entry_datetime': entry_time.isoformat() if isinstance(entry_time, datetime) else entry_time,  # Alias for compatibility
            'quantity': position.get('quantity', 0.0),
            'leverage': leverage,
            'margin_used': margin_used,
            'total_investment': total_investment,
            'pnl': position.get('pnl', 0.0),
            'pnl_percentage': position.get('pnl_percentage', 0.0),
            'strategy': position.get('strategy_name', 'Unknown'),
            'side': position.get('position_type', 'LONG'),  # Alias for frontend compatibility
            'holding_time': holding_time,
            'holding_seconds': holding_seconds,
            'trading_fee': position.get('trading_fee', 0.0),
            'stop_loss': position.get('stop_loss'),
            'target': position.get('target'),
            'status': position.get('status', 'OPEN')
        }
    
    async def send_sse_event(self, event_type: str, data: Dict):
        """Send event to all SSE connections"""
        if not self.sse_connections:
            return
        
        event = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Send to all connected clients
        disconnected_clients = []
        for client_id, queue in self.sse_connections.items():
            try:
                await queue.put(event)
            except Exception as e:
                self.logger.debug(f"Failed to send SSE event to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.sse_connections:
                del self.sse_connections[client_id]
    
    async def start_server(self):
        """Start the REST API server"""
        try:
            self.logger.info(f"🚀 Starting REST API server on {self.host}:{self.port}")
            
            config = uvicorn.Config(
                app=self.app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=True
            )
            
            server = uvicorn.Server(config)
            await server.serve()
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start REST API server: {e}")
            raise


# Global REST API server instance
_rest_api_server: Optional[TradingRestAPI] = None


def get_rest_api_server() -> TradingRestAPI:
    """Get the global REST API server instance"""
    global _rest_api_server
    if _rest_api_server is None:
        _rest_api_server = TradingRestAPI()
    return _rest_api_server


async def start_rest_api_server(host: str = "localhost", port: int = 8766) -> TradingRestAPI:
    """Start the REST API server"""
    server = get_rest_api_server()
    server.host = host
    server.port = port
    
    await server.start_server()
    return server