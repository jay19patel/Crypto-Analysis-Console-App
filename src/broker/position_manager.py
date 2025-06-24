"""
Position Manager for broker system
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pymongo import MongoClient
from src.broker.models import Position, PositionType, PositionStatus
from src.config import get_settings
from src.ui.console import ConsoleUI


class PositionManager:
    """Manages trading positions"""
    
    def __init__(self, ui: ConsoleUI):
        """Initialize position manager"""
        self.ui = ui
        self.settings = get_settings()
        self.client = None
        self.db = None
        self.positions_collection = None
        self.positions: List[Position] = []
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
            self.positions_collection = self.db['positions']
            
            self.is_connected = True
            return True
            
        except Exception as e:
            self.ui.print_error(f"MongoDB connection error: {e}")
            return False
    
    def load_positions(self) -> bool:
        """Load all positions from database"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            cursor = self.positions_collection.find({}).sort("created_at", -1)
            self.positions = []
            
            for doc in cursor:
                position = Position.from_dict(doc)
                self.positions.append(position)
            
            self.ui.print_success(f"Loaded {len(self.positions)} positions")
            return True
            
        except Exception as e:
            self.ui.print_error(f"Error loading positions: {e}")
            return False
    
    def save_position(self, position: Position) -> bool:
        """Save position to database"""
        if not self.is_connected:
            return False
        
        try:
            position_data = position.to_dict()
            
            # Update or insert position
            result = self.positions_collection.replace_one(
                {'id': position.id},
                position_data,
                upsert=True
            )
            
            return result.acknowledged
            
        except Exception as e:
            self.ui.print_error(f"Error saving position: {e}")
            return False
    
    def create_position(
        self,
        symbol: str,
        position_type: PositionType,
        entry_price: float,
        quantity: float,
        invested_amount: float,
        strategy_name: str = "",
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        leverage: float = 1.0,
        margin_used: float = 0.0,
        trading_fee: float = 0.0,
        analysis_id: str = ""
    ) -> Optional[Position]:
        """Create a new position"""
        
        # Check if we can open this position type
        if not self.can_open_position(symbol, position_type):
            return None
        
        # Create position
        position = Position()
        position.symbol = symbol
        position.position_type = position_type
        position.entry_price = entry_price
        position.quantity = quantity
        position.invested_amount = invested_amount
        position.strategy_name = strategy_name
        position.stop_loss = stop_loss
        position.target = target
        position.leverage = leverage
        position.margin_used = margin_used
        position.trading_fee = trading_fee
        position.analysis_id = analysis_id
        position.status = PositionStatus.OPEN
        
        # Calculate initial PnL (should be 0)
        position.calculate_pnl(entry_price)
        
        # Save to database
        if self.save_position(position):
            self.positions.append(position)
            self.ui.print_success(f"Created {position_type.value} position for {symbol} at ${entry_price:.2f}")
            return position
        
        return None
    
    def close_position(
        self,
        position_id: str,
        exit_price: float,
        reason: str = ""
    ) -> bool:
        """Close a position"""
        
        position = self.get_position_by_id(position_id)
        if not position:
            self.ui.print_error(f"Position {position_id} not found")
            return False
        
        if position.status != PositionStatus.OPEN:
            self.ui.print_warning(f"Position {position_id} is not open")
            return False
        
        # Close the position
        position.close_position(exit_price)
        position.notes = reason
        
        # Save to database
        if self.save_position(position):
            # Simple one-line logging for position closure
            pnl_emoji = "🟢" if position.pnl >= 0 else "🔴"
            pnl_symbol = "+" if position.pnl >= 0 else ""
            
            self.ui.print_warning(f"🔔 POSITION CLOSED: {position.position_type.value} {position.symbol} at ${exit_price:.2f} | {pnl_emoji} P&L: {pnl_symbol}${position.pnl:.2f} | {reason}")
            return True
        
        return False
    
    def get_open_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get all open positions, optionally filtered by symbol"""
        open_positions = [p for p in self.positions if p.status == PositionStatus.OPEN]
        
        if symbol:
            open_positions = [p for p in open_positions if p.symbol == symbol]
        
        return open_positions
    
    def get_closed_positions(self, limit: int = 10) -> List[Position]:
        """Get recent closed positions"""
        closed_positions = [p for p in self.positions if p.status == PositionStatus.CLOSED]
        # Sort by exit time, most recent first
        closed_positions.sort(key=lambda x: x.exit_time or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return closed_positions[:limit]
    
    def get_position_by_id(self, position_id: str) -> Optional[Position]:
        """Get position by ID"""
        for position in self.positions:
            if position.id == position_id:
                return position
        return None
    
    def can_open_position(self, symbol: str, position_type: PositionType) -> bool:
        """Check if can open position of given type for symbol"""
        # Check if there's already an open position of the same type for this symbol
        open_positions = self.get_open_positions(symbol)
        
        for pos in open_positions:
            if pos.position_type == position_type:
                self.ui.print_warning(
                    f"Cannot open {position_type.value} position for {symbol}: "
                    f"Already have open {position_type.value} position"
                )
                return False
        
        return True
    
    def update_positions_pnl(self, current_prices: Dict[str, float]) -> None:
        """Update PnL for all open positions"""
        for position in self.get_open_positions():
            if position.symbol in current_prices:
                position.calculate_pnl(current_prices[position.symbol])
                position.calculate_holding_time()
                # Save updated position
                self.save_position(position)
    
    def check_stop_loss_and_targets(self, current_prices: Dict[str, float]) -> List[str]:
        """Check margin liquidation, stop loss and targets for open positions"""
        positions_to_close = []
        
        for position in self.get_open_positions():
            if position.symbol not in current_prices:
                continue
                
            current_price = current_prices[position.symbol]
            should_close = False
            reason = ""
            
            # PRIORITY 1: Check margin liquidation first (higher priority than stop loss)
            if position.should_liquidate(current_price, self.settings.BROKER_LIQUIDATION_THRESHOLD):
                should_close = True
                margin_usage = position.calculate_margin_usage(current_price)
                reason = f"💀 MARGIN LIQUIDATION: Loss {margin_usage*100:.1f}% of margin used | Price: ${current_price:.2f}"
            
            # PRIORITY 2: Check stop loss only if no liquidation and position still open
            elif position.stop_loss and position.status == PositionStatus.OPEN:
                if position.position_type == PositionType.LONG and current_price <= position.stop_loss:
                    should_close = True
                    reason = f"🛡️ Stop Loss Hit: ${current_price:.2f} <= ${position.stop_loss:.2f}"
                elif position.position_type == PositionType.SHORT and current_price >= position.stop_loss:
                    should_close = True
                    reason = f"🛡️ Stop Loss Hit: ${current_price:.2f} >= ${position.stop_loss:.2f}"
            
            # PRIORITY 3: Check target only if no liquidation/stop loss hit
            elif position.target and position.status == PositionStatus.OPEN:
                if position.position_type == PositionType.LONG and current_price >= position.target:
                    should_close = True
                    reason = f"🎯 Target Hit: ${current_price:.2f} >= ${position.target:.2f}"
                elif position.position_type == PositionType.SHORT and current_price <= position.target:
                    should_close = True
                    reason = f"🎯 Target Hit: ${current_price:.2f} <= ${position.target:.2f}"
            
            # If position should be closed, close it
            if should_close:
                if self.close_position(position.id, current_price, reason):
                    positions_to_close.append(position.id)
        
        return positions_to_close
    
    def check_margin_health(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """Check margin health for all open positions"""
        margin_stats = {
            'positions_at_risk': [],
            'total_margin_used': 0.0,
            'positions_near_liquidation': 0,
            'margin_call_positions': 0
        }
        
        for position in self.get_open_positions():
            if position.symbol not in current_prices or position.leverage <= 1:
                continue
            
            current_price = current_prices[position.symbol]
            margin_usage = position.calculate_margin_usage(current_price)
            margin_stats['total_margin_used'] += position.margin_used
            
            position_risk = {
                'id': position.id,
                'symbol': position.symbol,
                'margin_usage': margin_usage,
                'margin_used': position.margin_used,
                'leverage': position.leverage,
                'current_pnl': position.calculate_pnl(current_price)
            }
            
            # Check if position is at risk
            if margin_usage >= self.settings.BROKER_LIQUIDATION_THRESHOLD:
                position_risk['status'] = 'LIQUIDATION_RISK'
                margin_stats['positions_near_liquidation'] += 1
                margin_stats['positions_at_risk'].append(position_risk)
            elif margin_usage >= self.settings.BROKER_MARGIN_CALL_THRESHOLD:
                position_risk['status'] = 'MARGIN_CALL'
                margin_stats['margin_call_positions'] += 1
                margin_stats['positions_at_risk'].append(position_risk)
        
        return margin_stats
    
    def calculate_unrealized_pnl(self, current_prices: Dict[str, float]) -> float:
        """Calculate total unrealized PnL"""
        total_pnl = 0.0
        
        for position in self.get_open_positions():
            if position.symbol in current_prices:
                position.calculate_pnl(current_prices[position.symbol])
                total_pnl += position.pnl
        
        return total_pnl
    
    def get_positions_summary(self) -> Dict[str, Any]:
        """Get positions summary for display"""
        open_positions = self.get_open_positions()
        closed_positions = self.get_closed_positions()
        
        total_open_value = sum(pos.invested_amount for pos in open_positions)
        total_unrealized_pnl = sum(pos.pnl for pos in open_positions)
        
        return {
            'total_positions': len(self.positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_open_value': total_open_value,
            'total_unrealized_pnl': total_unrealized_pnl,
            'open_positions_list': open_positions,
            'recent_closed_positions': closed_positions[:5]
        }
    
    def set_stop_loss(self, position_id: str, stop_loss: float) -> bool:
        """Set stop loss for a position"""
        position = self.get_position_by_id(position_id)
        if not position:
            return False
        
        position.stop_loss = stop_loss
        position.updated_at = datetime.now(timezone.utc)
        
        return self.save_position(position)
    
    def set_target(self, position_id: str, target: float) -> bool:
        """Set target for a position"""
        position = self.get_position_by_id(position_id)
        if not position:
            return False
        
        position.target = target
        position.updated_at = datetime.now(timezone.utc)
        
        return self.save_position(position)
    
    def disconnect(self) -> None:
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.is_connected = False 