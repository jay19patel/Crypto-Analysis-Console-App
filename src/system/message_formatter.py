from datetime import datetime
from typing import Any, Dict, Optional
import json
from enum import Enum

class MessageType(Enum):
    LOGS = "logs"
    ANALYSIS = "analysis"
    POSITIONS = "positions"
    LIVE_PRICE = "liveprice"
    TRADE_LOGS = "tradelogs"
    SYSTEM = "system"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    SUCCESS = "success"

class MessageFormatter:
    @staticmethod
    def format_message(msg_type: MessageType, data: Any, source: str = "", level: str = "info") -> Dict:
        """Format a message for WebSocket transmission
        
        Args:
            msg_type: Type of message (logs, analysis, positions, etc)
            data: The actual message data
            source: Source component of the message
            level: Message level (info, warning, error, success)
            
        Returns:
            Formatted message dictionary
        """
        return {
            "type": msg_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "level": level,
            "data": data
        }

    @staticmethod
    def format_log(message: str, level: str = "info", source: str = "") -> Dict:
        """Format a log message"""
        return MessageFormatter.format_message(
            MessageType.LOGS,
            {"message": message},
            source=source,
            level=level
        )

    @staticmethod
    def format_error(message: str, source: str = "", error: Optional[Exception] = None) -> Dict:
        """Format an error message"""
        data = {
            "message": message,
            "error": str(error) if error else None
        }
        return MessageFormatter.format_message(
            MessageType.ERROR,
            data,
            source=source,
            level="error"
        )

    @staticmethod
    def format_analysis(analysis_data: Dict, source: str = "") -> Dict:
        """Format analysis data"""
        return MessageFormatter.format_message(
            MessageType.ANALYSIS,
            analysis_data,
            source=source
        )

    @staticmethod
    def format_position_update(position_data: Dict, source: str = "") -> Dict:
        """Format position update data"""
        return MessageFormatter.format_message(
            MessageType.POSITIONS,
            position_data,
            source=source
        )

    @staticmethod
    def format_trade_log(
        message: str,
        trade_type: str,
        position_id: Optional[str] = None,
        source: str = ""
    ) -> Dict:
        """Format trade log message"""
        data = {
            "message": message,
            "trade_type": trade_type,
            "position_id": position_id
        }
        return MessageFormatter.format_message(
            MessageType.TRADE_LOGS,
            data,
            source=source
        )

    @staticmethod
    def format_system_status(
        component: str,
        status: str,
        details: Optional[str] = None,
        source: str = ""
    ) -> Dict:
        """Format system status message"""
        data = {
            "component": component,
            "status": status,
            "details": details
        }
        return MessageFormatter.format_message(
            MessageType.SYSTEM,
            data,
            source=source
        )

    @staticmethod
    def to_string(message: Dict) -> str:
        """Convert message to JSON string"""
        return json.dumps(message) 