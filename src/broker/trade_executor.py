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
        analysis_data: Optional[Dict[str, Any]] = None,
        leverage: Optional[float] = None,
        analysis_id: str = ""
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
        
        # Check and reset daily trades for new day first
        if not self.account_manager.check_and_reset_daily_trades():
            self.ui.print_error("Failed to check daily trades status")
            return False
        
        # Get actual daily position count from database
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        actual_daily_count = self.account_manager.get_daily_positions_count(today)
        
        # Check if we can trade today based on actual database count
        account = self.account_manager.get_account()
        if not account:
            self.ui.print_warning("Account not available")
            return False
        
        if actual_daily_count >= account.daily_trades_limit:
            self.ui.print_warning(f"Cannot execute trade: Daily limit reached ({actual_daily_count}/{account.daily_trades_limit}) positions taken today")
            return False
        
        # Determine position type
        position_type = PositionType.LONG if signal == 'BUY' else PositionType.SHORT
        
        # Check if we can open this type of position
        if not self.position_manager.can_open_position(symbol, position_type):
            return False
        
        # Set default leverage if not provided
        if leverage is None:
            leverage = self.settings.BROKER_DEFAULT_LEVERAGE
        
        # Ensure leverage is within limits
        account = self.account_manager.get_account()
        max_leverage = account.max_leverage if account else self.settings.BROKER_MAX_LEVERAGE
        if leverage > max_leverage:
            leverage = max_leverage
            self.ui.print_warning(f"Leverage reduced to maximum allowed: {max_leverage}x")
        
        # Calculate position size with margin requirements
        position_value, margin_required, trading_fee = self.account_manager.calculate_position_size(
            current_price, leverage=leverage
        )
        
        if position_value <= 0 or margin_required <= 0:
            self.ui.print_warning("Cannot execute trade: Insufficient margin or invalid position size")
            return False
        
        # Calculate quantity based on position value
        quantity = position_value / current_price
        
        # Calculate stop loss and target
        stop_loss, target = self._calculate_risk_levels(
            current_price, 
            position_type,
            self.stop_loss_percentage,
            self.target_percentage
        )
        
        # Reserve margin and pay trading fee (deduct from current balance)
        if not self.account_manager.reserve_margin(margin_required, trading_fee):
            self.ui.print_error("Failed to reserve margin for trade")
            return False
        
        # Create position with margin details
        position = self.position_manager.create_position(
            symbol=symbol,
            position_type=position_type,
            entry_price=current_price,
            quantity=quantity,
            invested_amount=position_value,
            strategy_name=strategy_name,
            stop_loss=stop_loss,
            target=target,
            leverage=leverage,
            margin_used=margin_required,
            trading_fee=trading_fee,
            analysis_id=analysis_id
        )
        
        if position:
            # Sync daily trades count with actual database count after position creation
            self.account_manager.sync_daily_trades_after_position_creation()
            
            # Get updated account for display
            account = self.account_manager.get_account()
            
            # Enhanced logging for margin trade execution
            leverage_text = f" | {leverage}x Leverage" if leverage > 1 else ""
            margin_text = f" | Margin: ${margin_required:.2f}" if leverage > 1 else ""
            fee_text = f" | Fee: ${trading_fee:.2f}" if trading_fee > 0 else ""
            balance_text = f" | Balance: ${account.current_balance:.2f}"
            trades_text = f" | Daily Trades: {account.daily_trades_count}/{account.daily_trades_limit}"
            self.ui.print_success(f"🚀 TRADE EXECUTED: {signal} {symbol} at ${current_price:.2f} | Value: ${position_value:.2f}{leverage_text}{margin_text}{fee_text}{balance_text}{trades_text} | SL: ${stop_loss:.2f} | Target: ${target:.2f}")
            
            # Save trade execution details
            if analysis_data:
                self._log_trade_execution(position, analysis_data, confidence)
            
            return True
        else:
            # Release margin if position creation failed (add back to balance)
            self.account_manager.release_margin(margin_required, 0, -trading_fee)  # Negative fee to refund
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
            
            # Check margin health for leveraged positions
            margin_health = self.position_manager.check_margin_health(current_prices)
            
            # Issue warnings for positions at risk
            if margin_health['margin_call_positions'] > 0:
                self.ui.print_warning(f"⚠️  MARGIN CALL: {margin_health['margin_call_positions']} position(s) need attention")
            
            if margin_health['positions_near_liquidation'] > 0:
                self.ui.print_error(f"🚨 LIQUIDATION WARNING: {margin_health['positions_near_liquidation']} position(s) at high risk")
            
            # Check for positions approaching 48-hour time limit
            approaching_limit = self.position_manager.get_positions_approaching_time_limit()
            if approaching_limit:
                for pos in approaching_limit:
                    holding_hours = self.position_manager.get_holding_time_hours(pos)
                    self.ui.print_warning(f"⏰ Position {pos.symbol} approaching time limit: {holding_hours:.1f}/48 hours")
            
            # Check stop loss and targets
            closed_positions.extend(self.position_manager.check_stop_loss_and_targets(current_prices))
            
            # Check and close expired positions
            closed_positions.extend(self.position_manager.check_and_close_expired_positions(current_prices))
            
            # Release margin for all closed positions
            for position_id in closed_positions:
                position = self.position_manager.get_position_by_id(position_id)
                if position and position.status == PositionStatus.CLOSED:
                    # Release margin with PnL and exit fee
                    exit_fee = position.trading_fee * 0.5  # Exit fee is half of entry fee
                    self.account_manager.release_margin(position.margin_used, position.pnl, exit_fee)
                    
                    # Log margin release
                    balance_after = self.account_manager.get_account().current_balance
                    self.ui.print_info(f"💰 Margin released: ${position.margin_used:.2f} + P&L: ${position.pnl:.2f} - Exit fee: ${exit_fee:.2f} | Balance: ${balance_after:.2f}")
            
            # Update account statistics if any positions were closed
            if closed_positions:
                all_positions = self.position_manager.positions
                self.account_manager.update_statistics(all_positions)
            
        except Exception as e:
            self.ui.print_error(f"Error checking positions: {e}")
        
        return closed_positions
    
    def force_close_position(
        self,
        position_id: str,
        current_price: float,
        reason: str = "Manual close"
    ) -> bool:
        """Force close a position manually"""
        
        try:
            # Close the position
            if self.position_manager.close_position(position_id, current_price, reason):
                # Get the closed position to release margin
                position = self.position_manager.get_position_by_id(position_id)
                if position and position.status == PositionStatus.CLOSED:
                    # Release margin with PnL and exit fee
                    exit_fee = position.trading_fee * 0.5  # Exit fee is half of entry fee
                    self.account_manager.release_margin(position.margin_used, position.pnl, exit_fee)
                    
                    # Log the closure with balance update
                    balance_after = self.account_manager.get_account().current_balance
                    pnl_emoji = "🟢" if position.pnl >= 0 else "🔴"
                    pnl_symbol = "+" if position.pnl >= 0 else ""
                    self.ui.print_success(f"✅ Position manually closed: {position.symbol} | {pnl_emoji} P&L: {pnl_symbol}${position.pnl:.2f} | Balance: ${balance_after:.2f}")
                    
                    # Update account statistics
                    all_positions = self.position_manager.positions
                    self.account_manager.update_statistics(all_positions)
                    
                return True
                
        except Exception as e:
            self.ui.print_error(f"Error force closing position: {e}")
        
        return False
    
    def get_trading_summary(self) -> Dict[str, Any]:
        """Get trading summary for display"""
        positions_summary = self.position_manager.get_positions_summary_with_time_info()
        account_summary = self.account_manager.get_account_summary()
        
        return {
            'account': account_summary,
            'positions': positions_summary,
            'trading_status': {
                'can_trade_today': account_summary.get('daily_trades_count', 0) < account_summary.get('daily_trades_limit', 5),
                'trades_remaining': max(0, account_summary.get('daily_trades_limit', 5) - account_summary.get('daily_trades_count', 0)),
                'stop_loss_percentage': self.stop_loss_percentage * 100,
                'target_percentage': self.target_percentage * 100,
                'min_confidence_threshold': self.min_confidence_threshold,
                'max_holding_time_hours': self.position_manager.settings.BROKER_MAX_HOLDING_HOURS
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