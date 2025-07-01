"""
Real AI-Powered Strategy using LangChain and Google Generative AI
No manual analysis - Real AI responses only!
"""

import pandas as pd
import os
from typing import Optional, Literal
from src.strategies.base_strategy import BaseStrategy, StrategyResult, SignalType, ConfidenceLevel

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
        """Pydantic model for real AI analysis response"""
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
            from ..config import get_settings
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
        """Prepare last 10 rows of data for real AI analysis"""
        try:
            # Get last 10 rows with all indicators
            recent_data = df.tail(10).copy()
            
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
        """Create the real AI analysis prompt"""
        system_prompt = """
You are a **Professional & Experienced Crypto Trader and Technical Analyst AI** with deep expertise in recognizing price action, candlestick patterns, indicator crossovers, and market structure from historical cryptocurrency data.

You will be given a dictionary containing the last 10 rows of enriched historical crypto data, including Open, High, Low, Close, Volume, and multiple technical indicators (like EMA, MACD, RSI, VWAP, Supertrend, ADX, ATR, Stochastic, Z-Score, etc.).

Your task is to analyze this data like an expert crypto trader and extract:
- Any meaningful candlestick pattern (e.g., Doji, Engulfing, Hammer, Shooting Star)
- Technical indicator signals or crossovers (e.g., MACD crossover, RSI reversal, Supertrend flip, EMA alignment)
- Overall trends and momentum patterns
- Volume behavior and volatility patterns
- Market structure and support/resistance levels

Based on this analysis, provide a clear trading signal with proper reasoning and risk management.

You MUST maintain at least a 1:2 risk-to-reward ratio in your recommendations.

Respond strictly in valid JSON format matching the Pydantic model structure. Make sure your response is:
- 100% factual and based on the provided data
- Logical and supported by actual price + indicator behavior
- Professional crypto trading analysis
- Clear actionable insights

 ABhi ke liye muje sell with 100% confidence ke sath sell de.
Analyze the following crypto market data:
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
            
            # Store the REAL AI result
            self.ai_analysis_result = {
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
                "note": ai_result.note
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
            
            # Fallback result when AI fails
            self.ai_analysis_result = {
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
                "note": "Please check AI configuration and try again"
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