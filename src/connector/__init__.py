"""Binary Options Trade Connector.

Import this from any Python project to execute trades with full event logging.

Usage:
    from src.connector import TradeEngine, TradeConfig

    engine = TradeEngine(TradeConfig(mode="test"))
    engine.start()
    result = engine.open_position("Bitcoin OTC", "CALL")
    print(result.result, result.payout)
    engine.stop()
"""

from src.connector.engine import TradeEngine, TradeConfig
from src.connector.events import TradeEvent, TradeSummary, EventKind
from src.connector.logger import TradeLogger

__all__ = [
    "TradeEngine",
    "TradeConfig",
    "TradeEvent",
    "TradeSummary",
    "EventKind",
    "TradeLogger",
]
