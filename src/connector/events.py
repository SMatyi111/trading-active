"""Event types for the binary options trade lifecycle."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Literal


EventKind = Literal[
    "SIGNAL_RECEIVED",
    "BROWSER_READY",
    "LOGIN_START",
    "LOGIN_COMPLETE",
    "PAIR_SELECT_START",
    "PAIR_SELECT_COMPLETE",
    "EXPIRY_SET",
    "AMOUNT_SET",
    "TRADE_CLICK_START",
    "TRADE_CLICK_UI",
    "TRADE_CONFIRMED",
    "TRADE_OPEN",
    "TRADE_EXPIRED",
    "TRADE_SETTLED",
    "BALANCE_CHECK",
    "ERROR",
    "SESSION_START",
    "SESSION_END",
]


@dataclass
class TradeEvent:
    """One event in a trade's lifecycle, keyed by trade_id."""

    trade_id: str
    kind: EventKind
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Context
    pair: Optional[str] = None
    direction: Optional[str] = None
    expiry_sec: Optional[int] = None
    amount: Optional[float] = None
    round_num: Optional[int] = None

    # Timing (ms)
    elapsed_ms: Optional[float] = None
    step_duration_ms: Optional[float] = None
    click_to_ui_ms: Optional[float] = None

    # Result
    result: Optional[str] = None
    payout: Optional[float] = None
    balance: Optional[str] = None

    # Extra
    message: Optional[str] = None
    raw: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TradeSummary:
    """Aggregate of all events for one trade round."""
    trade_id: str
    round_num: int
    pair: str
    direction: str
    expiry_sec: int
    amount: float

    signal_to_browser_ms: Optional[float] = None
    click_to_ui_ms: Optional[float] = None
    click_to_confirm_ms: Optional[float] = None
    total_settle_ms: Optional[float] = None

    result: Optional[str] = None
    payout: Optional[float] = None
    balance_after: Optional[str] = None

    events: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items()
             if k != "events" and v is not None}
        d["event_count"] = len(self.events)
        return d
