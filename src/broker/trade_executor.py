"""
Trade Executor for broker system
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from src.broker.models import Position, PositionType, PositionStatus
from src.broker.account_manager import AccountManager
from src.broker.position_manager import PositionManager
from src.ui.console import ConsoleUI
from src.config import get_settings


class TradeExecutor:
    """Executes trades based on analysis signals"""
    
    def __init__(self, ui: ConsoleUI, account_manager: AccountManager, position_manager: PositionManager):
        """Initialize trade executor"""
        self.ui = ui
        self.account_manager = account_manager
        self.position_manager = position_manager
        self.settings = get_settings()
        
        # Trading settings from config
        self.stop_loss_percentage = self.settings.BROKER_STOP_LOSS_PCT
        self.target_percentage = self.settings.BROKER_TARGET_PCT
        self.min_confidence_threshold = self.settings.BROKER_MIN_CONFIDENCE
    
    def process_signal(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        current_price: float,
        strategy_name: str = "",
        analysis_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Process trading signal and execute if conditions are met"""
        
        signal = signal.upper().strip()
        
        # Validate signal
        if signal not in ['BUY', 'SELL']:
            self.ui.print_warning(f"⚠️  Invalid signal: {signal} - Only BUY/SELL allowed")
            return False
        
        # Check confidence threshold
        if confidence < self.min_confidence_threshold:
            self.ui.print_warning(f"❌ Signal ignored: {signal} | Confidence: {confidence:.1f}% < {self.min_confidence_threshold}%")
            return False
        
        # Check if we can trade today
        account = self.account_manager.get_account()
        if not account or not account.can_trade_today():
            self.ui.print_warning("Cannot execute trade: Daily limit reached or account not available")
            return False
        
        # Determine position type
        position_type = PositionType.LONG if signal == 'BUY' else PositionType.SHORT
        
        # Check if we can open this type of position
        if not self.position_manager.can_open_position(symbol, position_type):
            return False
        
        # Calculate position size
        position_amount = self.account_manager.calculate_position_size(current_price)
        
        if position_amount <= 0:
            self.ui.print_warning("Cannot execute trade: Insufficient funds")
            return False
        
        # Calculate quantity
        quantity = position_amount / current_price
        
        # Calculate stop loss and target
        stop_loss, target = self._calculate_risk_levels(
            current_price, 
            position_type,
            self.stop_loss_percentage,
            self.target_percentage
        )
        
        # Reserve funds
        if not self.account_manager.reserve_funds(position_amount):
            self.ui.print_error("Failed to reserve funds for trade")
            return False
        
        # Create position
        position = self.position_manager.create_position(
            symbol=symbol,
            position_type=position_type,
            entry_price=current_price,
            quantity=quantity,
            invested_amount=position_amount,
            strategy_name=strategy_name,
            stop_loss=stop_loss,
            target=target
        )
        
        if position:
            # Enhanced logging for trade execution
            self.ui.print_success(f"🚀 TRADE EXECUTED: {signal} {symbol} at ${current_price:.2f} | Amount: ${position_amount:.2f} | SL: ${stop_loss:.2f} | Target: ${target:.2f}")
            
            # Save trade execution details
            if analysis_data:
                self._log_trade_execution(position, analysis_data, confidence)
            
            return True
        else:
            # Release funds if position creation failed
            self.account_manager.update_balance(position_amount, "Trade execution failed - funds released")
            return False
    
    def _calculate_risk_levels(
        self,
        entry_price: float,
        position_type: PositionType,
        stop_loss_pct: float,
        target_pct: float
    ) -> tuple[float, float]:
        """Calculate stop loss and target levels"""
        
        if position_type == PositionType.LONG:
            # For long positions: SL below entry, target above entry
            stop_loss = entry_price * (1 - stop_loss_pct)
            target = entry_price * (1 + target_pct)
        else:
            # For short positions: SL above entry, target below entry
            stop_loss = entry_price * (1 + stop_loss_pct)
            target = entry_price * (1 - target_pct)
        
        return stop_loss, target
    
    def _log_trade_execution(
        self,
        position: Position,
        analysis_data: Dict[str, Any],
        confidence: float
    ) -> None:
        """Log trade execution details"""
        try:
            # Add trade execution details to position notes
            execution_details = {
                'execution_time': datetime.now(timezone.utc).isoformat(),
                'signal_confidence': confidence,
                'analysis_summary': analysis_data.get('consensus_signal', {}),
                'market_conditions': {
                    'rsi': analysis_data.get('indicators', {}).get('RSI_14', {}).get('value', 'N/A'),
                    'trend': analysis_data.get('consensus_signal', {}).get('interpretation', 'N/A')
                }
            }
            
            position.notes = f"Auto-executed | Confidence: {confidence:.1f}% | {execution_details}"
            self.position_manager.save_position(position)
            
        except Exception as e:
            self.ui.print_warning(f"Failed to log trade execution details: {e}")
    
    def check_open_positions(self, current_prices: Dict[str, float]) -> List[str]:
        """Check open positions for stop loss/target hits"""
        closed_positions = []
        
        try:
            # Update PnL for all positions
            self.position_manager.update_positions_pnl(current_prices)
            
            # Check stop loss and targets
            closed_position_ids = self.position_manager.check_stop_loss_and_targets(current_prices)
            
            # Process closed positions
            for position_id in closed_position_ids:
                position = self.position_manager.get_position_by_id(position_id)
                if position and position.status == PositionStatus.CLOSED:
                    # Release funds back to account
                    self.account_manager.release_funds(position.invested_amount, position.pnl)
                    closed_positions.append(position_id)
                    
                    # Update account statistics
                    all_positions = self.position_manager.positions
                    self.account_manager.update_statistics(all_positions)
            
            return closed_positions
            
        except Exception as e:
            self.ui.print_error(f"Error checking positions: {e}")
            return []
    
    def force_close_position(
        self,
        position_id: str,
        current_price: float,
        reason: str = "Manual close"
    ) -> bool:
        """Force close a position manually"""
        
        position = self.position_manager.get_position_by_id(position_id)
        if not position:
            self.ui.print_error(f"Position {position_id} not found")
            return False
        
        if position.status != PositionStatus.OPEN:
            self.ui.print_warning(f"Position {position_id} is not open")
            return False
        
        # Close the position
        if self.position_manager.close_position(position_id, current_price, reason):
            # Release funds back to account
            self.account_manager.release_funds(position.invested_amount, position.pnl)
            
            # Update account statistics
            all_positions = self.position_manager.positions
            self.account_manager.update_statistics(all_positions)
            
            return True
        
        return False
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """Get trading summary for display"""
        positions_summary = self.position_manager.get_positions_summary()
        account_summary = self.account_manager.get_account_summary()
        
        return {
            'account': account_summary,
            'positions': positions_summary,
            'trading_status': {
                'can_trade_today': account_summary.get('daily_trades_count', 0) < account_summary.get('daily_trades_limit', 5),
                'trades_remaining': max(0, account_summary.get('daily_trades_limit', 5) - account_summary.get('daily_trades_count', 0)),
                'stop_loss_percentage': self.stop_loss_percentage * 100,
                'target_percentage': self.target_percentage * 100,
                'min_confidence_threshold': self.min_confidence_threshold
            }
        }
    
    def update_risk_settings(
        self,
        stop_loss_percentage: Optional[float] = None,
        target_percentage: Optional[float] = None,
        min_confidence_threshold: Optional[float] = None
    ) -> None:
        """Update risk management settings"""
        
        if stop_loss_percentage is not None:
            self.stop_loss_percentage = stop_loss_percentage
            self.ui.print_info(f"Stop loss percentage updated to {stop_loss_percentage * 100:.1f}%")
        
        if target_percentage is not None:
            self.target_percentage = target_percentage
            self.ui.print_info(f"Target percentage updated to {target_percentage * 100:.1f}%")
        
        if min_confidence_threshold is not None:
            self.min_confidence_threshold = min_confidence_threshold
            self.ui.print_info(f"Minimum confidence threshold updated to {min_confidence_threshold:.1f}%")
    
    def get_position_details(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific position"""
        position = self.position_manager.get_position_by_id(position_id)
        
        if not position:
            return None
        
        return {
            'id': position.id,
            'symbol': position.symbol,
            'type': position.position_type.value,
            'status': position.status.value,
            'entry_price': position.entry_price,
            'exit_price': position.exit_price,
            'quantity': position.quantity,
            'invested_amount': position.invested_amount,
            'current_pnl': position.pnl,
            'profit_after_amount': position.profit_after_amount,
            'stop_loss': position.stop_loss,
            'target': position.target,
            'holding_time': position.holding_time,
            'strategy': position.strategy_name,
            'entry_time': position.entry_time,
            'exit_time': position.exit_time,
            'notes': position.notes
        } 