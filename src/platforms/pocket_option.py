"""Pocket Option platform mapper and executor — live-mapped selectors."""

import sys
import time
from datetime import datetime, timezone

from src.utils.browser import Browser
from src.platforms.base import (
    BasePlatform,
    PlatformMap,
    UIElement,
)


POCKET_URL = "https://pocketoption.com/en"
POCKET_DEMO = "https://pocketoption.com/en/cabinet/try-demo/"

# Live-mapped selectors (verified 2026-06-11)
SELECTORS = {
    "start_one_click": "a[href*='try-demo']",
    "pair_selector": ".pair-number-wrap",
    "current_pair": ".current-symbol",
    "asset_dropdown": ".drop-down-modal--quotes-list",
    "crypto_category": ".assets-block__col-nav >> text=Cryptocurrencies",
    "btc_otc_item": ".alist__link (text contains Bitcoin OTC)",
    "buy_button": ".btn.btn-call",
    "sell_button": ".btn.btn-put",
    "amount_input": "input[type='text']",  # in trade panel
    "time_display": ".control__value.value--several-items",
    "expiry_dropdown": ".expiration-inputs-list-m",
    "deals_list": ".deals-list",
    "balance": "[class*='balance']",
}


class PocketOption(BasePlatform):
    """Pocket Option binary options — live selectors mapped via browser-harness."""

    def login(self, browser: Browser, email: str = "", password: str = ""):
        """Log in via 'Start in one click' demo flow."""
        print("[PocketOption] Navigating to homepage...")
        browser.navigate(POCKET_URL)
        time.sleep(3)

        if email and password:
            print("[PocketOption] Credentials provided — attempting login...")
            browser.evaluate(
                "document.querySelector('a[href*=\"login\"]')?.click()"
            )
            time.sleep(2)
            # TODO: fill credentials
        else:
            print("[PocketOption] Clicking 'Start in one click'...")
            browser.evaluate(
                'Array.from(document.querySelectorAll("a")).find(a=>a.innerText.includes("Start in one click"))?.click()'
            )
            time.sleep(5)

        # Dismiss tutorial with Escape + remove overlays
        browser.evaluate("""
            document.querySelectorAll('[class*="tour"],[class*="overlay"],[class*="modal"]').forEach(el => {
                if (el.offsetParent) el.style.display = 'none';
            });
        """)
        time.sleep(1)
        print("[PocketOption] Demo ready")

    def select_pair(self, browser: Browser, pair: str = "Bitcoin OTC"):
        """Open asset list and select pair."""
        print(f"[PocketOption] Selecting pair: {pair}")

        # Click pair selector to open dropdown
        browser.evaluate("document.querySelector('.pair-number-wrap')?.click()")
        time.sleep(2)

        # Click Cryptocurrencies category
        browser.evaluate("""
            const nav = document.querySelector('.assets-block__col-nav');
            if (nav) {
                Array.from(nav.querySelectorAll('*')).find(el =>
                    el.innerText?.trim() === 'Cryptocurrencies'
                )?.click();
            }
        """)
        time.sleep(1.5)

        # Click the pair in the list
        browser.evaluate(f"""
            const dropdown = document.querySelector('.drop-down-modal--quotes-list');
            if (dropdown) {{
                const items = dropdown.querySelectorAll('.alist__link');
                for (const item of items) {{
                    if (item.innerText?.includes('{pair}')) {{
                        item.click();
                        break;
                    }}
                }}
            }}
        """)
        time.sleep(1.5)
        print(f"[PocketOption] Pair selected")

    def set_expiry(self, browser: Browser, seconds: int = 60):
        """Set expiry — 60 seconds = M1 in the preset list."""
        print(f"[PocketOption] Setting expiry: {seconds}s")

        # Click time value to open dropdown
        browser.evaluate(
            "document.querySelector('.control__value.value--several-items')?.click()"
        )
        time.sleep(0.4)

        # Click M1 (1 minute = 60 seconds)
        browser.evaluate("""
            const dd = document.querySelector('.expiration-inputs-list-m');
            if (dd) {
                const items = dd.querySelectorAll('*');
                for (const item of items) {
                    if (item.innerText?.trim() === 'M1') {
                        item.click();
                        break;
                    }
                }
            }
        """)
        time.sleep(1)
        print(f"[PocketOption] Expiry set")

    def set_amount(self, browser: Browser, amount: float = 10.0):
        """Set trade amount via input field."""
        print(f"[PocketOption] Setting amount: ${amount}")
        browser.evaluate(f"""
            const input = document.querySelector('.block__control.control input[type="text"]');
            if (input) {{
                input.value = '{amount}';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)
        time.sleep(0.5)

    def place_trade(self, browser: Browser, direction: str) -> float:
        """Place a CALL or PUT trade. Returns monotonic entry timestamp."""
        direction = direction.upper()
        selector = ".btn.btn-call" if direction == "CALL" else ".btn.btn-put"
        label = "BUY" if direction == "CALL" else "SELL"
        print(f"[PocketOption] Placing {direction} trade...")

        click_start = time.monotonic()
        browser.evaluate(f"document.querySelector('{selector}')?.click()")
        click_end = time.monotonic()

        click_to_ui_ms = (click_end - click_start) * 1000
        print(f"[PocketOption] {label} clicked — {click_to_ui_ms:.0f}ms")
        return click_start

    def wait_for_result(self, browser: Browser, timeout_ms: int = 90000):
        """Wait for trade expiry and return result."""
        print(f"[PocketOption] Waiting for result...")
        start = time.monotonic()

        while time.monotonic() - start < timeout_ms / 1000:
            result = browser.evaluate("""
                const deals = document.querySelector('.deals-list');
                return deals ? deals.innerText.substring(0, 200) : '';
            """)
            if result and "No opened trades" not in result:
                elapsed = (time.monotonic() - start) * 1000
                return {"result": result.strip(), "delivery_ms": elapsed}
            time.sleep(1)

        return {"result": "TIMEOUT", "delivery_ms": timeout_ms}

    def map_ui(self, browser: Browser) -> PlatformMap:
        """Build PlatformMap from live DOM."""
        pmap = PlatformMap(
            platform_name="pocket_option",
            url=POCKET_DEMO,
            login_url=POCKET_URL,
            mapped_at=datetime.now(timezone.utc).isoformat(),
        )

        pmap.pair_selector = UIElement("pair_selector", SELECTORS["pair_selector"], "link")
        pmap.btc_pair_button = UIElement("btc_pair", SELECTORS["btc_otc_item"], "link")
        pmap.buy_call_button = UIElement("buy_call", SELECTORS["buy_button"], "a")
        pmap.buy_put_button = UIElement("buy_put", SELECTORS["sell_button"], "a")
        pmap.amount_input = UIElement("amount", SELECTORS["amount_input"], "input")
        pmap.expiry_selector = UIElement("expiry", SELECTORS["time_display"], "div")
        pmap.expiry_60s_button = UIElement("expiry_60s", "M1 in .expiration-inputs-list-m", "option")
        pmap.trade_ticket_panel = UIElement("trades", SELECTORS["deals_list"], "div")
        pmap.balance_label = UIElement("balance", SELECTORS["balance"], "div")
        pmap.current_price_label = UIElement("pair", SELECTORS["current_pair"], "div")
        pmap.countdown_timer = UIElement("countdown", SELECTORS["time_display"], "div")
        pmap.demo_account_toggle = UIElement("demo", SELECTORS["start_one_click"], "link")

        print(f"[PocketOption] Map built — call/put/expiry/pair/amount all mapped")
        return pmap
