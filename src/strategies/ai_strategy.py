"""
Real AI-Powered Strategy using LangChain and Google Generative AI
No manual analysis - Real AI responses only!
"""

import pandas as pd
import os
from typing import Optional, Literal
from src.strategies.base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel
from src.config import get_settings

# Try importing LangChain dependencies
try:
    from pydantic import BaseModel, Field
    from langchain.prompts import PromptTemplate
    from langchain.output_parsers import PydanticOutputParser
    from langchain_google_genai import ChatGoogleGenerativeAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

if LANGCHAIN_AVAILABLE:
    class AIAnalysisResponse(BaseModel):
        """Enhanced Pydantic model for comprehensive AI analysis response"""
        # === EXISTING FIELDS (DO NOT REMOVE) ===
        summary: str = Field(description="Short market behavior summary in Hinglish")
        current_trend: Literal["Bullish", "Bearish", "Sideways"] = Field(description="Current market trend")
        candlestick_patterns: str = Field(description="Any candle patterns detected")
        strength: Literal["Strong", "Moderate", "Weak"] = Field(description="Signal strength based on indicator confluence")
        recommendation: Literal["Buy", "Sell", "Wait"] = Field(description="Trading recommendation")
        reason: str = Field(description="Main technical reasons for the recommendation")
        price_movement: Literal["Up", "Down", "Sideways"] = Field(description="Expected price movement")
        momentum_forecast: str = Field(description="Short forecast using momentum indicators")
        action_type: Literal["Buy", "Sell", "Wait"] = Field(description="Recommended action")
        action_strength: int = Field(description="Signal strength 0-100", ge=0, le=100)
        entry_price: Optional[float] = Field(description="Suggested entry price", default=None)
        stoploss: Optional[float] = Field(description="Suggested stop loss", default=None)
        target: Optional[float] = Field(description="Suggested target price", default=None)
        risk_to_reward: str = Field(description="Risk to reward ratio", default="1:2")
        max_holding_period: Optional[str] = Field(description="Maximum holding period", default=None)
        reason_to_hold: Optional[str] = Field(description="Reason for wait recommendation", default=None)
        volatility_risk: str = Field(description="Volatility assessment", default="Moderate")
        unusual_behavior: str = Field(description="Any unusual market behavior", default="Normal")
        overbought_oversold_alert: str = Field(description="Overbought/oversold conditions", default="Normal")
        note: str = Field(description="Additional trading insights", default="AI analysis")
        
        # === NEW ENHANCED FIELDS FOR COMPREHENSIVE ANALYSIS ===
        
        # 1. HISTORICAL TREND & MARKET STRUCTURE
        trend_strength: Literal["Strong", "Moderate", "Weak", "Reversal"] = Field(description="Detailed trend strength assessment", default="Moderate")
        market_structure: Literal["HH/HL", "LH/LL", "Consolidation", "Breakout"] = Field(description="Market structure pattern (Higher Highs/Lower Lows)", default="Consolidation")
        trend_continuation_probability: int = Field(description="Trend continuation probability 0-100", ge=0, le=100, default=50)
        
        # 2. BREAKOUT & BREAKDOWN ANALYSIS
        support_level: Optional[float] = Field(description="Key support level identified", default=None)
        resistance_level: Optional[float] = Field(description="Key resistance level identified", default=None)
        breakout_probability: int = Field(description="Breakout probability 0-100", ge=0, le=100, default=50)
        breakout_direction: Literal["Upward", "Downward", "Uncertain"] = Field(description="Expected breakout direction", default="Uncertain")
        consolidation_pattern: str = Field(description="Identified consolidation pattern", default="None detected")
        false_breakout_risk: Literal["High", "Medium", "Low"] = Field(description="Risk of false breakout", default="Medium")
        
        # 3. ADVANCED FIBONACCI ANALYSIS
        swing_high: Optional[float] = Field(description="Identified swing high price", default=None)
        swing_low: Optional[float] = Field(description="Identified swing low price", default=None)
        fibonacci_23_6: Optional[float] = Field(description="23.6% Fibonacci retracement level", default=None)
        fibonacci_38_2: Optional[float] = Field(description="38.2% Fibonacci retracement level", default=None)
        fibonacci_50_0: Optional[float] = Field(description="50% Fibonacci retracement level", default=None)
        fibonacci_61_8: Optional[float] = Field(description="61.8% Fibonacci retracement level", default=None)
        fibonacci_78_6: Optional[float] = Field(description="78.6% Fibonacci retracement level", default=None)
        fibonacci_extension_127: Optional[float] = Field(description="127.2% Fibonacci extension target", default=None)
        fibonacci_extension_161: Optional[float] = Field(description="161.8% Fibonacci extension target", default=None)
        fibonacci_extension_261: Optional[float] = Field(description="261.8% Fibonacci extension target", default=None)
        fibonacci_confluence: str = Field(description="Fibonacci confluence zones analysis", default="No confluence detected")
        
        # 4. VOLUME PROFILE & MARKET MICROSTRUCTURE
        volume_trend: Literal["Increasing", "Decreasing", "Divergent", "Normal"] = Field(description="Volume trend analysis", default="Normal")
        volume_confirmation: Literal["Strong", "Weak", "Neutral"] = Field(description="Volume confirmation for price movement", default="Neutral")
        smart_money_activity: Literal["Accumulation", "Distribution", "Neutral"] = Field(description="Smart money vs retail activity", default="Neutral")
        volume_divergence: str = Field(description="Volume divergence analysis", default="No divergence")
        institutional_behavior: str = Field(description="Institutional behavior indicators", default="Normal activity")
        
        # 5. MULTI-INDICATOR CONFLUENCE
        momentum_confluence: Literal["Bullish", "Bearish", "Neutral", "Mixed"] = Field(description="RSI, MACD, Stochastic alignment", default="Neutral")
        trend_confluence: Literal["Bullish", "Bearish", "Neutral", "Mixed"] = Field(description="EMA, Supertrend, ADX alignment", default="Neutral")
        volatility_analysis: str = Field(description="ATR, Bollinger Band analysis", default="Normal volatility")
        mean_reversion_signal: Literal["Overbought", "Oversold", "Normal"] = Field(description="Mean reversion indicators", default="Normal")
        indicator_strength: int = Field(description="Overall indicator confluence strength 0-100", ge=0, le=100, default=50)
        
        # 6. ENHANCED CANDLESTICK PATTERNS
        reversal_patterns: str = Field(description="Identified reversal candlestick patterns", default="None detected")
        continuation_patterns: str = Field(description="Identified continuation patterns", default="None detected")
        pattern_context: str = Field(description="Pattern context within current trend", default="No significant patterns")
        pattern_reliability: Literal["High", "Medium", "Low"] = Field(description="Pattern reliability assessment", default="Medium")
        
        # 7. ENHANCED RISK MANAGEMENT
        stop_loss_method: str = Field(description="Stop loss calculation method used", default="Standard")
        take_profit_1: Optional[float] = Field(description="First take profit target", default=None)
        take_profit_2: Optional[float] = Field(description="Second take profit target", default=None)
        take_profit_3: Optional[float] = Field(description="Third take profit target", default=None)
        position_size_recommendation: str = Field(description="Position size based on volatility", default="Standard position")
        max_drawdown_risk: str = Field(description="Maximum expected drawdown", default="Moderate")
        risk_level: Literal["Very Low", "Low", "Medium", "High", "Very High"] = Field(description="Overall risk assessment", default="Medium")
        
        # 8. MARKET SENTIMENT & PSYCHOLOGY
        fear_greed_indicator: Literal["Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"] = Field(description="Fear and greed assessment", default="Neutral")
        retail_sentiment: Literal["FOMO", "Panic", "Neutral", "Optimistic"] = Field(description="Retail trader sentiment", default="Neutral")
        market_psychology: str = Field(description="Overall market psychology analysis", default="Balanced sentiment")
        sentiment_extremes: str = Field(description="Extreme sentiment conditions", default="No extremes detected")
        
        # 9. ADDITIONAL PROFESSIONAL INSIGHTS
        confidence_level: int = Field(description="Analysis confidence level 0-100", ge=0, le=100, default=70)
        signal_quality: Literal["Excellent", "Good", "Average", "Poor"] = Field(description="Overall signal quality", default="Average")
        market_regime: Literal["Trending", "Ranging", "Volatile", "Breakout"] = Field(description="Current market regime", default="Ranging")
        time_horizon_detail: str = Field(description="Detailed time horizon analysis", default="Medium term")
        key_levels_to_watch: str = Field(description="Important price levels to monitor", default="Current support/resistance")
        catalyst_events: str = Field(description="Potential market moving events", default="No major catalysts identified")
        execution_notes: str = Field(description="Trade execution recommendations", default="Standard execution")
else:
    class AIAnalysisResponse:
        pass

class AIPoweredStrategy(BaseStrategy):
    """Real AI-powered strategy using Google Generative AI with LangChain"""
    
    def __init__(self):
        super().__init__("AI Powered")
        self.required_indicators = []
        self.ai_analysis_result = None
        self.ai_available = False
        
        if not LANGCHAIN_AVAILABLE:
            return
        
        # Initialize real AI components
        try:
            settings = get_settings()
            
            if not settings.GOOGLE_API_KEY or settings.GOOGLE_API_KEY == "":
                return
            
            # Set API key
            os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY
            
            # Initialize LangChain components
            self.llm = ChatGoogleGenerativeAI(
                model=settings.AI_MODEL_NAME,
                temperature=settings.AI_TEMPERATURE,
                max_retries=settings.AI_MAX_RETRIES,
                google_api_key=settings.GOOGLE_API_KEY
            )
            self.parser = PydanticOutputParser(pydantic_object=AIAnalysisResponse)
            self.ai_available = True
            
        except Exception as e:
            self.ai_available = False
    
    def _prepare_data_for_ai(self, df: pd.DataFrame) -> str:
        """Prepare last 50 rows of data for comprehensive AI analysis"""
        try:
            # Get last 50 rows with all indicators for comprehensive analysis
            recent_data = df.tail(50).copy()
            
            # Convert to dictionary format for AI
            data_dict = {}
            for i, (idx, row) in enumerate(recent_data.iterrows()):
                candle_data = {
                    "datetime": str(idx),
                    "open": float(row.get('open', 0)),
                    "high": float(row.get('high', 0)), 
                    "low": float(row.get('low', 0)),
                    "close": float(row.get('close', 0)),
                    "volume": float(row.get('volume', 0))
                }
                
                # Add all available indicators
                for col in row.index:
                    if col not in ['open', 'high', 'low', 'close', 'volume', 'time']:
                        if pd.notna(row[col]):
                            candle_data[col] = float(row[col])
                
                data_dict[f"candle_{i+1}"] = candle_data
            
            return str(data_dict)
        except Exception as e:
            return f"Error preparing data: {e}"
    
    def _create_ai_prompt(self) -> PromptTemplate:
        """Create the comprehensive advanced AI analysis prompt"""
        system_prompt = """
            You are an **Elite Professional Crypto Trader and Master Technical Analyst AI** with 15+ years of expertise in cryptocurrency markets, price action mastery, advanced pattern recognition, institutional-level analysis, and algorithmic trading strategies.

            You will receive a comprehensive dataset containing the last 50 candles of enriched historical cryptocurrency data, including OHLCV data and multiple advanced technical indicators (EMA, MACD, RSI, VWAP, Supertrend, ADX, ATR, Stochastic, Z-Score, Bollinger Bands, etc.).

            ## **COMPREHENSIVE ANALYSIS FRAMEWORK - MANDATORY REQUIREMENTS:**

            ### **1. HISTORICAL TREND & MARKET STRUCTURE ANALYSIS:**
            - Analyze the complete 50 candle dataset to identify:
            * **Primary Trend Direction**: Bullish, Bearish, or Consolidation
            * **Trend Strength**: Strong, Moderate, Weak, or Reversal Phase
            * **Market Structure**: Higher Highs/Higher Lows (HH/HL) or Lower Highs/Lower Lows (LH/LL)
            * **Trend Continuation vs Reversal Signals**: Based on price action and indicator confluence

            ### **2. BREAKOUT & BREAKDOWN ANALYSIS:**
            - Identify key levels and breakout scenarios:
            * **Support & Resistance Levels**: Calculate from historical swing highs/lows
            * **Breakout Confirmation**: Volume surge, candle close above/below key levels
            * **False Breakout Detection**: Weak volume, quick reversal patterns
            * **Consolidation Patterns**: Triangles, Rectangles, Flags, Pennants
            * **Breakout Direction Probability**: Based on volume profile and momentum

            ### **3. ADVANCED FIBONACCI RETRACEMENT ANALYSIS:**
            - Perform comprehensive Fibonacci analysis:
            * **Identify Swing Highs & Swing Lows**: From the 50 candle dataset
            * **Calculate Key Fibonacci Levels**: 23.6%, 38.2%, 50%, 61.8%, 78.6%
            * **Fibonacci Extension Targets**: 127.2%, 161.8%, 261.8% for profit targets
            * **Golden Ratio Confluences**: Multiple Fibonacci level alignments
            * **Fibonacci Support/Resistance**: Strong reaction zones and bounce levels

            ### **4. VOLUME PROFILE & MARKET MICROSTRUCTURE:**
            - Deep volume analysis:
            * **Volume Trends**: Increasing, Decreasing, or Divergent with price
            * **Volume Accumulation/Distribution**: Smart money vs retail activity
            * **Volume Breakout Confirmation**: High volume on breakouts
            * **Volume Divergence**: Price vs volume misalignment signals

            ### **5. MULTI-INDICATOR CONFLUENCE ANALYSIS:**
            - Analyze indicator combinations for signal strength:
            * **Momentum Confluence**: RSI, MACD, Stochastic alignment
            * **Trend Confluence**: EMA alignment, Supertrend direction, ADX strength
            * **Volatility Analysis**: ATR expansion/contraction, Bollinger Band squeezes
            * **Mean Reversion**: Z-Score extremes, RSI overbought/oversold

            ### **6. CANDLESTICK PATTERN RECOGNITION:**
            - Identify and analyze candlestick patterns:
            * **Reversal Patterns**: Doji, Hammer, Shooting Star, Engulfing, Evening/Morning Star
            * **Continuation Patterns**: Spinning Tops, Small Bodies, Flag patterns
            * **Pattern Context**: Position within trend, volume confirmation, indicator support

            ### **7. RISK MANAGEMENT & POSITION SIZING:**
            - Calculate precise risk parameters:
            * **Stop Loss Placement**: Based on ATR, support/resistance, or pattern invalidation
            * **Take Profit Targets**: Multiple targets using Fibonacci extensions and resistance levels
            * **Risk-to-Reward Ratio**: MINIMUM 1:2, preferably 1:3 or higher
            * **Position Size**: Based on volatility (ATR) and account risk percentage

            ### **8. MARKET SENTIMENT & PSYCHOLOGY:**
            - Assess market psychology:
            * **Fear/Greed Indicators**: Extreme RSI readings, volume spikes
            * **Smart Money Activity**: Large volume at key levels, institutional behavior
            * **Retail Sentiment**: FOMO patterns, panic selling/buying signals

            ## **OUTPUT REQUIREMENTS:**

            Provide a comprehensive analysis covering ALL above points and conclude with:

            1. **Primary Trading Signal**: BUY/SELL/WAIT with specific reasoning
            2. **Signal Strength**: 0-100 based on confluence of factors
            3. **Entry Strategy**: Exact entry price with rationale
            4. **Risk Management**: Stop loss, take profit levels, position sizing
            5. **Time Horizon**: Expected holding period based on analysis
            6. **Confidence Level**: Based on pattern strength and confluence

            ## **CRITICAL ANALYSIS STANDARDS:**
            - Use ONLY the provided 50 candle data for calculations
            - Every recommendation MUST be backed by specific data points
            - Identify exact price levels for entries, stops, and targets
            - Maintain professional institutional-level analysis quality
            - Provide actionable insights with clear risk parameters

            Respond in valid JSON format matching the Pydantic model structure.

            **Analyze the following comprehensive crypto market data:**
{data}

{format_instructions}
"""
        
        return PromptTemplate(
            template=system_prompt,
            input_variables=["data"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )
    
    def analyze(self, df: pd.DataFrame, latest_data: pd.Series) -> StrategyResult:
        """Real AI analysis using Google Generative AI"""
        conditions_met = []
        conditions_failed = []
        
        if not self.ai_available:
            return StrategyResult(
                name=self.name,
                signal=SignalType.NEUTRAL,
                confidence=ConfidenceLevel.VERY_LOW,
                strength=0,
                interpretation="Real AI not available - install: pip install langchain langchain-google-genai and add GOOGLE_API_KEY",
                conditions_met=[],
                conditions_failed=["Missing LangChain dependencies or Google API key"]
            )
        
        try:
            # Prepare real market data for AI
            data_str = self._prepare_data_for_ai(df)
            conditions_met.append("Market data prepared for real AI analysis")
            
            # Create AI prompt and chain
            prompt = self._create_ai_prompt()
            chain = prompt | self.llm | self.parser
            
            # Get REAL AI analysis from Google Generative AI
            ai_result = chain.invoke({"data": data_str})
            
            # Store the comprehensive REAL AI result with all enhanced fields
            self.ai_analysis_result = {
                # === EXISTING FIELDS ===
                "summary": ai_result.summary,
                "current_trend": ai_result.current_trend,
                "candlestick_patterns": ai_result.candlestick_patterns,
                "strength": ai_result.strength,
                "recommendation": ai_result.recommendation,
                "reason": ai_result.reason,
                "price_movement": ai_result.price_movement,
                "momentum_forecast": ai_result.momentum_forecast,
                "action_type": ai_result.action_type,
                "action_strength": ai_result.action_strength,
                "entry_price": ai_result.entry_price,
                "stoploss": ai_result.stoploss,
                "target": ai_result.target,
                "risk_to_reward": ai_result.risk_to_reward,
                "max_holding_period": ai_result.max_holding_period,
                "reason_to_hold": ai_result.reason_to_hold,
                "volatility_risk": ai_result.volatility_risk,
                "unusual_behavior": ai_result.unusual_behavior,
                "overbought_oversold_alert": ai_result.overbought_oversold_alert,
                "note": ai_result.note,
                
                # === NEW ENHANCED FIELDS ===
                # 1. Historical Trend & Market Structure
                "trend_strength": ai_result.trend_strength,
                "market_structure": ai_result.market_structure,
                "trend_continuation_probability": ai_result.trend_continuation_probability,
                
                # 2. Breakout & Breakdown Analysis
                "support_level": ai_result.support_level,
                "resistance_level": ai_result.resistance_level,
                "breakout_probability": ai_result.breakout_probability,
                "breakout_direction": ai_result.breakout_direction,
                "consolidation_pattern": ai_result.consolidation_pattern,
                "false_breakout_risk": ai_result.false_breakout_risk,
                
                # 3. Advanced Fibonacci Analysis
                "swing_high": ai_result.swing_high,
                "swing_low": ai_result.swing_low,
                "fibonacci_23_6": ai_result.fibonacci_23_6,
                "fibonacci_38_2": ai_result.fibonacci_38_2,
                "fibonacci_50_0": ai_result.fibonacci_50_0,
                "fibonacci_61_8": ai_result.fibonacci_61_8,
                "fibonacci_78_6": ai_result.fibonacci_78_6,
                "fibonacci_extension_127": ai_result.fibonacci_extension_127,
                "fibonacci_extension_161": ai_result.fibonacci_extension_161,
                "fibonacci_extension_261": ai_result.fibonacci_extension_261,
                "fibonacci_confluence": ai_result.fibonacci_confluence,
                
                # 4. Volume Profile & Market Microstructure
                "volume_trend": ai_result.volume_trend,
                "volume_confirmation": ai_result.volume_confirmation,
                "smart_money_activity": ai_result.smart_money_activity,
                "volume_divergence": ai_result.volume_divergence,
                "institutional_behavior": ai_result.institutional_behavior,
                
                # 5. Multi-Indicator Confluence
                "momentum_confluence": ai_result.momentum_confluence,
                "trend_confluence": ai_result.trend_confluence,
                "volatility_analysis": ai_result.volatility_analysis,
                "mean_reversion_signal": ai_result.mean_reversion_signal,
                "indicator_strength": ai_result.indicator_strength,
                
                # 6. Enhanced Candlestick Patterns
                "reversal_patterns": ai_result.reversal_patterns,
                "continuation_patterns": ai_result.continuation_patterns,
                "pattern_context": ai_result.pattern_context,
                "pattern_reliability": ai_result.pattern_reliability,
                
                # 7. Enhanced Risk Management
                "stop_loss_method": ai_result.stop_loss_method,
                "take_profit_1": ai_result.take_profit_1,
                "take_profit_2": ai_result.take_profit_2,
                "take_profit_3": ai_result.take_profit_3,
                "position_size_recommendation": ai_result.position_size_recommendation,
                "max_drawdown_risk": ai_result.max_drawdown_risk,
                "risk_level": ai_result.risk_level,
                
                # 8. Market Sentiment & Psychology
                "fear_greed_indicator": ai_result.fear_greed_indicator,
                "retail_sentiment": ai_result.retail_sentiment,
                "market_psychology": ai_result.market_psychology,
                "sentiment_extremes": ai_result.sentiment_extremes,
                
                # 9. Additional Professional Insights
                "confidence_level": ai_result.confidence_level,
                "signal_quality": ai_result.signal_quality,
                "market_regime": ai_result.market_regime,
                "time_horizon_detail": ai_result.time_horizon_detail,
                "key_levels_to_watch": ai_result.key_levels_to_watch,
                "catalyst_events": ai_result.catalyst_events,
                "execution_notes": ai_result.execution_notes
            }
            
            conditions_met.append("Real AI analysis completed successfully")
            conditions_met.append(f"AI detected patterns: {ai_result.candlestick_patterns}")
            conditions_met.append(f"AI trend analysis: {ai_result.current_trend}")
            
            # Convert AI recommendation to strategy signal
            if ai_result.recommendation == "Buy":
                signal = SignalType.BUY
                confidence = ConfidenceLevel.VERY_HIGH if ai_result.strength == "Strong" else ConfidenceLevel.HIGH
            elif ai_result.recommendation == "Sell":
                signal = SignalType.SELL
                confidence = ConfidenceLevel.VERY_HIGH if ai_result.strength == "Strong" else ConfidenceLevel.HIGH
            else:  # Wait
                signal = SignalType.HOLD
                confidence = ConfidenceLevel.MEDIUM
            
            strength = ai_result.action_strength
            interpretation = f"Real AI: {ai_result.reason}"
            
        except Exception as e:
            conditions_failed.append(f"Real AI analysis failed: {str(e)}")
            signal = SignalType.NEUTRAL
            confidence = ConfidenceLevel.VERY_LOW
            strength = 0
            interpretation = "Real AI analysis failed - check API key and internet connection"
            
            # Comprehensive fallback result when AI fails
            self.ai_analysis_result = {
                # === EXISTING FIELDS ===
                "summary": "AI analysis failed due to technical error",
                "current_trend": "Sideways",
                "candlestick_patterns": "Unable to analyze patterns",
                "strength": "Weak",
                "recommendation": "Wait",
                "reason": f"Technical error: {str(e)}",
                "price_movement": "Sideways",
                "momentum_forecast": "Unable to forecast due to error",
                "action_type": "Wait",
                "action_strength": 0,
                "entry_price": None,
                "stoploss": None,
                "target": None,
                "risk_to_reward": "N/A",
                "max_holding_period": None,
                "reason_to_hold": "Analysis failed, wait for system recovery",
                "volatility_risk": "Unknown",
                "unusual_behavior": "System error occurred",
                "overbought_oversold_alert": "Data unavailable",
                "note": "Please check AI configuration and try again",
                
                # === NEW ENHANCED FIELDS - DEFAULT VALUES ===
                # 1. Historical Trend & Market Structure
                "trend_strength": "Weak",
                "market_structure": "Consolidation",
                "trend_continuation_probability": 50,
                
                # 2. Breakout & Breakdown Analysis
                "support_level": None,
                "resistance_level": None,
                "breakout_probability": 50,
                "breakout_direction": "Uncertain",
                "consolidation_pattern": "Analysis failed",
                "false_breakout_risk": "High",
                
                # 3. Advanced Fibonacci Analysis
                "swing_high": None,
                "swing_low": None,
                "fibonacci_23_6": None,
                "fibonacci_38_2": None,
                "fibonacci_50_0": None,
                "fibonacci_61_8": None,
                "fibonacci_78_6": None,
                "fibonacci_extension_127": None,
                "fibonacci_extension_161": None,
                "fibonacci_extension_261": None,
                "fibonacci_confluence": "Unable to calculate due to error",
                
                # 4. Volume Profile & Market Microstructure
                "volume_trend": "Normal",
                "volume_confirmation": "Neutral",
                "smart_money_activity": "Neutral",
                "volume_divergence": "Unable to analyze",
                "institutional_behavior": "Data unavailable",
                
                # 5. Multi-Indicator Confluence
                "momentum_confluence": "Neutral",
                "trend_confluence": "Neutral",
                "volatility_analysis": "Unable to analyze",
                "mean_reversion_signal": "Normal",
                "indicator_strength": 0,
                
                # 6. Enhanced Candlestick Patterns
                "reversal_patterns": "Analysis failed",
                "continuation_patterns": "Analysis failed",
                "pattern_context": "Unable to determine due to error",
                "pattern_reliability": "Low",
                
                # 7. Enhanced Risk Management
                "stop_loss_method": "Error - unable to calculate",
                "take_profit_1": None,
                "take_profit_2": None,
                "take_profit_3": None,
                "position_size_recommendation": "Avoid trading during system error",
                "max_drawdown_risk": "Unknown",
                "risk_level": "Very High",
                
                # 8. Market Sentiment & Psychology
                "fear_greed_indicator": "Neutral",
                "retail_sentiment": "Neutral",
                "market_psychology": "Unable to assess due to error",
                "sentiment_extremes": "System error - data unavailable",
                
                # 9. Additional Professional Insights
                "confidence_level": 0,
                "signal_quality": "Poor",
                "market_regime": "Ranging",
                "time_horizon_detail": "Wait for system recovery",
                "key_levels_to_watch": "Unable to identify due to error",
                "catalyst_events": "System maintenance required",
                "execution_notes": "Do not trade until AI system is restored"
            }
        
        return StrategyResult(
            name=self.name,
            signal=signal,
            confidence=confidence,
            strength=strength,
            interpretation=interpretation,
            conditions_met=conditions_met,
            conditions_failed=conditions_failed
        )
    
    def get_ai_analysis(self) -> Optional[dict]:
        """Get the real AI analysis result from Google Generative AI"""
        return self.ai_analysis_result 