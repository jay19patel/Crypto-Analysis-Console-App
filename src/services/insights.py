#!/usr/bin/env python3
"""
Market Data Insights Module
Analyzes real-time market data and extracts meaningful insights
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import math
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
import os

@dataclass
class MarketInsights:
    """Market insights data structure"""
    symbol: str
    timestamp: str
    price_insights: Dict[str, Any]
    volume_insights: Dict[str, Any]
    volatility_insights: Dict[str, Any]
    funding_insights: Dict[str, Any]
    order_book_insights: Dict[str, Any]
    risk_insights: Dict[str, Any]
    trend_insights: Dict[str, Any]

class MarketDataAnalyzer:
    """Analyzes market data and extracts insights"""
    
    def __init__(self):
        self.logger = logging.getLogger("market_insights")
        self.historical_data: Dict[str, List[Dict]] = {}
        self.max_history = 100  # Keep last 100 data points per symbol
        
    def analyze_market_data(self, symbol: str, price_data: Dict[str, Any]) -> MarketInsights:
        """Analyze market data and extract insights"""
        try:
            # Add to historical data
            if symbol not in self.historical_data:
                self.historical_data[symbol] = []
            
            self.historical_data[symbol].append(price_data)
            
            # Keep only recent data
            if len(self.historical_data[symbol]) > self.max_history:
                self.historical_data[symbol] = self.historical_data[symbol][-self.max_history:]
            
            # Extract insights
            price_insights = self._analyze_price_insights(symbol, price_data)
            volume_insights = self._analyze_volume_insights(symbol, price_data)
            volatility_insights = self._analyze_volatility_insights(symbol, price_data)
            funding_insights = self._analyze_funding_insights(symbol, price_data)
            order_book_insights = self._analyze_order_book_insights(symbol, price_data)
            risk_insights = self._analyze_risk_insights(symbol, price_data)
            trend_insights = self._analyze_trend_insights(symbol, price_data)
            
            return MarketInsights(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc).isoformat(),
                price_insights=price_insights,
                volume_insights=volume_insights,
                volatility_insights=volatility_insights,
                funding_insights=funding_insights,
                order_book_insights=order_book_insights,
                risk_insights=risk_insights,
                trend_insights=trend_insights
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing market data: {str(e)}")
            return self._create_empty_insights(symbol)
    
    def _analyze_price_insights(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze price-related insights"""
        try:
            mark_price = float(data.get('mark_price', 0))
            spot_price = float(data.get('spot_price', 0))
            high_24h = float(data.get('high', 0))
            low_24h = float(data.get('low', 0))
            open_price = float(data.get('open', 0))
            
            # Price spread analysis
            price_spread = abs(mark_price - spot_price) if spot_price else 0
            spread_percentage = (price_spread / mark_price * 100) if mark_price else 0
            
            # Price range analysis
            price_range = high_24h - low_24h
            price_range_percentage = (price_range / mark_price * 100) if mark_price else 0
            
            # Price position within range
            price_position = ((mark_price - low_24h) / price_range * 100) if price_range else 50
            
            # Daily change
            daily_change = ((mark_price - open_price) / open_price * 100) if open_price else 0
            
            return {
                "current_price": mark_price,
                "spot_price": spot_price,
                "price_spread": price_spread,
                "spread_percentage": round(spread_percentage, 4),
                "price_range": price_range,
                "price_range_percentage": round(price_range_percentage, 2),
                "price_position_in_range": round(price_position, 2),
                "daily_change_percentage": round(daily_change, 2),
                "high_24h": high_24h,
                "low_24h": low_24h,
                "open_price": open_price,
                "price_volatility": "HIGH" if price_range_percentage > 10 else "MEDIUM" if price_range_percentage > 5 else "LOW"
            }
        except Exception as e:
            self.logger.error(f"Error in price insights: {str(e)}")
            return {}
    
    def _analyze_volume_insights(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volume-related insights"""
        try:
            volume = float(data.get('volume', 0))
            turnover = float(data.get('turnover', 0))
            turnover_usd = float(data.get('turnover_usd', 0))
            open_interest = float(data.get('open_interest', 0))
            oi_value_usd = float(data.get('oi_value_usd', 0))
            
            # Volume analysis
            avg_price = (turnover / volume) if volume else 0
            volume_intensity = "HIGH" if volume > 10000 else "MEDIUM" if volume > 1000 else "LOW"
            
            # Open Interest analysis
            oi_intensity = "HIGH" if open_interest > 1000 else "MEDIUM" if open_interest > 100 else "LOW"
            
            return {
                "volume": volume,
                "turnover_usd": turnover_usd,
                "average_price": round(avg_price, 2),
                "volume_intensity": volume_intensity,
                "open_interest": open_interest,
                "oi_value_usd": oi_value_usd,
                "oi_intensity": oi_intensity,
                "volume_oi_ratio": round(volume / open_interest, 2) if open_interest else 0
            }
        except Exception as e:
            self.logger.error(f"Error in volume insights: {str(e)}")
            return {}
    
    def _analyze_volatility_insights(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volatility-related insights"""
        try:
            mark_iv = float(data.get('mark_iv', 0))
            mark_basis = float(data.get('mark_basis', 0))
            price_band_lower = float(data.get('price_band_lower', 0))
            price_band_upper = float(data.get('price_band_upper', 0))
            current_price = float(data.get('mark_price', 0))
            
            # Volatility analysis
            volatility_level = "HIGH" if abs(mark_iv) > 0.5 else "MEDIUM" if abs(mark_iv) > 0.2 else "LOW"
            
            # Price band analysis
            band_width = price_band_upper - price_band_lower
            price_position_in_band = ((current_price - price_band_lower) / band_width * 100) if band_width else 50
            
            return {
                "implied_volatility": mark_iv,
                "mark_basis": mark_basis,
                "volatility_level": volatility_level,
                "price_band_lower": price_band_lower,
                "price_band_upper": price_band_upper,
                "price_position_in_band": round(price_position_in_band, 2),
                "band_width": band_width,
                "volatility_risk": "HIGH" if volatility_level == "HIGH" else "MEDIUM"
            }
        except Exception as e:
            self.logger.error(f"Error in volatility insights: {str(e)}")
            return {}
    
    def _analyze_funding_insights(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze funding-related insights"""
        try:
            funding_rate = float(data.get('funding_rate', 0))
            mark_basis = float(data.get('mark_basis', 0))
            
            # Funding analysis
            funding_direction = "POSITIVE" if funding_rate > 0 else "NEGATIVE" if funding_rate < 0 else "NEUTRAL"
            funding_intensity = "HIGH" if abs(funding_rate) > 0.01 else "MEDIUM" if abs(funding_rate) > 0.005 else "LOW"
            
            return {
                "funding_rate": funding_rate,
                "mark_basis": mark_basis,
                "funding_direction": funding_direction,
                "funding_intensity": funding_intensity,
                "funding_risk": "HIGH" if funding_intensity == "HIGH" else "MEDIUM"
            }
        except Exception as e:
            self.logger.error(f"Error in funding insights: {str(e)}")
            return {}
    
    def _analyze_order_book_insights(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze order book insights"""
        try:
            best_bid = float(data.get('best_bid', 0))
            best_ask = float(data.get('best_ask', 0))
            bid_size = float(data.get('bid_size', 0))
            ask_size = float(data.get('ask_size', 0))
            
            # Spread analysis
            spread = best_ask - best_bid
            spread_percentage = (spread / best_bid * 100) if best_bid else 0
            
            # Order book imbalance
            total_size = bid_size + ask_size
            bid_ratio = (bid_size / total_size * 100) if total_size else 50
            ask_ratio = (ask_size / total_size * 100) if total_size else 50
            
            # Market depth analysis
            depth_level = "HIGH" if total_size > 1000 else "MEDIUM" if total_size > 100 else "LOW"
            
            return {
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread": spread,
                "spread_percentage": round(spread_percentage, 4),
                "bid_size": bid_size,
                "ask_size": ask_size,
                "bid_ratio": round(bid_ratio, 2),
                "ask_ratio": round(ask_ratio, 2),
                "order_imbalance": "BID_HEAVY" if bid_ratio > 60 else "ASK_HEAVY" if ask_ratio > 60 else "BALANCED",
                "market_depth": depth_level
            }
        except Exception as e:
            self.logger.error(f"Error in order book insights: {str(e)}")
            return {}
    
    def _analyze_risk_insights(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze risk-related insights"""
        try:
            initial_margin = float(data.get('initial_margin', 0))
            price_band_lower = float(data.get('price_band_lower', 0))
            price_band_upper = float(data.get('price_band_upper', 0))
            current_price = float(data.get('mark_price', 0))
            
            # Risk analysis
            margin_risk = "HIGH" if initial_margin < 0.1 else "MEDIUM" if initial_margin < 0.5 else "LOW"
            
            # Price band risk
            band_width = price_band_upper - price_band_lower
            price_position = ((current_price - price_band_lower) / band_width * 100) if band_width else 50
            band_risk = "HIGH" if price_position < 10 or price_position > 90 else "MEDIUM" if price_position < 20 or price_position > 80 else "LOW"
            
            # Overall risk assessment
            overall_risk = "HIGH" if margin_risk == "HIGH" or band_risk == "HIGH" else "MEDIUM" if margin_risk == "MEDIUM" or band_risk == "MEDIUM" else "LOW"
            
            return {
                "initial_margin": initial_margin,
                "margin_risk": margin_risk,
                "price_band_lower": price_band_lower,
                "price_band_upper": price_band_upper,
                "price_position_in_band": round(price_position, 2),
                "band_risk": band_risk,
                "overall_risk_level": overall_risk,
                "risk_factors": []
            }
        except Exception as e:
            self.logger.error(f"Error in risk insights: {str(e)}")
            return {}
    
    def _analyze_trend_insights(self, symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze trend-related insights"""
        try:
            mark_change_24h = float(data.get('mark_change_24h', 0))
            current_price = float(data.get('mark_price', 0))
            open_price = float(data.get('open', 0))
            
            # Trend analysis
            trend_direction = "BULLISH" if mark_change_24h > 0 else "BEARISH" if mark_change_24h < 0 else "SIDEWAYS"
            trend_strength = "STRONG" if abs(mark_change_24h) > 5 else "MODERATE" if abs(mark_change_24h) > 2 else "WEAK"
            
            # Price momentum
            momentum = "POSITIVE" if current_price > open_price else "NEGATIVE" if current_price < open_price else "NEUTRAL"
            
            return {
                "mark_change_24h": mark_change_24h,
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "price_momentum": momentum,
                "trend_confidence": "HIGH" if trend_strength == "STRONG" else "MEDIUM" if trend_strength == "MODERATE" else "LOW"
            }
        except Exception as e:
            self.logger.error(f"Error in trend insights: {str(e)}")
            return {}
    
    def _create_empty_insights(self, symbol: str) -> MarketInsights:
        """Create empty insights when analysis fails"""
        return MarketInsights(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc).isoformat(),
            price_insights={},
            volume_insights={},
            volatility_insights={},
            funding_insights={},
            order_book_insights={},
            risk_insights={},
            trend_insights={}
        )
    
    def get_insights_as_dict(self, insights: MarketInsights) -> Dict[str, Any]:
        """Convert insights to dictionary format"""
        return asdict(insights)
    
    def save_insights_to_json(self, insights: MarketInsights, filename: str = None) -> str:
        """Save insights to JSON file"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"market_insights_{insights.symbol}_{timestamp}.json"
            
            insights_dict = self.get_insights_as_dict(insights)
            
            with open(filename, 'w') as f:
                json.dump(insights_dict, f, indent=2)
            
            return filename
        except Exception as e:
            self.logger.error(f"Error saving insights to JSON: {str(e)}")
            return "" 

    @staticmethod
    def fetch_live_prices_from_db(symbol: str, mongo_uri: str, db_name: str, collection_name: str, limit: int = 100) -> list:
        """Fetch live price data for a specific symbol from MongoDB"""
        client = MongoClient(mongo_uri)
        db = client[db_name]
        collection = db[collection_name]
        cursor = collection.find({"symbol": symbol}).sort("timestamp", -1).limit(limit)
        data = list(cursor)
        client.close()
        return data

    @staticmethod
    def dataframe_from_price_data(price_data_list: list) -> pd.DataFrame:
        """Convert list of price data dicts to pandas DataFrame and optimize/clean"""
        if not price_data_list:
            return pd.DataFrame()
        # Remove MongoDB _id
        for d in price_data_list:
            d.pop('_id', None)
        df = pd.DataFrame(price_data_list)
        # Convert timestamp to datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        # Sort by timestamp ascending
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df

    def add_insights_to_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add insights columns to DataFrame using analyze_market_data for each row"""
        if df.empty:
            return df
        insights_list = []
        for _, row in df.iterrows():
            insights = self.analyze_market_data(row['symbol'], row.to_dict())
            insights_dict = self.get_insights_as_dict(insights)
            # Flatten nested dicts
            flat = {}
            for k, v in insights_dict.items():
                if isinstance(v, dict):
                    for subk, subv in v.items():
                        flat[f"{k}_{subk}"] = subv
                else:
                    flat[k] = v
            insights_list.append(flat)
        insights_df = pd.DataFrame(insights_list)
        # Merge with original df
        result = pd.concat([df.reset_index(drop=True), insights_df.reset_index(drop=True)], axis=1)
        return result

    @staticmethod
    def save_dataframe_and_visualizations(df: pd.DataFrame, output_dir: str, symbol: str = None):
        """Save DataFrame as CSV and generate visualizations for insights and data"""
        os.makedirs(output_dir, exist_ok=True)
        # Save CSV
        csv_path = os.path.join(output_dir, f"{symbol or 'data'}_with_insights.csv")
        df.to_csv(csv_path, index=False)
        # Visualizations
        plt.style.use('seaborn-v0_8')
        # 1. Price over time
        if 'timestamp' in df.columns and 'mark_price' in df.columns:
            plt.figure(figsize=(12,6))
            plt.plot(df['timestamp'], df['mark_price'], label='Mark Price')
            if 'spot_price' in df.columns:
                plt.plot(df['timestamp'], df['spot_price'], label='Spot Price', alpha=0.7)
            plt.title(f"{symbol} Price Over Time")
            plt.xlabel('Timestamp')
            plt.ylabel('Price')
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_price_lineplot.png"))
            plt.close()
        # 2. Volume over time
        if 'timestamp' in df.columns and 'volume' in df.columns:
            plt.figure(figsize=(12,6))
            plt.bar(df['timestamp'], df['volume'], color='skyblue')
            plt.title(f"{symbol} Volume Over Time")
            plt.xlabel('Timestamp')
            plt.ylabel('Volume')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_volume_barchart.png"))
            plt.close()
        # 3. Daily change percentage (if available)
        if 'price_insights_daily_change_percentage' in df.columns:
            plt.figure(figsize=(12,6))
            plt.plot(df['timestamp'], df['price_insights_daily_change_percentage'], label='Daily Change %', color='orange')
            plt.title(f"{symbol} Daily Change Percentage Over Time")
            plt.xlabel('Timestamp')
            plt.ylabel('Daily Change (%)')
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_daily_change_lineplot.png"))
            plt.close()
        # 4. Volatility level count
        if 'volatility_insights_volatility_level' in df.columns:
            plt.figure(figsize=(8,5))
            sns.countplot(x='volatility_insights_volatility_level', data=df)
            plt.title(f"{symbol} Volatility Level Distribution")
            plt.xlabel('Volatility Level')
            plt.ylabel('Count')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_volatility_level_bar.png"))
            plt.close()
        # 5. Funding rate over time
        if 'timestamp' in df.columns and 'funding_rate' in df.columns:
            plt.figure(figsize=(12,6))
            plt.plot(df['timestamp'], df['funding_rate'], label='Funding Rate', color='green')
            plt.title(f"{symbol} Funding Rate Over Time")
            plt.xlabel('Timestamp')
            plt.ylabel('Funding Rate')
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_funding_rate_lineplot.png"))
            plt.close()
        # 6. Risk level count
        if 'risk_insights_overall_risk_level' in df.columns:
            plt.figure(figsize=(8,5))
            sns.countplot(x='risk_insights_overall_risk_level', data=df)
            plt.title(f"{symbol} Overall Risk Level Distribution")
            plt.xlabel('Risk Level')
            plt.ylabel('Count')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_risk_level_bar.png"))
            plt.close()
        # 7. Trend direction count
        if 'trend_insights_trend_direction' in df.columns:
            plt.figure(figsize=(8,5))
            sns.countplot(x='trend_insights_trend_direction', data=df)
            plt.title(f"{symbol} Trend Direction Distribution")
            plt.xlabel('Trend Direction')
            plt.ylabel('Count')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_trend_direction_bar.png"))
            plt.close()
        # 8. Correlation heatmap (for numeric columns)
        numeric_cols = df.select_dtypes(include='number').columns
        if len(numeric_cols) > 2:
            plt.figure(figsize=(14,10))
            corr = df[numeric_cols].corr()
            sns.heatmap(corr, annot=False, cmap='coolwarm')
            plt.title(f"{symbol} Numeric Feature Correlation Heatmap")
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{symbol}_correlation_heatmap.png"))
            plt.close()
        # More plots can be added as needed
        return csv_path 