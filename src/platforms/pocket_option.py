"""Pocket Option platform mapper and executor -- live-mapped via browser-harness."""

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

# Confirmed live selectors (verified 2026-06-11 20:20 UTC+2)
SELECTORS = {
    # --- Navigation ---
    "start_one_click": "a[href*='try-demo']",
    "demo_url": POCKET_DEMO,

    # --- Pair/Asset Selection ---
    "pair_selector_wrapper": ".currencies-block",
    "current_pair": ".current-symbol",
    "asset_dropdown_modal": ".drop-down-modal--quotes-list",
    "asset_list_items": ".alist__item",
    "asset_label": ".alist__label",
    "asset_payout": ".alist__payout",
    "asset_active": ".alist__item--active",
    "asset_inactive": ".alist__item--no-active",
    "crypto_nav": ".assets-block__col-nav",

    # --- Trade Panel (right sidebar) ---
    "buy_button": ".btn.btn-call",
    "sell_button": ".btn.btn-put",
    "amount_input": ".block--bet-amount input",
    "payout_block": ".block--payout",
    "expiry_val": ".value__val",
    "expiry_control": ".control__value.value--several-items",
    "expiry_dropdown_modal": ".expiration-inputs-list-m",
    "expiry_items": ".dops__timeframes-item",
    "mode_toggle": ".control-buttons__wrapper a, .control__buttons a",

    # --- Trade Monitoring ---
    "deals_list": ".deals-list",
    "trade_confirmation": "[class*='trade'] [class*='notify']",

    # --- Account ---
    "balance_area": ".right-block",
    "demo_label": "[class*='demo']",

    # --- Overlays/Interference ---
    "tutorial_overlay": ".tutorial-v1",
    "tutorial_button": ".tutorial-v1 .js-change-slide",
    "inactive_overlay": ".asset-inactive",
}


class PocketOption(BasePlatform):
    """Pocket Option binary options -- live selectors mapped via browser-harness."""

    def login(self, browser: Browser, email: str = "", password: str = ""):
        """Navigate to demo trading interface."""
        print("[PocketOption] Opening demo trading...")

        if not email:
            browser.navigate(POCKET_DEMO)
            time.sleep(4)

            # Kill tutorial overlay permanently
            browser.evaluate("""
                const tut = document.querySelector('.tutorial-v1');
                if (tut) tut.remove();
            """)
            time.sleep(1)

            tutorial_gone = browser.evaluate(
                "return document.querySelector('.tutorial-v1') ? 'still there' : 'gone';"
            )
            print(f"[PocketOption] Tutorial: {tutorial_gone}")
        else:
            browser.navigate(POCKET_URL)
            time.sleep(3)
            browser.evaluate(
                "document.querySelector('a[href*=\"login\"]')?.click()"
            )
            time.sleep(2)
            print("[PocketOption] Login form opened -- fill credentials manually for now")

        print("[PocketOption] Demo ready")

    def select_pair(self, browser: Browser, pair: str = "Bitcoin OTC"):
        """Open asset list dropdown and click the target pair."""
        print(f"[PocketOption] Selecting pair: {pair}")

        # Skip if already on the right pair
        current = browser.evaluate(
            "return document.querySelector('.current-symbol')?.innerText?.trim() || '';"
        )
        if current == pair:
            print(f"[PocketOption] Already on {pair}, skipping")
            return

        # Open asset list
        browser.evaluate("document.querySelector('.pair-number-wrap')?.click()")
        time.sleep(1.5)

        # Find and click the target pair
        clicked = browser.evaluate(f"""
            const labels = document.querySelectorAll('.alist__label');
            for (const lbl of labels) {{
                if (lbl.innerText.trim() === '{pair}') {{
                    const item = lbl.closest('.alist__item');
                    if (item && !item.className.includes('no-active')) {{
                        item.scrollIntoView({{block: 'center'}});
                        item.click();
                        return 'ok';
                    }}
                    return 'inactive';
                }}
            }}
            return 'not found';
        """)
        print(f"[PocketOption] Pair select: {clicked}")

        time.sleep(0.5)
        browser.press_key("Escape")
        time.sleep(0.3)

    def set_expiry(self, browser: Browser, seconds: int = 60):
        """Set trade expiry. Switches from quick (5s) to time-based mode if needed."""
        preset_map = {
            30: "+S30", 60: "+M1", 120: "+M2", 180: "+M3", 300: "+M5",
        }
        preset = preset_map.get(seconds, "+M1")
        print(f"[PocketOption] Setting expiry: {seconds}s -> {preset}")

        # Check if in quick mode (countdown display like "00:00:05")
        current_val = browser.evaluate(
            "return document.querySelector('.value__val')?.innerText?.trim() || '';"
        )
        is_quick = current_val.startswith("00:")

        if is_quick:
            print("[PocketOption] Quick mode detected, switching to time-based...")
            browser.evaluate("""
                const btn = document.querySelector('.control-buttons__wrapper a, .control__buttons a');
                if (btn) btn.click();
            """)
            time.sleep(0.5)

        # Open expiry picker
        browser.evaluate(
            "document.querySelector('.control__value.value--several-items')?.click()"
        )
        time.sleep(0.5)

        # Select the preset
        clicked = browser.evaluate(f"""
            const items = document.querySelectorAll('.dops__timeframes-item');
            for (const item of items) {{
                if (item.innerText.trim() === '{preset}') {{
                    item.click();
                    return 'ok';
                }}
            }}
            return 'not found';
        """)
        print(f"[PocketOption] Preset: {clicked}")

        time.sleep(0.3)
        browser.press_key("Escape")

        expiry = browser.evaluate(
            "return document.querySelector('.value__val')?.innerText?.trim() || '?';"
        )
        print(f"[PocketOption] Expiry set to: {expiry}")

    def set_amount(self, browser: Browser, amount: float = 10.0):
        """Set trade amount."""
        print(f"[PocketOption] Setting amount: ${amount}")
        browser.evaluate(f"""
            const input = document.querySelector('.block--bet-amount input');
            if (input) {{
                input.value = '{amount}';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)
        time.sleep(0.3)

    def place_trade(self, browser: Browser, direction: str) -> float:
        """Place a CALL or PUT trade. Returns monotonic entry timestamp."""
        direction = direction.upper()
        selector = ".btn.btn-call" if direction == "CALL" else ".btn.btn-put"
        print(f"[PocketOption] Placing {direction} trade...")

        result = browser.evaluate(f"""
            const btn = document.querySelector('{selector}');
            if (!btn) return 'button not found';
            const clickTime = performance.now();
            btn.click();
            return 'clicked:' + clickTime;
        """)

        print(f"[PocketOption] {direction} trade: {result}")
        return time.monotonic()

    def wait_for_result(self, browser: Browser, timeout_ms: int = 90000):
        """Wait for trade to expire. Returns trade outcome text."""
        print(f"[PocketOption] Waiting for result (timeout: {timeout_ms}ms)...")
        start = time.monotonic()
        poll_interval = 1.0

        while (time.monotonic() - start) * 1000 < timeout_ms:
            deals = browser.evaluate("""
                const list = document.querySelector('.deals-list');
                return list ? list.innerText.substring(0, 300) : '';
            """)
            # Check if we have actual trade entries (not just "No opened trades")
            if deals and "No opened trades" not in deals and len(deals) > 40:
                elapsed = (time.monotonic() - start) * 1000
                return {"result": deals.strip(), "delivery_ms": elapsed}
            time.sleep(poll_interval)

        return {"result": "TIMEOUT", "delivery_ms": timeout_ms}

    def get_balance(self, browser: Browser) -> str:
        """Get current demo balance."""
        return browser.evaluate("""
            const el = document.querySelector('.right-block');
            if (el) {
                const text = el.innerText;
                const match = text.match(/\\$[\\d,]+\\.?\\d*/);
                return match ? match[0] : text.substring(0, 50);
            }
            return '?';
        """)

    def map_ui(self, browser: Browser) -> PlatformMap:
        """Build PlatformMap from confirmed live selectors."""
        pmap = PlatformMap(
            platform_name="pocket_option",
            url=POCKET_DEMO,
            login_url=POCKET_URL,
            mapped_at=datetime.now(timezone.utc).isoformat(),
        )

        pmap.pair_selector = UIElement(
            "pair_selector", SELECTORS["pair_selector_wrapper"], "div",
            notes="Click to open asset list modal"
        )
        pmap.btc_pair_button = UIElement(
            "btc_pair", ".alist__label:text='Bitcoin OTC'", "span",
            notes="Bitcoin OTC in the asset dropdown -- highest payout (92%)"
        )
        pmap.asset_list_item = UIElement(
            "asset_list", SELECTORS["asset_list_items"], "div",
            notes="Each .alist__item in the dropdown modal"
        )
        pmap.buy_call_button = UIElement(
            "buy_call", SELECTORS["buy_button"], "a",
            notes="Green BUY/CALL button, rect (682,272) 140x48"
        )
        pmap.buy_put_button = UIElement(
            "buy_put", SELECTORS["sell_button"], "a",
            notes="Red SELL/PUT button, rect (682,328) 140x48"
        )
        pmap.amount_input = UIElement(
            "amount", SELECTORS["amount_input"], "input",
            notes="Trade amount input in .block--bet-amount"
        )
        pmap.expiry_selector = UIElement(
            "expiry_control", SELECTORS["expiry_control"], "div",
            notes="Click to open expiry picker modal"
        )
        pmap.expiry_60s_button = UIElement(
            "expiry_M1", ".dops__timeframes-item:text='+M1'", "div",
            notes="1-minute expiry preset (60 seconds)"
        )
        pmap.payout_display = UIElement(
            "payout", SELECTORS["payout_block"], "div",
            notes="Shows payout % and dollar amount"
        )
        pmap.trade_ticket_panel = UIElement(
            "deals", SELECTORS["deals_list"], "div",
            notes="Opened/closed trades list"
        )
        pmap.current_pair_label = UIElement(
            "current_pair", SELECTORS["current_pair"], "span",
            notes="Currently selected trading pair"
        )
        pmap.balance_label = UIElement(
            "balance", SELECTORS["balance_area"], "div",
            notes="Header balance -- parse with regex"
        )
        pmap.extra_elements = {
            "tutorial": SELECTORS["tutorial_overlay"],
            "tutorial_nav": SELECTORS["tutorial_button"],
            "inactive_overlay": SELECTORS["inactive_overlay"],
            "mode_toggle": SELECTORS["mode_toggle"],
        }

        print(f"[PocketOption] Map built -- {len(pmap.__dict__)} elements mapped")
        return pmap
