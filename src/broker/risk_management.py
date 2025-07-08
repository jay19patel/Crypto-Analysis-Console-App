"""
Advanced Risk Management System
Handles trailing stops, risk analysis, position management, and automated decisions
"""

import logging
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
from src.broker.models import Position, PositionType, PositionStatus
from src.config import get_settings

class RiskLevel(Enum):
    """Risk level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TrailingStopType(Enum):
    """Trailing stop types"""
    PERCENTAGE = "percentage"
    ATR = "atr"
    FIXED = "fixed"

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
    recommendation: str
    trailing_stop_price: Optional[float] = None

@dataclass
class TrailingStopConfig:
    """Trailing stop configuration"""
    enabled: bool = True
    trigger_percentage: float = 0.05  # Start trailing after 5% profit
    trail_percentage: float = 0.03    # Trail by 3%
    stop_type: TrailingStopType = TrailingStopType.PERCENTAGE
    min_profit_lock: float = 0.02     # Lock in minimum 2% profit

class RiskManager:
    """
    Advanced Risk Management System
    Handles all risk-related decisions, trailing stops, and position management
    """
    
    def __init__(self, broker):
        """Initialize risk manager"""
        self.broker = broker
        self.settings = get_settings()
        self.logger = logging.getLogger("risk_manager")
        
        # Risk thresholds from config
        self.max_portfolio_risk = self.settings.RISK_MAX_PORTFOLIO_RISK
        self.max_position_risk = self.settings.RISK_MAX_POSITION_RISK
        self.correlation_threshold = self.settings.RISK_CORRELATION_THRESHOLD
        
        # Trailing stop configurations per symbol
        self.trailing_configs: Dict[str, TrailingStopConfig] = {}
        self.trailing_states: Dict[str, Dict] = {}  # Track trailing state per position
        
        # Risk monitoring
        self._risk_monitor_thread = None
        self._stop_monitoring = threading.Event()
        self._last_risk_check = time.time()
        
        # Performance tracking
        self._risk_decisions = []
        
        # Default trailing stop config
        self.default_trailing_config = TrailingStopConfig()
    
    def start_risk_monitoring(self) -> None:
        """Start continuous risk monitoring"""
        if self._risk_monitor_thread and self._risk_monitor_thread.is_alive():
            return
        
        self._stop_monitoring.clear()
        self._risk_monitor_thread = threading.Thread(target=self._risk_monitoring_loop, daemon=True)
        self._risk_monitor_thread.start()
        
        self._log_risk_event("info", "Risk monitoring started", {})
    
    def stop_risk_monitoring(self) -> None:
        """Stop risk monitoring"""
        self._stop_monitoring.set()
        if self._risk_monitor_thread:
            self._risk_monitor_thread.join(timeout=5.0)
        
        self._log_risk_event("info", "Risk monitoring stopped", {})
    
    def analyze_position_risk(self, position: Position, current_price: float) -> RiskMetrics:
        """Comprehensive risk analysis for a position"""
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
            
            # Calculate volatility score (simplified)
            volatility_score = self._calculate_volatility_score(position.symbol, current_price)
            
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
            
            return RiskMetrics(
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
                trailing_stop_price=trailing_stop_price
            )
            
        except Exception as e:
            self._log_risk_event("error", f"Risk analysis failed for {position.symbol}", {"error": str(e)})
            
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
                recommendation="CLOSE_IMMEDIATELY"
            )
    
    def execute_risk_action(self, position: Position, risk_metrics: RiskMetrics, current_price: float) -> bool:
        """Execute risk management action based on analysis"""
        try:
            action_taken = False
            
            # Handle trailing stop
            if risk_metrics.trailing_stop_price:
                if self._should_trigger_trailing_stop(position, current_price, risk_metrics.trailing_stop_price):
                    if self.broker.close_position(position.id, current_price, "Trailing Stop Hit"):
                        self._log_risk_event("info", f"Trailing stop executed for {position.symbol}", {
                            "entry_price": position.entry_price,
                            "exit_price": current_price,
                            "trailing_price": risk_metrics.trailing_stop_price,
                            "pnl": position.pnl
                        })
                        action_taken = True
                else:
                    # Update trailing stop
                    self._update_trailing_stop(position, current_price, risk_metrics.trailing_stop_price)
            
            # Handle critical risk situations
            if risk_metrics.risk_level == RiskLevel.CRITICAL:
                if "CLOSE" in risk_metrics.recommendation.upper():
                    if self.broker.close_position(position.id, current_price, f"Risk Management: {risk_metrics.recommendation}"):
                        self._log_risk_event("warning", f"Critical risk closure for {position.symbol}", {
                            "risk_level": risk_metrics.risk_level.value,
                            "recommendation": risk_metrics.recommendation,
                            "margin_usage": risk_metrics.margin_usage,
                            "pnl_percentage": risk_metrics.pnl_percentage
                        })
                        action_taken = True
            
            # Handle high risk situations
            elif risk_metrics.risk_level == RiskLevel.HIGH:
                # Tighten stop loss for high risk positions
                if risk_metrics.pnl_percentage < -3.0:  # More than 3% loss
                    new_stop_loss = self._calculate_tighter_stop_loss(position, current_price)
                    if new_stop_loss != position.stop_loss:
                        if self.broker.update_stop_loss(position.id, new_stop_loss):
                            self._log_risk_event("warning", f"Tightened stop loss for {position.symbol}", {
                                "old_stop_loss": position.stop_loss,
                                "new_stop_loss": new_stop_loss,
                                "current_price": current_price
                            })
                            action_taken = True
            
            # Handle profit protection
            if risk_metrics.pnl_percentage > 10.0:  # More than 10% profit
                if not self._is_trailing_active(position.id):
                    self._activate_trailing_stop(position, current_price)
                    self._log_risk_event("info", f"Activated trailing stop for profitable position {position.symbol}", {
                        "pnl_percentage": risk_metrics.pnl_percentage,
                        "current_price": current_price
                    })
                    action_taken = True
            
            return action_taken
            
        except Exception as e:
            self._log_risk_event("error", f"Risk action execution failed for {position.symbol}", {"error": str(e)})
            return False
    
    def analyze_portfolio_risk(self) -> Dict[str, Any]:
        """Analyze overall portfolio risk"""
        try:
            if not self.broker.open_positions:
                return {"status": "no_positions", "risk_level": "low"}
            
            # Collect all position risks
            position_risks = []
            total_risk_value = 0.0
            total_portfolio_value = self.broker.account.current_balance if self.broker.account else 0.0
            
            for position in self.broker.open_positions.values():
                if position.symbol in self.broker.current_prices:
                    current_price = self.broker.current_prices[position.symbol]["price"]
                    risk_metrics = self.analyze_position_risk(position, current_price)
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
                        "recommendation": r.recommendation
                    } for r in position_risks
                ],
                "recommendations": recommendations,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self._log_risk_event("error", "Portfolio risk analysis failed", {"error": str(e)})
            return {"status": "error", "error": str(e)}
    
    def should_allow_new_position(self, symbol: str, position_value: float) -> Tuple[bool, str]:
        """Check if a new position should be allowed based on risk analysis"""
        try:
            if not self.broker.account:
                self._log_risk_event("error", "❌ No account available for position check")
                return False, "No account available"
            
            self._log_risk_event("debug", f"Checking position allowance for {symbol}", {
                "symbol": symbol,
                "position_value": position_value,
                "account_balance": self.broker.account.current_balance
            })
            
            # Check portfolio risk
            current_portfolio_value = sum(pos.invested_amount for pos in self.broker.open_positions.values())
            total_portfolio_value = self.broker.account.current_balance + current_portfolio_value
            
            new_portfolio_risk = (current_portfolio_value + position_value) / total_portfolio_value
            
            self._log_risk_event("debug", f"Portfolio risk check for {symbol}", {
                "current_portfolio_value": current_portfolio_value,
                "total_portfolio_value": total_portfolio_value,
                "new_portfolio_risk": f"{new_portfolio_risk:.2%}",
                "max_portfolio_risk": f"{self.max_portfolio_risk:.2%}"
            })
            
            if new_portfolio_risk > self.max_portfolio_risk:
                reason = f"Portfolio risk {new_portfolio_risk:.1%} would exceed {self.max_portfolio_risk:.1%} limit"
                self._log_risk_event("warning", f"❌ Portfolio risk limit exceeded for {symbol}: {reason}")
                return False, reason
            
            # Check position size risk
            position_risk = position_value / total_portfolio_value
            
            self._log_risk_event("debug", f"Position size risk check for {symbol}", {
                "position_risk": f"{position_risk:.2%}",
                "max_position_risk": f"{self.max_position_risk:.2%}"
            })
            
            if position_risk > self.max_position_risk:
                reason = f"Position size {position_risk:.1%} would exceed {self.max_position_risk:.1%} limit"
                self._log_risk_event("warning", f"❌ Position size limit exceeded for {symbol}: {reason}")
                return False, reason
            
            # Check correlation (simplified - check if same symbol already open)
            for pos in self.broker.open_positions.values():
                if pos.symbol == symbol:
                    reason = f"Position already open for {symbol}"
                    self._log_risk_event("warning", f"❌ Duplicate position rejected for {symbol}")
                    return False, reason
            
            # Check daily trade limits
            if not self.broker._can_trade_today():
                reason = "Daily trade limit reached"
                self._log_risk_event("warning", f"❌ Daily trade limit reached")
                return False, reason
            
            self._log_risk_event("info", f"✅ Position validation passed for {symbol}", {
                "symbol": symbol,
                "position_value": position_value,
                "portfolio_risk": f"{new_portfolio_risk:.2%}",
                "position_risk": f"{position_risk:.2%}"
            })
            
            return True, "Position approved"
            
        except Exception as e:
            error_msg = f"Risk check failed: {str(e)}"
            self._log_risk_event("error", f"❌ Position validation error for {symbol}: {error_msg}")
            return False, error_msg
    
    def execute_signal_trade(self, signal_data: Dict[str, Any]) -> bool:
        """Execute a trade based on signal with proper risk management"""
        try:
            signal = signal_data.get("signal", "").upper()
            symbol = signal_data.get("symbol", "")
            current_price = signal_data.get("current_price", 0.0)
            
            self._log_risk_event("info", f"Processing {signal} signal for {symbol} at ${current_price:.2f}")
            
            # Validate signal
            if signal not in ["BUY", "SELL"]:
                self._log_risk_event("warning", f"❌ Invalid signal ignored: {signal} for {symbol}")
                return False
            
            if not symbol or current_price <= 0:
                self._log_risk_event("warning", f"❌ Invalid signal data for {symbol}: price={current_price}")
                return False
            
            # Check if we should allow new position
            position_value, leverage = self._calculate_optimal_position_size(current_price)
            allowed, reason = self.should_allow_new_position(symbol, position_value)
            
            if not allowed:
                self._log_risk_event("warning", f"❌ Trade rejected for {symbol}: {reason}", {
                    "symbol": symbol,
                    "signal": signal,
                    "price": current_price,
                    "calculated_position_value": position_value,
                    "rejection_reason": reason
                })
                return False
            
            if position_value <= 0:
                self._log_risk_event("warning", f"❌ Invalid position size calculated for {symbol}: ${position_value:.2f}")
                return False
            
            self._log_risk_event("info", f"✅ Trade validation passed for {symbol}", {
                "signal": signal,
                "position_value": position_value,
                "leverage": leverage,
                "account_balance": self.broker.account.current_balance if self.broker.account else 0
            })
            
            # Execute trade through broker
            success = self.broker.execute_trade(
                signal=signal,
                symbol=symbol,
                current_price=current_price,
                confidence=100.0,  # Full confidence from strategy
                strategy_name="Simple Random Strategy",
                leverage=leverage
            )
            
            if success:
                self._log_risk_event("info", f"🎯 Trade executed successfully: {signal} {symbol} at ${current_price:.2f}", {
                    "signal": signal,
                    "symbol": symbol,
                    "price": current_price,
                    "position_value": position_value,
                    "leverage": leverage
                })
                return True
            else:
                self._log_risk_event("error", f"❌ Broker execution failed: {signal} {symbol}")
                return False
                
        except Exception as e:
            self._log_risk_event("error", f"❌ Error executing signal trade: {str(e)}", {
                "signal_data": signal_data,
                "error": str(e)
            })
            return False
    
    def _calculate_optimal_position_size(self, current_price: float) -> Tuple[float, float]:
        """Calculate optimal position size based on risk management rules"""
        try:
            if not self.broker.account:
                return 0.0, 1.0
            
            # Use account risk per trade setting (default 2%)
            risk_amount = self.broker.account.current_balance * self.broker.account.risk_per_trade
            
            # Use default leverage from settings
            leverage = self.settings.BROKER_DEFAULT_LEVERAGE
            
            # Calculate position value (risk amount * leverage, but cap at max position size)
            position_value = min(
                risk_amount * leverage,
                self.broker.account.max_position_size,
                self.broker.account.current_balance * 0.1  # Never more than 10% of balance
            )
            
            return position_value, leverage
            
        except Exception as e:
            self._log_risk_event("error", f"Error calculating position size: {str(e)}")
            return 0.0, 1.0
    
    def monitor_positions(self) -> List[str]:
        """Monitor all open positions and execute risk management actions"""
        try:
            actions_taken = []
            
            for position in list(self.broker.open_positions.values()):
                if position.symbol in self.broker.current_prices:
                    current_price = self.broker.current_prices[position.symbol]["price"]
                    
                    # Check stop loss
                    if self._check_stop_loss_hit(position, current_price):
                        if self.broker.close_position(position.id, current_price, "Stop Loss Hit"):
                            actions_taken.append(f"Stop Loss: {position.symbol}")
                            self._log_risk_event("info", f"Stop loss triggered for {position.symbol}")
                            continue
                    
                    # Check target hit
                    if self._check_target_hit(position, current_price):
                        if self.broker.close_position(position.id, current_price, "Target Hit"):
                            actions_taken.append(f"Target Hit: {position.symbol}")
                            self._log_risk_event("info", f"Target reached for {position.symbol}")
                            continue
                    
                    # Check holding time limit (48 hours)
                    if self._check_time_limit_exceeded(position):
                        if self.broker.close_position(position.id, current_price, "Time Limit Reached"):
                            actions_taken.append(f"Time Limit: {position.symbol}")
                            self._log_risk_event("info", f"Time limit reached for {position.symbol}")
                            continue
                    
                    # Advanced risk management
                    risk_metrics = self.analyze_position_risk(position, current_price)
                    if self.execute_risk_action(position, risk_metrics, current_price):
                        actions_taken.append(f"Risk Action: {position.symbol}")
            
            return actions_taken
            
        except Exception as e:
            self._log_risk_event("error", f"Error monitoring positions: {str(e)}")
            return []
    
    def _check_stop_loss_hit(self, position: Position, current_price: float) -> bool:
        """Check if stop loss is hit"""
        if not position.stop_loss:
            return False
        
        if position.position_type == PositionType.LONG:
            return current_price <= position.stop_loss
        else:  # SHORT
            return current_price >= position.stop_loss
    
    def _check_target_hit(self, position: Position, current_price: float) -> bool:
        """Check if target is hit"""
        if not position.target:
            return False
        
        if position.position_type == PositionType.LONG:
            return current_price >= position.target
        else:  # SHORT
            return current_price <= position.target
    
    def _check_time_limit_exceeded(self, position: Position) -> bool:
        """Check if holding time exceeded maximum limit"""
        try:
            entry_time = position.entry_time
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            holding_hours = (current_time - entry_time).total_seconds() / 3600
            
            return holding_hours >= self.settings.BROKER_MAX_HOLDING_HOURS
        except:
            return False
    
    # Private helper methods
    def _risk_monitoring_loop(self) -> None:
        """Main risk monitoring loop"""
        while not self._stop_monitoring.is_set():
            try:
                start_time = time.time()
                
                # Analyze each open position
                actions_taken = 0
                for position in list(self.broker.open_positions.values()):
                    if position.symbol in self.broker.current_prices:
                        current_price = self.broker.current_prices[position.symbol]["price"]
                        
                        # Analyze risk
                        risk_metrics = self.analyze_position_risk(position, current_price)
                        
                        # Execute risk actions
                        if self.execute_risk_action(position, risk_metrics, current_price):
                            actions_taken += 1
                
                # Log monitoring results
                if actions_taken > 0:
                    self._log_risk_event("info", f"Risk monitoring completed - {actions_taken} actions taken")
                
                # Analyze portfolio risk periodically
                current_time = time.time()
                if current_time - self._last_risk_check > 300:  # Every 5 minutes
                    portfolio_risk = self.analyze_portfolio_risk()
                    self._last_risk_check = current_time
                    
                    if portfolio_risk.get("overall_risk_level") in ["high", "critical"]:
                        self._log_risk_event("warning", "High portfolio risk detected", portfolio_risk)
                
                # Sleep
                elapsed = time.time() - start_time
                sleep_time = max(0, 2.0 - elapsed)  # Target 2-second intervals
                time.sleep(sleep_time)
                
            except Exception as e:
                self._log_risk_event("error", f"Risk monitoring error: {e}")
                time.sleep(5)  # Wait before retrying
    
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
                                    margin_usage: float) -> str:
        """Generate risk management recommendation"""
        if risk_level == RiskLevel.CRITICAL:
            if margin_usage > 95:
                return "CLOSE_IMMEDIATELY - Margin Call Risk"
            elif pnl_percentage < -10:
                return "CLOSE_IMMEDIATELY - Heavy Loss"
            elif holding_time_hours > 47:
                return "CLOSE_IMMEDIATELY - Time Limit Reached"
            else:
                return "CLOSE_IMMEDIATELY - Critical Risk"
        
        elif risk_level == RiskLevel.HIGH:
            if pnl_percentage < -5:
                return "TIGHTEN_STOP_LOSS - Limit Further Loss"
            elif margin_usage > 80:
                return "MONITOR_CLOSELY - High Margin Usage"
            else:
                return "CONSIDER_CLOSING - High Risk Detected"
        
        elif risk_level == RiskLevel.MEDIUM:
            if pnl_percentage > 5:
                return "ACTIVATE_TRAILING - Protect Profits"
            else:
                return "MONITOR - Moderate Risk"
        
        else:
            if pnl_percentage > 10:
                return "CONSIDER_PARTIAL_CLOSE - Lock Profits"
            else:
                return "HOLD - Low Risk"
    
    def _calculate_volatility_score(self, symbol: str, current_price: float) -> float:
        """Calculate simplified volatility score"""
        # This is a placeholder - in real implementation, you'd calculate based on historical data
        # For now, return a moderate score
        return 50.0
    
    def _calculate_trailing_stop(self, position: Position, current_price: float) -> Optional[float]:
        """Calculate trailing stop price"""
        config = self.trailing_configs.get(position.symbol, self.default_trailing_config)
        
        if not config.enabled:
            return None
        
        # Check if position is profitable enough to start trailing
        pnl_percentage = (position.pnl / position.invested_amount) * 100 if position.invested_amount > 0 else 0
        
        if pnl_percentage < config.trigger_percentage * 100:
            return None
        
        # Calculate trailing stop price
        if position.position_type == PositionType.LONG:
            trailing_price = current_price * (1 - config.trail_percentage)
        else:
            trailing_price = current_price * (1 + config.trail_percentage)
        
        return trailing_price
    
    def _should_trigger_trailing_stop(self, position: Position, current_price: float, trailing_price: float) -> bool:
        """Check if trailing stop should be triggered"""
        if position.position_type == PositionType.LONG:
            return current_price <= trailing_price
        else:
            return current_price >= trailing_price
    
    def _update_trailing_stop(self, position: Position, current_price: float, trailing_price: float) -> None:
        """Update trailing stop state"""
        position_state = self.trailing_states.get(position.id, {})
        
        # Update the highest/lowest price seen
        if position.position_type == PositionType.LONG:
            highest_price = max(position_state.get("highest_price", position.entry_price), current_price)
            position_state["highest_price"] = highest_price
            
            # Update trailing stop price
            new_trailing = highest_price * (1 - self.default_trailing_config.trail_percentage)
            if new_trailing > position_state.get("trailing_price", 0):
                position_state["trailing_price"] = new_trailing
        else:
            lowest_price = min(position_state.get("lowest_price", position.entry_price), current_price)
            position_state["lowest_price"] = lowest_price
            
            # Update trailing stop price
            new_trailing = lowest_price * (1 + self.default_trailing_config.trail_percentage)
            if new_trailing < position_state.get("trailing_price", float('inf')):
                position_state["trailing_price"] = new_trailing
        
        self.trailing_states[position.id] = position_state
    
    def _calculate_tighter_stop_loss(self, position: Position, current_price: float) -> float:
        """Calculate a tighter stop loss for high-risk positions"""
        if position.position_type == PositionType.LONG:
            # Tighten stop loss to 2% below current price
            return current_price * 0.98
        else:
            # Tighten stop loss to 2% above current price
            return current_price * 1.02
    
    def _is_trailing_active(self, position_id: str) -> bool:
        """Check if trailing stop is active for position"""
        return position_id in self.trailing_states
    
    def _activate_trailing_stop(self, position: Position, current_price: float) -> None:
        """Activate trailing stop for a position"""
        if position.position_type == PositionType.LONG:
            self.trailing_states[position.id] = {
                "highest_price": current_price,
                "trailing_price": current_price * (1 - self.default_trailing_config.trail_percentage),
                "activated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            self.trailing_states[position.id] = {
                "lowest_price": current_price,
                "trailing_price": current_price * (1 + self.default_trailing_config.trail_percentage),
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
    
    def _log_risk_event(self, level: str, message: str, data: Any = None) -> None:
        """Log risk management events"""
        timestamp = datetime.now(timezone.utc)
        
        log_entry = {
            "module": "RiskManager",
            "timestamp": timestamp.isoformat(),
            "level": level.upper(),
            "message": message,
            "data": data
        }
        
        # Log to file
        getattr(self.logger, level)(f"[RiskManager] {message}")
        
        # Simplified logging - no WebSocket dependency
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary"""
        try:
            portfolio_risk = self.analyze_portfolio_risk()
            
            return {
                "portfolio_risk": portfolio_risk,
                "trailing_stops_active": len(self.trailing_states),
                "risk_decisions_today": len([
                    d for d in self._risk_decisions 
                    if d.get("timestamp", "").startswith(datetime.now().strftime("%Y-%m-%d"))
                ]),
                "monitoring_status": "active" if not self._stop_monitoring.is_set() else "stopped",
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {"error": str(e)} 