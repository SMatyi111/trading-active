"""Base platform interface for binary options brokers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UIElement:
    """Mapped UI element on the trading platform."""

    name: str  # logical name e.g. "buy_button_CALL"
    selector: str  # CSS selector
    element_type: str  # "button", "input", "label", "container"
    rect: dict | None = None
    visible: bool = True
    notes: str = ""


@dataclass
class PlatformMap:
    """Complete UI map of a trading platform."""

    platform_name: str
    url: str
    login_url: str = ""
    mapped_at: str = ""

    # Login
    login_email_input: Optional[UIElement] = None
    login_password_input: Optional[UIElement] = None
    login_submit_button: Optional[UIElement] = None

    # Pair / Asset selection
    pair_selector: Optional[UIElement] = None
    btc_pair_button: Optional[UIElement] = None
    asset_list_item: Optional[UIElement] = None  # generic list item

    # Trade execution
    buy_call_button: Optional[UIElement] = None
    buy_put_button: Optional[UIElement] = None
    amount_input: Optional[UIElement] = None
    expiry_selector: Optional[UIElement] = None
    expiry_60s_button: Optional[UIElement] = None
    payout_display: Optional[UIElement] = None

    # Status / Monitoring
    trade_confirmation_label: Optional[UIElement] = None
    trade_ticket_panel: Optional[UIElement] = None
    trade_result_label: Optional[UIElement] = None
    balance_label: Optional[UIElement] = None
    current_price_label: Optional[UIElement] = None
    current_pair_label: Optional[UIElement] = None
    countdown_timer: Optional[UIElement] = None

    # Demo toggle
    demo_account_toggle: Optional[UIElement] = None

    # Overflow — any extra mapped elements keyed by name
    extra_elements: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize map to JSON-serializable dict."""
        out = {
            "platform_name": self.platform_name,
            "url": self.url,
            "login_url": self.login_url,
            "mapped_at": self.mapped_at,
        }
        for fname in self.__dataclass_fields__:
            if fname in ("extra_elements", "platform_name", "url", "login_url", "mapped_at"):
                continue
            val = getattr(self, fname)
            if val is not None:
                out[fname] = {
                    "selector": val.selector,
                    "element_type": val.element_type,
                    "notes": val.notes,
                }
        if self.extra_elements:
            out["extra_elements"] = self.extra_elements
        return out


class BasePlatform(ABC):
    """Abstract platform — implement per-broker."""

    @abstractmethod
    def login(self, browser, email: str = "", password: str = ""):
        """Log into the platform (or use demo if credentials empty)."""
        ...

    @abstractmethod
    def select_pair(self, browser, pair: str = "BTC/USD"):
        """Select trading pair."""
        ...

    @abstractmethod
    def set_expiry(self, browser, seconds: int = 60):
        """Set expiry time."""
        ...

    @abstractmethod
    def set_amount(self, browser, amount: float = 1.0):
        """Set trade amount."""
        ...

    @abstractmethod
    def place_trade(self, browser, direction: str) -> float:
        """
        Click CALL or PUT, return entry timestamp (monotonic).
        Must capture: click_to_ui_response_ms, click_to_fill_ms.
        """
        ...

    @abstractmethod
    def wait_for_result(self, browser, timeout_ms: int = 90000):
        """Wait for trade result. Returns result dict."""
        ...

    @abstractmethod
    def map_ui(self, browser) -> PlatformMap:
        """Map all relevant UI elements."""
        ...
