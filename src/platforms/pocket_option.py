"""Pocket Option platform mapper and executor."""

import time
import json
from datetime import datetime, timezone

from src.utils.browser import Browser
from src.platforms.base import (
    BasePlatform,
    PlatformMap,
    UIElement,
)


POCKET_URL = "https://pocketoption.com"
POCKET_LOGIN = "https://pocketoption.com/en/login"
POCKET_DEMO = "https://pocketoption.com/en/demo"


class PocketOption(BasePlatform):
    """Pocket Option binary options platform."""

    def login(self, browser: Browser, email: str = "", password: str = ""):
        """Log in — use demo mode if no credentials."""
        print("[PocketOption] Navigating to demo...")
        browser.navigate(POCKET_DEMO)
        time.sleep(3)

        # Try clicking "Try demo" or "Demo account" button
        page = browser.page_info()
        print(f"[PocketOption] Page: {page.get('title', 'unknown')}")

        # Pocket Option usually auto-loads demo without login
        # If a login form appears, we'd fill it here
        if email and password:
            print("[PocketOption] Credentials provided — attempting login...")
            browser.navigate(POCKET_LOGIN)
            time.sleep(2)
            # TODO: Map and fill login form dynamically
        else:
            print("[PocketOption] No credentials — relying on demo auto-login")

    def select_pair(self, browser: Browser, pair: str = "BTC/USD"):
        """Click to select BTC/USD pair."""
        # Pocket Option has an asset list; click the pair name
        print(f"[PocketOption] Selecting pair: {pair}")
        # Strategy: click the current pair display to open dropdown,
        # then find "BTC/USD" in the list
        # Selectors TBD during mapping
        try:
            # Click current pair button
            browser.click_selector("[data-testid='pair-selector']")
            time.sleep(0.5)
            # Click BTC/USD in list
            browser.click_text(pair)
            time.sleep(1)
        except Exception as e:
            print(f"[PocketOption] select_pair error (will be mapped): {e}")

    def set_expiry(self, browser: Browser, seconds: int = 60):
        """Set trade expiry."""
        print(f"[PocketOption] Setting expiry: {seconds}s")
        # Pocket Option has preset expiry buttons
        try:
            browser.click_text(f"{seconds}s")
        except Exception:
            browser.click_text(f"{seconds} sec")
        time.sleep(0.5)

    def set_amount(self, browser: Browser, amount: float = 1.0):
        """Set trade amount."""
        print(f"[PocketOption] Setting amount: ${amount}")
        try:
            # Click amount input, clear, type
            browser.click_selector("[data-testid='amount-input']")
            time.sleep(0.3)
            # Use JS to set value directly (more reliable)
            browser.evaluate(
                f"document.querySelector('[data-testid=\"amount-input\"] input').value = '{amount}'"
            )
            time.sleep(0.3)
        except Exception as e:
            print(f"[PocketOption] set_amount error (will be mapped): {e}")

    def place_trade(self, browser: Browser, direction: str) -> float:
        """
        Place a CALL or PUT trade.
        Returns monotonic entry timestamp.
        """
        direction = direction.upper()
        assert direction in ("CALL", "PUT"), f"Invalid direction: {direction}"

        print(f"[PocketOption] Placing {direction} trade...")

        click_start = time.monotonic()
        try:
            if direction == "CALL":
                browser.click_selector("[data-testid='buy-call']")
            else:
                browser.click_selector("[data-testid='buy-put']")
        except Exception:
            # Fallback: click by text
            color = "green" if direction == "CALL" else "red"
            browser.click_selector(f".{color}-button")
        click_end = time.monotonic()

        click_to_ui_ms = (click_end - click_start) * 1000
        print(f"[PocketOption] Click→UI response: {click_to_ui_ms:.1f}ms")

        return click_start

    def wait_for_result(self, browser: Browser, timeout_ms: int = 90000):
        """Wait for trade expiry and return result."""
        print(f"[PocketOption] Waiting for result ({timeout_ms/1000:.0f}s)...")

        start = time.monotonic()
        while time.monotonic() - start < timeout_ms / 1000:
            # Check for win/loss indicator
            result = browser.evaluate(
                "document.querySelector('.trade-result, .result-label, [data-result]')?.innerText || ''"
            )
            if result:
                elapsed = (time.monotonic() - start) * 1000
                return {
                    "result": result.strip(),
                    "delivery_ms": elapsed,
                    "raw": result,
                }
            time.sleep(0.5)

        return {"result": "TIMEOUT", "delivery_ms": timeout_ms, "raw": ""}

    def map_ui(self, browser: Browser) -> PlatformMap:
        """Map Pocket Option's UI elements and return PlatformMap."""
        print("[PocketOption] Mapping UI elements...")

        pmap = PlatformMap(
            platform_name="pocket_option",
            url=POCKET_URL,
            login_url=POCKET_LOGIN,
            mapped_at=datetime.now(timezone.utc).isoformat(),
        )

        # Dump all interactive elements
        all_els = browser.get_elements("button, a, input, select, [data-testid], [class*='btn']")
        print(f"[PocketOption] Found {len(all_els)} interactive elements")

        # Heuristic mapping — find elements by text/attributes
        for el in all_els:
            text = (el.get("text") or "").lower()
            css_class = (el.get("class") or "").lower()
            
            # Login elements
            if "email" in text or "e-mail" in text:
                pmap.login_email_input = UIElement("login_email", el.get("id",""), "input")
            if "password" in text:
                pmap.login_password_input = UIElement("login_password", el.get("id",""), "input")
            if "log in" in text or "sign in" in text:
                pmap.login_submit_button = UIElement("login_submit", el.get("id",""), "button")

            # Trade execution
            if text in ("call", "higher", "up", "buy") or "green" in css_class:
                pmap.buy_call_button = UIElement("buy_call", el.get("id",""), "button")
            if text in ("put", "lower", "down", "sell") or "red" in css_class:
                pmap.buy_put_button = UIElement("buy_put", el.get("id",""), "button")

            # Amount
            if "amount" in text or "stake" in text or "bet" in text:
                pmap.amount_input = UIElement("amount", el.get("id",""), "input")

            # Expiry
            if "60" in text and ("s" in text or "sec" in text):
                pmap.expiry_60s_button = UIElement("expiry_60s", el.get("id",""), "button")

            # Pair
            if "btc" in text or "bitcoin" in text:
                pmap.btc_pair_button = UIElement("btc_pair", el.get("id",""), "button")

            # Status
            if "balance" in text:
                pmap.balance_label = UIElement("balance", el.get("id",""), "label")
            if "demo" in text:
                pmap.demo_account_toggle = UIElement("demo_toggle", el.get("id",""), "button")

        # Store raw map for manual refinement
        pmap.extra_elements = [
            UIElement(
                name=f"el_{i}",
                selector=el.get("id","") or el.get("class",""),
                element_type=el.get("tag","?"),
                rect=el.get("rect"),
                visible=el.get("visible", True),
                notes=el.get("text","")[:100],
            )
            for i, el in enumerate(all_els)
        ]

        print(f"[PocketOption] Map complete — "
              f"call_btn={pmap.buy_call_button is not None}, "
              f"put_btn={pmap.buy_put_button is not None}, "
              f"expiry_60s={pmap.expiry_60s_button is not None}, "
              f"btc_pair={pmap.btc_pair_button is not None}")

        return pmap
