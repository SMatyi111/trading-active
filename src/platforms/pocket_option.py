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

SELECTORS = {
    "pair_selector_wrapper": ".currencies-block",
    "current_pair": ".current-symbol",
    "asset_dropdown_modal": ".drop-down-modal--quotes-list",
    "asset_list_items": ".alist__item",
    "asset_label": ".alist__label",
    "asset_payout": ".alist__payout",
    "buy_button": ".btn.btn-call",
    "sell_button": ".btn.btn-put",
    "amount_input": ".block--bet-amount input",
    "payout_block": ".block--payout",
    "expiry_val": ".value__val",
    "expiry_control": ".control__value.value--several-items",
    "expiry_dropdown_modal": ".expiration-inputs-list-m",
    "expiry_items": ".dops__timeframes-item",
    "mode_toggle": ".control-buttons__wrapper a",
    "deals_list": ".deals-list",
    "opened_tab": "a.flex-centered:first-child",
    "closed_tab": "a.flex-centered:nth-child(2)",
    "balance_area": ".right-block",
    "tutorial_overlay": ".tutorial-v1",
    "inactive_overlay": ".asset-inactive",
}


class PocketOption(BasePlatform):

    def login(self, browser: Browser, email: str = "", password: str = ""):
        print("[PocketOption] Opening demo...")
        if not email:
            browser.navigate(POCKET_DEMO)
            time.sleep(4)
            browser.evaluate("""
                const tut = document.querySelector('.tutorial-v1');
                if (tut) tut.remove();
            """)
            time.sleep(1)
            gone = browser.evaluate(
                "return document.querySelector('.tutorial-v1') ? 'still there' : 'gone';"
            )
            print(f"[PocketOption] Tutorial: {gone}")
        else:
            browser.navigate(POCKET_URL)
            time.sleep(3)
            browser.evaluate("document.querySelector('a[href*=\"login\"]')?.click()")
            time.sleep(2)
        print("[PocketOption] Ready")

    def select_pair(self, browser: Browser, pair: str = "Bitcoin OTC"):
        print(f"[PocketOption] Selecting pair: {pair}")
        current = browser.evaluate(
            "return document.querySelector('.current-symbol')?.innerText?.trim() || '';"
        )
        if current == pair:
            print(f"[PocketOption] Already on {pair}")
            return
        browser.evaluate("document.querySelector('.pair-number-wrap')?.click()")
        time.sleep(1.5)
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
        preset_map = {30: "+S30", 60: "+M1", 120: "+M2", 180: "+M3", 300: "+M5"}
        preset = preset_map.get(seconds, "+M1")
        print(f"[PocketOption] Setting expiry: {seconds}s -> {preset}")

        current_val = browser.evaluate(
            "return document.querySelector('.value__val')?.innerText?.trim() || '';"
        )
        if current_val.startswith("00:"):
            print("[PocketOption] Switching to time-based mode...")
            browser.evaluate("""
                const btn = document.querySelector('.control-buttons__wrapper a');
                if (btn) btn.click();
            """)
            time.sleep(0.8)

        browser.evaluate(
            "document.querySelector('.control__value.value--several-items')?.click()"
        )
        time.sleep(0.5)

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
        time.sleep(0.3)

        expiry = browser.evaluate(
            "return document.querySelector('.value__val')?.innerText?.trim() || '?';"
        )
        print(f"[PocketOption] Expiry set to: {expiry}")

    def set_amount(self, browser: Browser, amount: float = 10.0):
        """Set trade amount via input field."""
        print(f"[PocketOption] Setting amount: ${amount}")
        # Click the input, select all, type new value, then blur
        browser.evaluate(f"""
            const input = document.querySelector('.block--bet-amount input');
            if (!input) return 'no input';
            input.focus();
            input.select();
            input.value = '{amount}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            input.blur();
            return 'ok';
        """)
        time.sleep(0.3)

    def place_trade(self, browser: Browser, direction: str) -> float:
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

    def wait_for_result(self, browser: Browser, timeout_ms: int = 90000) -> dict:
        """3-phase settlement detection: appear -> countdown -> closed tab."""
        print("[PocketOption] Waiting for settlement...")
        start = time.monotonic()
        poll_interval = 1.0

        # Phase 1: Wait for trade to appear
        initial = browser.evaluate(
            "return document.querySelector('.deals-list')?.innerText?.trim() || '';"
        )
        trade_appeared = False
        for _ in range(30):
            current = browser.evaluate(
                "return document.querySelector('.deals-list')?.innerText?.trim() || '';"
            )
            if current != initial and "No opened trades" not in current:
                trade_appeared = True
                print(f"[PocketOption] Trade visible at {(time.monotonic()-start)*1000:.0f}ms")
                break
            time.sleep(poll_interval)

        if not trade_appeared:
            print("[PocketOption] Trade never appeared")
            return {"result": "TIMEOUT_NO_TRADE", "delivery_ms": (time.monotonic()-start)*1000}

        # Phase 2: Wait for settlement
        for _ in range(int(timeout_ms / 1000)):
            current = browser.evaluate(
                "return document.querySelector('.deals-list')?.innerText?.trim() || '';"
            )
            if "No opened trades" in current:
                settle_elapsed = (time.monotonic() - start) * 1000
                print(f"[PocketOption] Settled at {settle_elapsed:.0f}ms")

                # Phase 3: Read closed tab, then switch back to Opened
                time.sleep(0.5)
                browser.evaluate("""
                    const links = document.querySelectorAll('a.flex-centered');
                    for (const link of links) {
                        if (link.innerText.trim() === 'Closed') {
                            link.click(); break;
                        }
                    }
                """)
                time.sleep(0.3)
                closed = browser.evaluate(
                    "return document.querySelector('.deals-list')?.innerText?.trim() || '';"
                )
                print(f"[PocketOption] Closed: {repr(closed[:100])}")

                # Switch back to Opened tab for next round
                browser.evaluate("""
                    const links = document.querySelectorAll('a.flex-centered');
                    for (const link of links) {
                        if (link.innerText.trim() === 'Opened') {
                            link.click(); break;
                        }
                    }
                """)
                time.sleep(0.3)

                return {"result": closed.strip(), "delivery_ms": settle_elapsed}
            time.sleep(poll_interval)

        return {"result": "TIMEOUT", "delivery_ms": timeout_ms}

    def get_balance(self, browser: Browser) -> str:
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
        pmap = PlatformMap(
            platform_name="pocket_option",
            url=POCKET_DEMO,
            login_url=POCKET_URL,
            mapped_at=datetime.now(timezone.utc).isoformat(),
        )
        pmap.pair_selector = UIElement("pair_selector", SELECTORS["pair_selector_wrapper"], "div")
        pmap.btc_pair_button = UIElement("btc_pair", ".alist__label:text='Bitcoin OTC'", "span")
        pmap.buy_call_button = UIElement("buy_call", SELECTORS["buy_button"], "a")
        pmap.buy_put_button = UIElement("buy_put", SELECTORS["sell_button"], "a")
        pmap.amount_input = UIElement("amount", SELECTORS["amount_input"], "input")
        pmap.expiry_selector = UIElement("expiry", SELECTORS["expiry_control"], "div")
        pmap.expiry_60s_button = UIElement("expiry_M1", ".dops__timeframes-item:text='+M1'", "div")
        pmap.payout_display = UIElement("payout", SELECTORS["payout_block"], "div")
        pmap.trade_ticket_panel = UIElement("deals", SELECTORS["deals_list"], "div")
        pmap.current_pair_label = UIElement("pair", SELECTORS["current_pair"], "span")
        pmap.balance_label = UIElement("balance", SELECTORS["balance_area"], "div")
        pmap.extra_elements = {
            "tutorial": SELECTORS["tutorial_overlay"],
            "inactive_overlay": SELECTORS["inactive_overlay"],
            "mode_toggle": SELECTORS["mode_toggle"],
            "closed_tab": SELECTORS["closed_tab"],
        }
        print("[PocketOption] Map built")
        return pmap
