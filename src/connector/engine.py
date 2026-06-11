"""Trade Engine — the reusable connector for binary options execution.

Usage (from any project):
    from src.connector.engine import TradeEngine, TradeConfig

    engine = TradeEngine(TradeConfig(mode="test"))
    engine.start()

    result = engine.open_position(
        pair="Bitcoin OTC",
        direction="CALL",
        amount=10.0,
        expiry_sec=60,
    )
    print(f"Result: {result.result}, Payout: {result.payout}")

    engine.stop()
"""

import time
import uuid
from dataclasses import dataclass
from typing import Optional, Literal

from src.utils.browser import Browser
from src.connector.events import TradeEvent, TradeSummary
from src.connector.logger import TradeLogger, make_event
from src.platforms.pocket_option import PocketOption


@dataclass
class TradeConfig:
    """Configuration for the trade engine."""
    mode: Literal["test", "live"] = "test"
    platform: str = "pocket_option"
    cdp_url: str = "http://127.0.0.1:9222"
    session_label: str = ""
    default_pair: str = "Bitcoin OTC"
    default_expiry: int = 60
    default_amount: float = 10.0


class TradeEngine:
    """Reusable connector. Import this from any project to execute
    binary options trades with full event logging."""

    def __init__(self, config: TradeConfig = None):
        self.config = config or TradeConfig()
        self.logger = TradeLogger(mode=self.config.mode, label=self.config.session_label)
        self.browser: Optional[Browser] = None
        self.platform: Optional[PocketOption] = None
        self._ready = False
        self._session_id = uuid.uuid4().hex[:8]

        make_event(self.logger, "SESSION_START",
                   trade_id=self._session_id,
                   message=f"Engine init, mode={self.config.mode}")

    # ── Lifecycle ───────────────────────────────────────────────────

    def start(self) -> bool:
        """Connect browser, login, and prepare platform. Returns True if ready."""
        self.logger.log(TradeEvent(
            trade_id=self._session_id, kind="BROWSER_READY",
            message=f"Connecting to {self.config.cdp_url}"
        ))

        t0 = time.monotonic()
        self.browser = Browser(self.config.cdp_url)
        self.platform = PocketOption()

        self.platform.login(self.browser)
        self.platform.select_pair(self.browser, self.config.default_pair)
        self.platform.set_expiry(self.browser, self.config.default_expiry)
        self.platform.set_amount(self.browser, self.config.default_amount)

        self._ready = True
        elapsed = (time.monotonic() - t0) * 1000
        self.logger.log(TradeEvent(
            trade_id=self._session_id, kind="BROWSER_READY",
            message=f"Platform ready, setup took {elapsed:.0f}ms"
        ))
        return True

    def stop(self):
        """Close logger and clean up."""
        self.logger.log(TradeEvent(
            trade_id=self._session_id, kind="SESSION_END",
            message=f"Session complete, {self.logger.round_num} rounds"
        ))
        self.logger.close()
        self._ready = False

    # ── Core API ────────────────────────────────────────────────────

    def open_position(
        self,
        pair: str = None,
        direction: str = "CALL",
        amount: float = None,
        expiry_sec: int = None,
        signal_id: str = "",  # external signal ID for correlation
    ) -> TradeSummary:
        """
        Place a trade and wait for settlement.

        Args:
            pair: Trading pair (default from config)
            direction: "CALL" or "PUT"
            amount: Trade amount in $
            expiry_sec: Expiry in seconds
            signal_id: Optional external signal reference

        Returns:
            TradeSummary with full timing breakdown and result
        """
        if not self._ready:
            raise RuntimeError("Engine not started. Call engine.start() first.")

        pair = pair or self.config.default_pair
        amount = amount or self.config.default_amount
        expiry_sec = expiry_sec or self.config.default_expiry
        direction = direction.upper()
        round_num = self.logger.next_round()

        trade_id = uuid.uuid4().hex[:12]
        t_trade_start = time.monotonic()

        # ── Event: Signal received ──
        make_event(self.logger, "SIGNAL_RECEIVED",
                   trade_id=trade_id, round_num=round_num,
                   pair=pair, direction=direction,
                   amount=amount, expiry_sec=expiry_sec,
                   message=f"Signal: {direction} {pair} ${amount} / {expiry_sec}s",
                   raw=signal_id)

        # ── Event: Trade click ──
        make_event(self.logger, "TRADE_CLICK_START",
                   trade_id=trade_id, round_num=round_num,
                   pair=pair, direction=direction,
                   message="Clicking button")

        click_start = time.monotonic()
        platform_click_time = self.platform.place_trade(self.browser, direction)
        click_end = time.monotonic()

        click_to_ui_ms = (click_end - click_start) * 1000
        signal_to_click_ms = (click_start - t_trade_start) * 1000

        make_event(self.logger, "TRADE_CLICK_UI",
                   trade_id=trade_id, round_num=round_num,
                   click_to_ui_ms=click_to_ui_ms,
                   elapsed_ms=signal_to_click_ms + click_to_ui_ms,
                   message=f"Button clicked, UI responded in {click_to_ui_ms:.0f}ms")

        # ── Event: Trade confirmed ──
        time.sleep(0.5)
        make_event(self.logger, "TRADE_CONFIRMED",
                   trade_id=trade_id, round_num=round_num,
                   elapsed_ms=(time.monotonic() - t_trade_start) * 1000,
                   message="Trade placed on platform")

        # ── Wait for settlement ──
        settle_timeout = expiry_sec * 1000 + 30000
        result = self.platform.wait_for_result(self.browser, timeout_ms=settle_timeout)

        settle_elapsed = (time.monotonic() - t_trade_start) * 1000

        # ── Parse result ──
        result_text = result.get("result", "?")
        parsed = self._parse_result(result_text, direction)

        make_event(self.logger, "TRADE_SETTLED",
                   trade_id=trade_id, round_num=round_num,
                   result=parsed["outcome"],
                   payout=parsed["payout"],
                   elapsed_ms=settle_elapsed,
                   message=f"{parsed['outcome']} payout=${parsed['payout']}")

        # ── Balance check ──
        balance = self.platform.get_balance(self.browser)
        make_event(self.logger, "BALANCE_CHECK",
                   trade_id=trade_id,
                   balance=balance,
                   message=f"Balance: {balance}")

        # ── Build summary ──
        trade_events = [
            e for e in self.logger._events
            if e.trade_id == trade_id
        ]
        summary = TradeSummary(
            trade_id=trade_id,
            round_num=round_num,
            pair=pair,
            direction=direction,
            expiry_sec=expiry_sec,
            amount=amount,
            signal_to_browser_ms=signal_to_click_ms,
            click_to_ui_ms=click_to_ui_ms,
            total_settle_ms=settle_elapsed,
            result=parsed["outcome"],
            payout=parsed["payout"],
            balance_after=balance,
            events=trade_events,
        )
        self.logger.log_summary(summary)
        return summary

    # ── Helpers ──────────────────────────────────────────────────────

    def _parse_result(self, raw: str, direction: str) -> dict:
        """Extract outcome and payout from raw deals-list text."""
        if not raw or raw == "TIMEOUT":
            return {"outcome": "TIMEOUT", "payout": 0}

        lines = raw.strip().split("\n")
        payout = 0.0
        outcome = "LOSS"

        for line in lines:
            line = line.strip()
            if line.startswith("+$"):
                try:
                    p = float(line.replace("+$", "").replace(",", ""))
                    if p > 0:
                        outcome = "WIN"
                        payout = p
                except ValueError:
                    pass
            elif line.startswith("$") and outcome == "LOSS":
                # Could be the stake returning $0 or partial
                pass

        return {"outcome": outcome, "payout": payout}
