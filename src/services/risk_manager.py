"""
Simplified Async Risk Management System
Basic risk monitoring with dummy data and essential functionality
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from src.broker.models import Position, PositionType, PositionStatus
from src.config import get_settings, get_trading_config
from src.services.notifications import NotificationManager


class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAction(Enum):
    """Risk management actions"""
    MONITOR = "monitor"
    TIGHTEN_STOP_LOSS = "tighten_stop_loss"
    CLOSE_POSITION = "close_position"
    REDUCE_POSITION = "reduce_position"
    ACTIVATE_TRAILING = "activate_trailing"
    EMERGENCY_CLOSE = "emergency_close"


@dataclass
class RiskMetrics:
    """Risk metrics for a position"""
    position_id: str
    symbol: str
    risk_level: RiskLevel
    margin_usage: float
    pnl_percentage: float
    holding_time_hours: float
    distance_from_stop_loss: float
    distance_from_target: float
    volatility_score: float
    recommendation: RiskAction
    trailing_stop_price: Optional[float] = None
    risk_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "risk_level": self.risk_level.value,
            "margin_usage": self.margin_usage,
            "pnl_percentage": self.pnl_percentage,
            "holding_time_hours": self.holding_time_hours,
            "distance_from_stop_loss": self.distance_from_stop_loss,
            "distance_from_target": self.distance_from_target,
            "volatility_score": self.volatility_score,
            "recommendation": self.recommendation.value,
            "trailing_stop_price": self.trailing_stop_price,
            "risk_score": self.risk_score
        }


class AsyncRiskManager:
    """Simplified async risk management system"""
    
    def __init__(self, broker):
        """Initialize async risk manager"""
        self.broker = broker
        self.settings = get_settings()
        self.trading_config = get_trading_config()
        self.logger = logging.getLogger("risk_manager.async")
        
        # Simplified configuration - no complex risk thresholds needed
        
        # Risk tracking
        self._risk_metrics: Dict[str, RiskMetrics] = {}
        self._trailing_states: Dict[str, Dict] = {}
        
        # Performance tracking
        self._risk_decisions = []
        self._execution_times = {}
        
        # Warning spam prevention
        self._last_warning_time = {}  # Track last warning time per symbol/type
        self._warning_cooldown = 300  # 5 minutes between same warnings
        
        # Notification system
        self.notification_manager = NotificationManager()
        
        self.logger.info("Simplified async risk manager initialized")
    
    async def start(self):
        """Start async risk management system"""
        try:
            self.logger.info("Starting simplified async risk management system")
            
            # Note: Notification manager is started by main trading system
            # Don't start it here to avoid conflicts
            
            self.logger.info("Simplified async risk management system started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start async risk manager: {e}")
            return False
    
    async def stop(self):
        """Stop async risk management system"""
        self.logger.info("Stopping simplified async risk management system")
        
        # Note: Notification manager is stopped by main trading system
        
        self.logger.info("Simplified async risk management system stopped")
    
    async def analyze_position_risk_async(self, position: Position, current_price: float) -> RiskMetrics:
        """Analyze position risk asynchronously"""
        try:
            # Calculate basic metrics
            pnl_percentage = (position.pnl / position.invested_amount) * 100 if position.invested_amount > 0 else 0
            
            # Calculate holding time
            entry_time = position.entry_time
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            
            holding_time_hours = (datetime.now(timezone.utc) - entry_time).total_seconds() / 3600
            
            # Calculate margin usage with account balance context
            margin_usage = 0.0
            if position.leverage > 1 and position.margin_used > 0:
                account_balance = self.broker.account.current_balance if self.broker.account else 1000.0
                margin_usage = position.calculate_margin_usage(current_price, account_balance)
            
            # Calculate distances from stop loss and target
            distance_from_sl = 0.0
            distance_from_target = 0.0
            
            if position.stop_loss:
                distance_from_sl = abs(current_price - position.stop_loss) / current_price * 100
            
            if position.target:
                distance_from_target = abs(position.target - current_price) / current_price * 100
            
            # Calculate volatility score (dummy data)
            volatility_score = 50.0  # Fixed moderate score
            
            # Determine risk level
            risk_level = self._determine_risk_level(
                margin_usage, pnl_percentage, holding_time_hours, volatility_score
            )
            
            # Generate recommendation
            recommendation = self._generate_risk_recommendation(
                position, risk_level, pnl_percentage, holding_time_hours, margin_usage
            )
            
            # Check trailing stop
            trailing_stop_price = self._calculate_trailing_stop(position, current_price)
            
            # Calculate overall risk score
            risk_score = self._calculate_risk_score(
                margin_usage, pnl_percentage, holding_time_hours, volatility_score
            )
            
            metrics = RiskMetrics(
                position_id=position.id,
                symbol=position.symbol,
                risk_level=risk_level,
                margin_usage=margin_usage,
                pnl_percentage=pnl_percentage,
                holding_time_hours=holding_time_hours,
                distance_from_stop_loss=distance_from_sl,
                distance_from_target=distance_from_target,
                volatility_score=volatility_score,
                recommendation=recommendation,
                trailing_stop_price=trailing_stop_price,
                risk_score=risk_score
            )
            
            # Cache metrics
            self._risk_metrics[position.id] = metrics
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Risk analysis failed for {position.symbol}: {e}")
            
            # Return safe defaults
            return RiskMetrics(
                position_id=position.id,
                symbol=position.symbol,
                risk_level=RiskLevel.CRITICAL,
                margin_usage=100.0,
                pnl_percentage=0.0,
                holding_time_hours=0.0,
                distance_from_stop_loss=0.0,
                distance_from_target=0.0,
                volatility_score=100.0,
                recommendation=RiskAction.EMERGENCY_CLOSE,
                risk_score=100.0
            )
    
    async def execute_risk_action_async(self, position: Position, risk_metrics: RiskMetrics, current_price: float) -> bool:
        """Execute risk management action asynchronously"""
        try:
            action_taken = False
            
            # Handle trailing stop
            if risk_metrics.trailing_stop_price:
                if self._should_trigger_trailing_stop(position, current_price, risk_metrics.trailing_stop_price):
                    if await self.broker.close_position_async(position.id, current_price, "Trailing Stop Hit"):
                        await self.notification_manager.notify_position_close(
                            symbol=position.symbol,
                            position_id=position.id,
                            exit_price=current_price,
                            pnl=position.pnl,
                            reason="Trailing Stop Hit"
                        )
                        action_taken = True
                else:
                    # Update trailing stop
                    self._update_trailing_stop(position, current_price, risk_metrics.trailing_stop_price)
            
            # LIQUIDATION PROTECTION - AUTO-CLOSE CRITICAL POSITIONS
            if risk_metrics.risk_level == RiskLevel.CRITICAL:
                # Calculate liquidation distance for this position
                liquidation_distance = self._calculate_liquidation_distance(position, current_price)
                
                if liquidation_distance <= 5.0:  # Within 5% of liquidation
                    self.logger.warning(f"🚨 EMERGENCY AUTO-CLOSE: {position.symbol} - Liquidation risk {liquidation_distance:.1f}%")
                    if await self.broker.close_position_async(position.id, current_price, f"LIQUIDATION PROTECTION - Emergency Close"):
                        await self.notification_manager.notify_risk_alert(
                            symbol=position.symbol,
                            alert_type="LIQUIDATION PROTECTION - Auto Close",
                            current_price=current_price,
                            risk_level="EMERGENCY"
                        )
                        action_taken = True
                
                elif risk_metrics.recommendation in [RiskAction.CLOSE_POSITION, RiskAction.EMERGENCY_CLOSE]:
                    if await self.broker.close_position_async(position.id, current_price, f"Risk Management: {risk_metrics.recommendation.value}"):
                        await self.notification_manager.notify_risk_alert(
                            symbol=position.symbol,
                            alert_type="Critical Risk Closure",
                            current_price=current_price,
                            risk_level=risk_metrics.risk_level.value
                        )
                        action_taken = True
            
            # Handle HIGH RISK situations (liquidation approaching)
            elif risk_metrics.risk_level == RiskLevel.HIGH:
                # Calculate liquidation distance for warning
                liquidation_distance = self._calculate_liquidation_distance(position, current_price)
                
                if liquidation_distance <= 15.0:  # Within 15% of liquidation - WARNING
                    warning_key = f"{position.symbol}_liquidation_warning"
                    if self._should_send_warning(warning_key):
                        self.logger.warning(f"⚠️ LIQUIDATION WARNING: {position.symbol} - {liquidation_distance:.1f}% from liquidation")
                        await self.notification_manager.notify_risk_alert(
                            symbol=position.symbol,
                            alert_type=f"LIQUIDATION WARNING - {liquidation_distance:.1f}% away",
                            current_price=current_price,
                            risk_level="HIGH"
                        )
                        self._mark_warning_sent(warning_key)
                        action_taken = True
                
                elif risk_metrics.recommendation == RiskAction.TIGHTEN_STOP_LOSS:
                    new_stop_loss = self._calculate_tighter_stop_loss(position, current_price)
                    if new_stop_loss != position.stop_loss:
                        warning_key = f"{position.symbol}_stop_loss_tighten"
                        if self._should_send_warning(warning_key):
                            await self.notification_manager.notify_risk_alert(
                                symbol=position.symbol,
                                alert_type="Stop Loss Tightened",
                                current_price=current_price,
                                risk_level=risk_metrics.risk_level.value
                            )
                            self._mark_warning_sent(warning_key)
                            action_taken = True
            
            # Handle profit protection
            if risk_metrics.pnl_percentage > 10.0:  # More than 10% profit
                if not self._is_trailing_active(position.id):
                    self._activate_trailing_stop(position, current_price)
                    await self.notification_manager.notify_profit_alert(
                        symbol=position.symbol,
                        pnl=position.pnl,
                        profit_percentage=risk_metrics.pnl_percentage
                    )
                    action_taken = True
            
            return action_taken
            
        except Exception as e:
            self.logger.error(f"Risk action execution failed for {position.symbol}: {e}")
            return False
    
    async def analyze_portfolio_risk_async(self) -> Dict[str, Any]:
        """Analyze overall portfolio risk with proper risk calculation logic"""
        try:
            if not self.broker.positions:
                return {"status": "no_positions", "overall_risk_level": "low"}
            
            if not self.broker.account:
                return {"status": "error", "error": "No account available"}
            
            account_balance = self.broker.account.current_balance
            if account_balance <= 0:
                return {"status": "error", "error": "Invalid account balance"}
            
            # Get open positions only
            open_positions = [pos for pos in self.broker.positions.values() if pos.status.value == "OPEN"]
            
            if not open_positions:
                return {"status": "no_open_positions", "overall_risk_level": "low"}
            
            # Calculate portfolio metrics properly
            position_risks = []
            total_margin_used = 0.0
            total_unrealized_pnl = 0.0
            critical_positions = 0
            high_risk_positions = 0
            
            for position in open_positions:
                # Get current price
                current_price = 0.0
                if position.symbol in self.broker._price_cache:
                    current_price = self.broker._price_cache[position.symbol].get("price", 0.0)
                
                if current_price <= 0:
                    continue  # Skip positions without valid price data
                
                # Update position PnL with current price
                position.calculate_pnl(current_price)
                
                # Get risk metrics for this position
                risk_metrics = await self.analyze_position_risk_async(position, current_price)
                position_risks.append(risk_metrics)
                
                # Accumulate portfolio totals
                total_margin_used += position.margin_used
                total_unrealized_pnl += position.pnl
                
                # Count high-risk positions
                if risk_metrics.risk_level == RiskLevel.CRITICAL:
                    critical_positions += 1
                elif risk_metrics.risk_level == RiskLevel.HIGH:
                    high_risk_positions += 1
            
            # Calculate portfolio risk percentage (PURE margin used as % of account balance)
            portfolio_margin_usage = (total_margin_used / account_balance) * 100 if account_balance > 0 else 0
            
            # Calculate portfolio PnL percentage (separate from margin usage)
            portfolio_pnl_percentage = (total_unrealized_pnl / account_balance) * 100 if account_balance > 0 else 0
            
            # Calculate effective portfolio risk (combines margin + PnL risk with proper weighting)
            portfolio_pnl_risk = abs(portfolio_pnl_percentage) if portfolio_pnl_percentage < 0 else 0
            effective_portfolio_risk = portfolio_margin_usage + (portfolio_pnl_risk * 0.5)  # PnL risk gets 50% weight
            
            # Calculate total portfolio value (balance + unrealized PnL)
            total_portfolio_value = account_balance + total_unrealized_pnl
            
            # Portfolio return percentage from initial balance
            initial_balance = self.broker.account.initial_balance
            portfolio_return_pct = ((total_portfolio_value - initial_balance) / initial_balance) * 100 if initial_balance > 0 else 0
            
            # Smart portfolio risk level determination (now uses improved calculation)
            overall_risk = self._determine_portfolio_risk_level(
                portfolio_margin_usage, portfolio_pnl_percentage, portfolio_return_pct,
                critical_positions, high_risk_positions, len(open_positions),
                effective_portfolio_risk  # Pass the new combined risk metric
            )
            
            # Count positions by risk level
            risk_distribution = {
                "low": len([r for r in position_risks if r.risk_level == RiskLevel.LOW]),
                "medium": len([r for r in position_risks if r.risk_level == RiskLevel.MEDIUM]),
                "high": len([r for r in position_risks if r.risk_level == RiskLevel.HIGH]),
                "critical": len([r for r in position_risks if r.risk_level == RiskLevel.CRITICAL])
            }
            
            # Generate smart recommendations
            recommendations = self._generate_portfolio_recommendations(
                overall_risk, risk_distribution, portfolio_margin_usage, portfolio_pnl_percentage
            )
            
            return {
                "status": "analyzed",
                "overall_risk_level": overall_risk.value,
                "portfolio_margin_usage": portfolio_margin_usage,  # Pure margin usage only
                "portfolio_pnl_percentage": portfolio_pnl_percentage,  # PnL impact only
                "effective_portfolio_risk": effective_portfolio_risk,  # Combined risk with proper weighting
                "portfolio_return_percentage": portfolio_return_pct,
                "total_margin_used": total_margin_used,
                "total_unrealized_pnl": total_unrealized_pnl,
                "account_balance": account_balance,
                "total_portfolio_value": total_portfolio_value,
                "total_positions": len(position_risks),
                "open_positions": len(open_positions),
                "risk_distribution": risk_distribution,
                "position_risks": [
                    {
                        "symbol": r.symbol,
                        "risk_level": r.risk_level.value,
                        "pnl_percentage": r.pnl_percentage,
                        "margin_usage": r.margin_usage,
                        "recommendation": r.recommendation.value,
                        "risk_score": r.risk_score
                    } for r in position_risks
                ],
                "recommendations": recommendations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Portfolio risk analysis failed: {e}")
            return {"status": "error", "error": str(e), "overall_risk_level": "unknown"}
    
    async def calculate_safe_quantity_async(self, symbol: str, price: float, requested_quantity: float, leverage: float = None) -> Tuple[float, str]:
        """Calculate safe quantity with proper position sizing and liquidation protection"""
        try:
            if not self.broker.account:
                return 0.0, "No account available"
            
            # Step 0: ANTI-OVERTRADE CHECK - Check portfolio risk before allowing new trades
            portfolio_risk_data = await self.analyze_portfolio_risk_async()
            if portfolio_risk_data.get("status") == "analyzed":
                portfolio_margin_usage = portfolio_risk_data.get("portfolio_margin_usage", 0.0)
                max_portfolio_risk = self.trading_config.get("max_portfolio_risk_pct", 80.0)
                
                if portfolio_margin_usage >= max_portfolio_risk:
                    return 0.0, f"🚫 ANTI-OVERTRADE: Portfolio risk too high {portfolio_margin_usage:.1f}% >= {max_portfolio_risk}%. Close existing positions first."
                
                # Additional check for high risk warning
                high_risk_threshold = self.trading_config.get("high_risk_margin_pct", 85.0)
                if portfolio_margin_usage >= high_risk_threshold:
                    self.logger.warning(f"⚠️ Portfolio approaching high risk: {portfolio_margin_usage:.1f}% (limit: {max_portfolio_risk}%)")
            
            # Step 1: Check if position already exists for symbol (One position per symbol rule)
            for pos in self.broker.positions.values():
                if pos.symbol == symbol and pos.status.value == "OPEN":
                    return 0.0, f"Position already open for {symbol} ({pos.position_type.value}, qty={pos.quantity}, entry=₹{pos.entry_price:.2f})"
            
            # Step 1.5: Check maximum open positions limit
            open_positions_count = len([pos for pos in self.broker.positions.values() if pos.status.value == "OPEN"])
            max_positions = self.trading_config.get("max_positions_open", 2)  # Updated to 2
            
            if open_positions_count >= max_positions:
                return 0.0, f"Maximum open positions limit reached ({open_positions_count}/{max_positions}). Close some positions first."
            
            # Step 2: Get current available balance
            available_balance = self.broker.account.current_balance
            if available_balance <= 0:
                return 0.0, f"No available balance. Current balance: ₹{available_balance:.2f}"
            
            # Step 3: Use default leverage if not provided
            if leverage is None:
                leverage = self.trading_config.get("default_leverage", 50.0)
            
            # Step 4: Calculate position sizing (% of balance) - Use safe mode for small balances
            # Use safe mode if balance is small or if configured
            use_safe_mode = available_balance <= 1000  # Use safe mode for balances <= 1000
            
            if use_safe_mode:
                balance_per_trade_pct = self.trading_config.get("safe_balance_per_trade_pct", 0.05)  # 5% safe mode
                self.logger.info(f"Using SAFE MODE: {balance_per_trade_pct*100}% per trade for balance ₹{available_balance:.2f}")
            else:
                balance_per_trade_pct = self.trading_config.get("balance_per_trade_pct", 0.20)  # 20% normal mode
                self.logger.info(f"Using NORMAL MODE: {balance_per_trade_pct*100}% per trade for balance ₹{available_balance:.2f}")
            
            margin_to_use = available_balance * balance_per_trade_pct
            
            # Step 5: Calculate position value with leverage
            position_value = margin_to_use * leverage
            
            # Step 6: Calculate quantity from position value  
            calculated_quantity = position_value / price
            
            # Step 7: Apply liquidation protection
            liquidation_buffer = self.trading_config.get("liquidation_buffer_pct", 0.10)  # 10% buffer
            safe_quantity = calculated_quantity * (1 - liquidation_buffer)
            
            # Step 8: Use calculated safe quantity (ignore requested if it's 0 or too small)
            if requested_quantity <= 0 or requested_quantity < safe_quantity * 0.1:
                # Strategy didn't specify quantity or specified tiny amount - use calculated safe quantity
                final_quantity = safe_quantity
                self.logger.info(f"🎯 Using calculated quantity: {safe_quantity:.6f} (strategy requested: {requested_quantity:.6f})")
            else:
                # Strategy specified reasonable quantity - take minimum for safety
                final_quantity = min(requested_quantity, safe_quantity)
                self.logger.info(f"🎯 Using safer quantity: {final_quantity:.6f} (requested: {requested_quantity:.6f}, calculated: {safe_quantity:.6f})")
            
            # Step 9: Ensure minimum viable trade size
            min_trade_size = 0.001  
            if final_quantity < min_trade_size:
                return 0.0, f"Calculated quantity {final_quantity:.6f} below minimum trade size {min_trade_size}"
            
            # Step 10: Calculate final costs and validations
            final_position_value = final_quantity * price
            final_margin = final_position_value / leverage
            trading_fee = final_margin * self.trading_config["trading_fee_pct"]
            total_cost = final_margin + trading_fee
            
            # Step 11: Final balance validation
            if total_cost > available_balance:
                return 0.0, f"Insufficient balance. Need ₹{total_cost:.2f}, have ₹{available_balance:.2f}"
            
            # Step 12: Calculate liquidation price for safety check
            liquidation_distance = (final_margin / final_position_value) * 100  # % from entry
            
            # Step 13: Generate detailed response
            balance_usage_pct = (final_margin / available_balance) * 100
            position_size_pct = (final_position_value / available_balance) * 100
            
            if final_quantity < requested_quantity:
                reason = "liquidation protection" if final_quantity == safe_quantity else "balance limit"
                return final_quantity, f"Qty: {final_quantity:.6f} (adjusted for {reason}). Position: ₹{final_position_value:.0f} ({position_size_pct:.1f}% of balance), Margin: ₹{final_margin:.0f} ({balance_usage_pct:.1f}%), Liquidation risk: {liquidation_distance:.1f}% from entry"
            else:
                return final_quantity, f"Qty: {final_quantity:.6f} approved. Position: ₹{final_position_value:.0f} ({position_size_pct:.1f}% of balance), Margin: ₹{final_margin:.0f} ({balance_usage_pct:.1f}%), Liquidation risk: {liquidation_distance:.1f}% from entry"
                
        except Exception as e:
            self.logger.error(f"Error calculating safe quantity: {e}")
            return 0.0, f"Error calculating safe quantity: {str(e)}"

    
    async def monitor_positions_async(self) -> List[str]:
        """Monitor all open positions and execute risk management actions"""
        try:
            actions_taken = []
            
            for position in list(self.broker.positions.values()):
                if position.status != PositionStatus.OPEN:
                    continue
                
                # No grace period - immediate risk management as requested by user
                
                if position.symbol in self.broker._price_cache:
                    current_price = self.broker._price_cache[position.symbol].get("price", 0.0)
                    
                    if current_price <= 0:
                        continue
                    
                    # Check stop loss
                    if self._check_stop_loss_hit(position, current_price):
                        if await self.broker.close_position_async(position.id, current_price, "Stop Loss Hit"):
                            actions_taken.append(f"Stop Loss: {position.symbol}")
                            continue
                    
                    # Check target hit
                    if self._check_target_hit(position, current_price):
                        if await self.broker.close_position_async(position.id, current_price, "Target Hit"):
                            actions_taken.append(f"Target Hit: {position.symbol}")
                            continue
                    
                    # Check holding time limit
                    if self._check_time_limit_exceeded(position):
                        if await self.broker.close_position_async(position.id, current_price, "Time Limit Reached"):
                            actions_taken.append(f"Time Limit: {position.symbol}")
                            continue
                    
                    # Advanced risk management - only after grace period
                    risk_metrics = await self.analyze_position_risk_async(position, current_price)
                    if await self.execute_risk_action_async(position, risk_metrics, current_price):
                        actions_taken.append(f"Risk Action: {position.symbol}")
            
            return actions_taken
            
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {str(e)}")
            return []
    
    # Private methods
    def _determine_risk_level(self, margin_usage: float, pnl_percentage: float, 
                            holding_time_hours: float, volatility_score: float) -> RiskLevel:
        """Determine risk level based on configurable thresholds"""
        # Get configurable thresholds from trading config
        config = self.trading_config
        
        # Critical conditions - Now configurable
        if (margin_usage > config.get("critical_risk_margin_pct", 90.0) or 
            pnl_percentage < -config.get("critical_risk_loss_pct", 12.0) or 
            holding_time_hours > config.get("critical_risk_time_hours", 36.0)):
            return RiskLevel.CRITICAL
        
        # High risk conditions - Now configurable
        if (margin_usage > config.get("high_risk_margin_pct", 80.0) or 
            pnl_percentage < -config.get("high_risk_loss_pct", 8.0) or 
            volatility_score > 90 or
            holding_time_hours > config.get("high_risk_time_hours", 24.0)):
            return RiskLevel.HIGH
        
        # Medium risk conditions - Now configurable
        if (margin_usage > config.get("medium_risk_margin_pct", 70.0) or 
            pnl_percentage < -config.get("medium_risk_loss_pct", 5.0) or 
            volatility_score > 80 or
            holding_time_hours > config.get("medium_risk_time_hours", 12.0)):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _generate_risk_recommendation(self, position: Position, risk_level: RiskLevel, 
                                    pnl_percentage: float, holding_time_hours: float, 
                                    margin_usage: float) -> RiskAction:
        """Generate risk management recommendation with configurable thresholds"""
        config = self.trading_config
        
        # Check for emergency close conditions first (configurable)
        if (margin_usage > config.get("emergency_close_margin_pct", 95.0) or
            pnl_percentage < -config.get("emergency_close_loss_pct", 15.0) or
            holding_time_hours > config.get("emergency_close_time_hours", 48.0)):
            return RiskAction.EMERGENCY_CLOSE
        
        if risk_level == RiskLevel.CRITICAL:
            if pnl_percentage < -config.get("critical_risk_loss_pct", 12.0):
                return RiskAction.CLOSE_POSITION
            elif margin_usage > config.get("critical_risk_margin_pct", 90.0):
                return RiskAction.CLOSE_POSITION
            elif holding_time_hours > config.get("critical_risk_time_hours", 36.0):
                return RiskAction.CLOSE_POSITION
            else:
                return RiskAction.MONITOR
        
        elif risk_level == RiskLevel.HIGH:
            if pnl_percentage < -config.get("high_risk_loss_pct", 8.0):
                return RiskAction.TIGHTEN_STOP_LOSS
            elif margin_usage > config.get("high_risk_margin_pct", 80.0):
                return RiskAction.MONITOR
            else:
                return RiskAction.CLOSE_POSITION
        
        elif risk_level == RiskLevel.MEDIUM:
            if pnl_percentage > 5:
                return RiskAction.ACTIVATE_TRAILING
            else:
                return RiskAction.MONITOR
        
        else:
            if pnl_percentage > 10:
                return RiskAction.ACTIVATE_TRAILING
            else:
                return RiskAction.MONITOR
    
    def _calculate_risk_score(self, margin_usage: float, pnl_percentage: float, 
                            holding_time_hours: float, volatility_score: float) -> float:
        """Calculate overall risk score (0-100)"""
        # Weighted risk factors
        margin_weight = 0.3
        pnl_weight = 0.3
        time_weight = 0.2
        volatility_weight = 0.2
        
        # Normalize factors to 0-100 scale
        margin_score = min(margin_usage, 100)
        pnl_score = abs(pnl_percentage) if pnl_percentage < 0 else 0
        time_score = min(holding_time_hours / 48 * 100, 100)  # 48 hours max
        volatility_score_norm = min(volatility_score, 100)
        
        # Calculate weighted score
        risk_score = (
            margin_score * margin_weight +
            pnl_score * pnl_weight +
            time_score * time_weight +
            volatility_score_norm * volatility_weight
        )
        
        return min(risk_score, 100)
    
    def _should_send_warning(self, warning_key: str) -> bool:
        """Check if enough time has passed since last warning of this type"""
        import time
        current_time = time.time()
        last_warning = self._last_warning_time.get(warning_key, 0)
        return (current_time - last_warning) >= self._warning_cooldown
    
    def _mark_warning_sent(self, warning_key: str):
        """Mark that a warning was sent for this type/symbol"""
        import time
        self._last_warning_time[warning_key] = time.time()
    
    def _calculate_liquidation_distance(self, position: Position, current_price: float) -> float:
        """Calculate how close position is to liquidation (percentage)"""
        try:
            if position.leverage <= 1 or position.margin_used <= 0:
                return 100.0  # No liquidation risk for non-leveraged positions
            
            # Calculate liquidation price based on position type and leverage
            if position.position_type == PositionType.LONG:
                # For LONG: liquidation when price drops and margin is exhausted
                # Liquidation price = entry_price * (1 - (margin_used / position_value))
                margin_ratio = position.margin_used / (position.quantity * position.entry_price)
                liquidation_price = position.entry_price * (1 - margin_ratio * 0.95)  # 95% of margin (5% buffer)
                distance_pct = ((current_price - liquidation_price) / current_price) * 100
            else:
                # For SHORT: liquidation when price rises and margin is exhausted
                margin_ratio = position.margin_used / (position.quantity * position.entry_price)
                liquidation_price = position.entry_price * (1 + margin_ratio * 0.95)
                distance_pct = ((liquidation_price - current_price) / current_price) * 100
            
            return max(distance_pct, 0.0)  # Never negative
            
        except Exception as e:
            self.logger.error(f"Error calculating liquidation distance for {position.symbol}: {e}")
            return 100.0  # Safe default
    
    def _calculate_trailing_stop(self, position: Position, current_price: float) -> Optional[float]:
        """Calculate trailing stop price"""
        # Simplified trailing stop calculation
        pnl_percentage = (position.pnl / position.invested_amount) * 100 if position.invested_amount > 0 else 0
        
        if pnl_percentage < 5:  # Start trailing after 5% profit
            return None
        
        # Calculate trailing stop price
        if position.position_type == PositionType.LONG:
            trailing_price = current_price * 0.97  # 3% below current price
        else:
            trailing_price = current_price * 1.03  # 3% above current price
        
        return trailing_price
    
    def _should_trigger_trailing_stop(self, position: Position, current_price: float, trailing_price: float) -> bool:
        """Check if trailing stop should be triggered"""
        if position.position_type == PositionType.LONG:
            return current_price <= trailing_price
        else:
            return current_price >= trailing_price
    
    def _update_trailing_stop(self, position: Position, current_price: float, trailing_price: float):
        """Update trailing stop state"""
        position_state = self._trailing_states.get(position.id, {})
        
        if position.position_type == PositionType.LONG:
            highest_price = max(position_state.get("highest_price", position.entry_price), current_price)
            position_state["highest_price"] = highest_price
            
            new_trailing = highest_price * 0.97
            if new_trailing > position_state.get("trailing_price", 0):
                position_state["trailing_price"] = new_trailing
        else:
            lowest_price = min(position_state.get("lowest_price", position.entry_price), current_price)
            position_state["lowest_price"] = lowest_price
            
            new_trailing = lowest_price * 1.03
            if new_trailing < position_state.get("trailing_price", float('inf')):
                position_state["trailing_price"] = new_trailing
        
        self._trailing_states[position.id] = position_state
    
    def _calculate_tighter_stop_loss(self, position: Position, current_price: float) -> float:
        """Calculate a tighter stop loss for high-risk positions"""
        if position.position_type == PositionType.LONG:
            return current_price * 0.98  # 2% below current price
        else:
            return current_price * 1.02  # 2% above current price
    
    def _is_trailing_active(self, position_id: str) -> bool:
        """Check if trailing stop is active for position"""
        return position_id in self._trailing_states
    
    def _activate_trailing_stop(self, position: Position, current_price: float):
        """Activate trailing stop for a position"""
        if position.position_type == PositionType.LONG:
            self._trailing_states[position.id] = {
                "highest_price": current_price,
                "trailing_price": current_price * 0.97,
                "activated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            self._trailing_states[position.id] = {
                "lowest_price": current_price,
                "trailing_price": current_price * 1.03,
                "activated_at": datetime.now(timezone.utc).isoformat()
            }
    
    def _determine_portfolio_risk_level(self, portfolio_margin_usage: float, portfolio_pnl_percentage: float, 
                                       portfolio_return_pct: float, critical_positions: int, 
                                       high_risk_positions: int, total_positions: int, 
                                       effective_portfolio_risk: float = None) -> RiskLevel:
        """Smart portfolio risk level determination based on CORRECTED thresholds
        
        FIXED: Now uses pure margin usage for more accurate risk assessment.
        Effective risk is used only when needed for comprehensive analysis.
        """
        try:
            # Get configurable thresholds
            config = self.trading_config
            max_portfolio_risk = config.get("max_portfolio_risk_pct", 80.0)
            high_risk_margin = config.get("portfolio_high_risk_margin_pct", 80.0)  # Use portfolio-specific threshold
            
            # Use effective risk if available, otherwise pure margin usage
            primary_risk_metric = effective_portfolio_risk if effective_portfolio_risk is not None else portfolio_margin_usage
            
            self.logger.debug(f"Portfolio risk assessment:")
            self.logger.debug(f"  Pure margin usage: {portfolio_margin_usage:.1f}%")
            self.logger.debug(f"  PnL impact: {portfolio_pnl_percentage:.1f}%")
            self.logger.debug(f"  Effective risk: {primary_risk_metric:.1f}%")
            self.logger.debug(f"  High risk threshold: {high_risk_margin:.1f}%")
            
            # LIQUIDATION PROTECTION - CRITICAL RISK CONDITIONS
            liquidation_threshold = 92.0  # Very close to liquidation (95%+ = liquidation)
            emergency_loss_threshold = config.get("critical_risk_loss_pct", 35.0)  # 35% loss = emergency
            
            if (portfolio_margin_usage >= liquidation_threshold or  # Near liquidation - EMERGENCY
                portfolio_pnl_percentage < -emergency_loss_threshold or  # Major losses - EMERGENCY
                portfolio_return_pct < -40.0):  # Severe portfolio decline
                self.logger.warning(f"🚨 LIQUIDATION RISK - CRITICAL: margin={portfolio_margin_usage:.1f}%, pnl={portfolio_pnl_percentage:.1f}%")
                return RiskLevel.CRITICAL
            
            # LIQUIDATION-BASED HIGH RISK CONDITIONS
            liquidation_risk_threshold = 85.0  # Close to liquidation
            significant_loss_threshold = config.get("high_risk_loss_pct", 25.0)  # 25% loss is significant
            
            if (portfolio_margin_usage >= liquidation_risk_threshold or  # Near liquidation
                portfolio_pnl_percentage < -significant_loss_threshold or  # Major loss
                portfolio_return_pct < -30.0):  # Severe portfolio decline
                self.logger.info(f"HIGH RISK triggered: margin={portfolio_margin_usage:.1f}%, pnl={portfolio_pnl_percentage:.1f}%")
                return RiskLevel.HIGH
            
            # LIQUIDATION-BASED MEDIUM RISK CONDITIONS  
            medium_risk_margin = 70.0  # Approaching higher margin usage
            moderate_loss_threshold = config.get("medium_risk_loss_pct", 15.0)  # 15% loss needs attention
            
            if (portfolio_margin_usage >= medium_risk_margin or  # High margin usage
                portfolio_pnl_percentage < -moderate_loss_threshold or  # Moderate losses
                portfolio_return_pct < -20.0):  # Portfolio decline
                return RiskLevel.MEDIUM
            
            # Low risk (healthy portfolio)
            return RiskLevel.LOW
            
        except Exception as e:
            self.logger.error(f"Error determining portfolio risk level: {e}")
            return RiskLevel.MEDIUM  # Safe default

    def _generate_portfolio_recommendations(self, overall_risk: RiskLevel, 
                                          risk_distribution: Dict, 
                                          portfolio_margin_usage: float,
                                          portfolio_pnl_percentage: float) -> List[str]:
        """Generate smart portfolio-level recommendations"""
        recommendations = []
        
        try:
            if overall_risk == RiskLevel.CRITICAL:
                recommendations.append("🚨 CRITICAL: Immediate action required")
                if portfolio_margin_usage > 90:
                    recommendations.append(f"⚠️ Margin usage too high: {portfolio_margin_usage:.1f}% - Close positions immediately")
                if portfolio_pnl_percentage < -15:
                    recommendations.append(f"📉 Portfolio loss critical: {portfolio_pnl_percentage:.1f}% - Emergency close")
                if risk_distribution["critical"] > 0:
                    recommendations.append(f"🔴 {risk_distribution['critical']} position(s) in critical state")
            
            elif overall_risk == RiskLevel.HIGH:
                recommendations.append("⚠️ HIGH RISK: Consider reducing exposure")
                if portfolio_margin_usage > 75:
                    recommendations.append(f"📊 Margin usage high: {portfolio_margin_usage:.1f}% - Reduce position sizes")
                if portfolio_pnl_percentage < -10:
                    recommendations.append(f"📉 Portfolio declining: {portfolio_pnl_percentage:.1f}% - Review stop losses")
                if risk_distribution["high"] > 1:
                    recommendations.append(f"🟡 {risk_distribution['high']} positions need attention")
            
            elif overall_risk == RiskLevel.MEDIUM:
                recommendations.append("📊 MODERATE RISK: Monitor closely")
                if portfolio_margin_usage > 50:
                    recommendations.append(f"📈 Margin usage: {portfolio_margin_usage:.1f}% - Consider taking profits")
                if portfolio_pnl_percentage < -5:
                    recommendations.append(f"📉 Portfolio down: {portfolio_pnl_percentage:.1f}% - Review positions")
            
            else:  # LOW risk
                recommendations.append("✅ Portfolio risk is healthy")
                if portfolio_margin_usage < 30:
                    recommendations.append("💡 Low margin usage - Opportunity for more positions")
                if portfolio_pnl_percentage > 5:
                    recommendations.append("🎯 Good performance - Consider taking partial profits")
            
            # Anti-overtrade recommendations
            max_portfolio_margin = self.trading_config.get("max_portfolio_risk_pct", 80.0)
            high_risk_margin = self.trading_config.get("high_risk_margin_pct", 85.0)
            
            if portfolio_margin_usage >= max_portfolio_margin:
                recommendations.append(f"🚫 ANTI-OVERTRADE ACTIVE: {portfolio_margin_usage:.1f}% >= {max_portfolio_margin}% - New trades blocked")
            elif portfolio_margin_usage >= high_risk_margin:
                recommendations.append(f"⚠️ Approaching overtrade threshold: {portfolio_margin_usage:.1f}% (limit: {max_portfolio_margin}%)")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating portfolio recommendations: {e}")
            return ["⚠️ Unable to generate recommendations - check system logs"]
    
    def _check_stop_loss_hit(self, position: Position, current_price: float) -> bool:
        """Check if stop loss is hit"""
        if not position.stop_loss:
            return False
        
        if position.position_type == PositionType.LONG:
            return current_price <= position.stop_loss
        else:
            return current_price >= position.stop_loss
    
    def _check_target_hit(self, position: Position, current_price: float) -> bool:
        """Check if target is hit"""
        if not position.target:
            return False
        
        if position.position_type == PositionType.LONG:
            return current_price >= position.target
        else:
            return current_price <= position.target
    
    def _check_time_limit_exceeded(self, position: Position) -> bool:
        """Check if holding time exceeded maximum limit"""
        try:
            entry_time = position.entry_time
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            holding_hours = (current_time - entry_time).total_seconds() / 3600
            
            return holding_hours >= 48  # 48 hours max holding time
        except:
            return False
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            return {
                "total_positions_monitored": len(self._risk_metrics),
                "trailing_stops_active": len(self._trailing_states),
                "risk_decisions_today": len([
                    d for d in self._risk_decisions 
                    if d.get("timestamp", "").startswith(datetime.now().strftime("%Y-%m-%d"))
                ]),
                "monitoring_status": "active",
                "last_check": datetime.now(timezone.utc).isoformat(),
                "execution_times": self._execution_times,
                "balance_per_trade_pct": self.trading_config.get("balance_per_trade_pct", 0.20)
            }
            
        except Exception as e:
            return {"error": str(e)} 