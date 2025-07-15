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
from src.config import get_settings
from src.notifications import NotificationManager


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
        self.logger = logging.getLogger("risk_manager.async")
        
        # Risk thresholds
        self.max_portfolio_risk = 0.15  # 15% max portfolio risk
        self.max_position_risk = 0.05   # 5% max position risk
        self.correlation_threshold = 0.7
        
        # Risk tracking
        self._risk_metrics: Dict[str, RiskMetrics] = {}
        self._trailing_states: Dict[str, Dict] = {}
        
        # Performance tracking
        self._risk_decisions = []
        self._execution_times = {}
        
        # Notification system
        self.notification_manager = NotificationManager()
        
        self.logger.info("Simplified async risk manager initialized")
    
    async def start(self):
        """Start async risk management system"""
        try:
            self.logger.info("Starting simplified async risk management system")
            
            # Start notification manager
            await self.notification_manager.start()
            
            self.logger.info("Simplified async risk management system started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start async risk manager: {e}")
            return False
    
    async def stop(self):
        """Stop async risk management system"""
        self.logger.info("Stopping simplified async risk management system")
        
        # Stop notification manager
        await self.notification_manager.stop()
        
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
            
            # Calculate margin usage
            margin_usage = 0.0
            if position.leverage > 1 and position.margin_used > 0:
                margin_usage = position.calculate_margin_usage(current_price)
            
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
            
            # Handle critical risk situations
            if risk_metrics.risk_level == RiskLevel.CRITICAL:
                if risk_metrics.recommendation in [RiskAction.CLOSE_POSITION, RiskAction.EMERGENCY_CLOSE]:
                    if await self.broker.close_position_async(position.id, current_price, f"Risk Management: {risk_metrics.recommendation.value}"):
                        await self.notification_manager.notify_risk_alert(
                            symbol=position.symbol,
                            alert_type="Critical Risk Closure",
                            current_price=current_price,
                            risk_level=risk_metrics.risk_level.value
                        )
                        action_taken = True
            
            # Handle high risk situations
            elif risk_metrics.risk_level == RiskLevel.HIGH:
                if risk_metrics.recommendation == RiskAction.TIGHTEN_STOP_LOSS:
                    new_stop_loss = self._calculate_tighter_stop_loss(position, current_price)
                    if new_stop_loss != position.stop_loss:
                        await self.notification_manager.notify_risk_alert(
                            symbol=position.symbol,
                            alert_type="Stop Loss Tightened",
                            current_price=current_price,
                            risk_level=risk_metrics.risk_level.value
                        )
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
        """Analyze overall portfolio risk asynchronously"""
        try:
            if not self.broker.positions:
                return {"status": "no_positions", "risk_level": "low"}
            
            # Collect all position risks
            position_risks = []
            total_risk_value = 0.0
            total_portfolio_value = self.broker.account.current_balance if self.broker.account else 0.0
            
            for position in self.broker.positions.values():
                if position.symbol in self.broker._price_cache:
                    current_price = self.broker._price_cache[position.symbol].get("price", 0.0)
                    if current_price > 0:
                        risk_metrics = await self.analyze_position_risk_async(position, current_price)
                        position_risks.append(risk_metrics)
                        total_risk_value += position.invested_amount
            
            # Calculate portfolio metrics
            portfolio_risk_percentage = (total_risk_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
            
            # Count positions by risk level
            risk_distribution = {
                "low": len([r for r in position_risks if r.risk_level == RiskLevel.LOW]),
                "medium": len([r for r in position_risks if r.risk_level == RiskLevel.MEDIUM]),
                "high": len([r for r in position_risks if r.risk_level == RiskLevel.HIGH]),
                "critical": len([r for r in position_risks if r.risk_level == RiskLevel.CRITICAL])
            }
            
            # Determine overall portfolio risk
            if risk_distribution["critical"] > 0:
                overall_risk = RiskLevel.CRITICAL
            elif risk_distribution["high"] > 2 or portfolio_risk_percentage > 12:
                overall_risk = RiskLevel.HIGH
            elif risk_distribution["high"] > 0 or portfolio_risk_percentage > 8:
                overall_risk = RiskLevel.MEDIUM
            else:
                overall_risk = RiskLevel.LOW
            
            # Generate recommendations
            recommendations = self._generate_portfolio_recommendations(
                overall_risk, risk_distribution, portfolio_risk_percentage
            )
            
            return {
                "status": "analyzed",
                "overall_risk_level": overall_risk.value,
                "portfolio_risk_percentage": portfolio_risk_percentage,
                "total_positions": len(position_risks),
                "risk_distribution": risk_distribution,
                "position_risks": [
                    {
                        "symbol": r.symbol,
                        "risk_level": r.risk_level.value,
                        "pnl_percentage": r.pnl_percentage,
                        "recommendation": r.recommendation.value,
                        "risk_score": r.risk_score
                    } for r in position_risks
                ],
                "recommendations": recommendations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Portfolio risk analysis failed: {e}")
            return {"status": "error", "error": str(e)}
    
    async def should_allow_new_position_async(self, symbol: str, position_value: float) -> Tuple[bool, str]:
        """Check if a new position should be allowed based on risk analysis"""
        try:
            if not self.broker.account:
                return False, "No account available"
            
            # Check portfolio risk
            current_portfolio_value = sum(pos.invested_amount for pos in self.broker.positions.values())
            total_portfolio_value = self.broker.account.current_balance + current_portfolio_value
            
            new_portfolio_risk = (current_portfolio_value + position_value) / total_portfolio_value
            
            if new_portfolio_risk > self.max_portfolio_risk:
                reason = f"Portfolio risk {new_portfolio_risk:.1%} would exceed {self.max_portfolio_risk:.1%} limit"
                return False, reason
            
            # Check position size risk
            position_risk = position_value / total_portfolio_value
            
            if position_risk > self.max_position_risk:
                reason = f"Position size {position_risk:.1%} would exceed {self.max_position_risk:.1%} limit"
                return False, reason
            
            # Check correlation (simplified - check if same symbol already open)
            for pos in self.broker.positions.values():
                if pos.symbol == symbol and pos.status == PositionStatus.OPEN:
                    reason = f"Position already open for {symbol}"
                    return False, reason
            
            return True, "Position approved"
            
        except Exception as e:
            error_msg = f"Risk check failed: {str(e)}"
            return False, error_msg
    
    async def monitor_positions_async(self) -> List[str]:
        """Monitor all open positions and execute risk management actions"""
        try:
            actions_taken = []
            
            for position in list(self.broker.positions.values()):
                if position.status != PositionStatus.OPEN:
                    continue
                
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
                    
                    # Advanced risk management
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
        """Determine risk level based on multiple factors"""
        # Critical conditions
        if (margin_usage > 95 or 
            pnl_percentage < -10 or 
            holding_time_hours > 47):
            return RiskLevel.CRITICAL
        
        # High risk conditions
        if (margin_usage > 80 or 
            pnl_percentage < -5 or 
            volatility_score > 80 or
            holding_time_hours > 36):
            return RiskLevel.HIGH
        
        # Medium risk conditions
        if (margin_usage > 60 or 
            pnl_percentage < -2 or 
            volatility_score > 60 or
            holding_time_hours > 24):
            return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    def _generate_risk_recommendation(self, position: Position, risk_level: RiskLevel, 
                                    pnl_percentage: float, holding_time_hours: float, 
                                    margin_usage: float) -> RiskAction:
        """Generate risk management recommendation"""
        if risk_level == RiskLevel.CRITICAL:
            if margin_usage > 95:
                return RiskAction.EMERGENCY_CLOSE
            elif pnl_percentage < -10:
                return RiskAction.CLOSE_POSITION
            elif holding_time_hours > 47:
                return RiskAction.CLOSE_POSITION
            else:
                return RiskAction.EMERGENCY_CLOSE
        
        elif risk_level == RiskLevel.HIGH:
            if pnl_percentage < -5:
                return RiskAction.TIGHTEN_STOP_LOSS
            elif margin_usage > 80:
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
    
    def _generate_portfolio_recommendations(self, overall_risk: RiskLevel, 
                                          risk_distribution: Dict, 
                                          portfolio_risk_percentage: float) -> List[str]:
        """Generate portfolio-level recommendations"""
        recommendations = []
        
        if overall_risk == RiskLevel.CRITICAL:
            recommendations.append("EMERGENCY: Close high-risk positions immediately")
            recommendations.append("Reduce portfolio exposure below 10%")
        
        elif overall_risk == RiskLevel.HIGH:
            recommendations.append("Reduce position sizes or close some positions")
            recommendations.append("Tighten stop losses on all positions")
        
        elif overall_risk == RiskLevel.MEDIUM:
            recommendations.append("Monitor positions closely")
            recommendations.append("Consider taking profits on profitable positions")
        
        if portfolio_risk_percentage > self.max_portfolio_risk * 100:
            recommendations.append(f"Portfolio risk ({portfolio_risk_percentage:.1f}%) exceeds limit")
        
        if risk_distribution["critical"] > 0:
            recommendations.append(f"{risk_distribution['critical']} position(s) need immediate attention")
        
        return recommendations
    
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
            
            return holding_hours >= 48  # 48 hours max
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
                "execution_times": self._execution_times
            }
            
        except Exception as e:
            return {"error": str(e)} 