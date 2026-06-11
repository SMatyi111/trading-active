"""Execution probe — measures click-to-fill timing on binary options platforms."""

import time
import random
from typing import Optional

from src.utils.browser import Browser
from src.utils.logger import ProbeLogger, ExecutionRecord
from src.platforms.base import BasePlatform
from src.platforms.pocket_option import PocketOption


PLATFORM_REGISTRY = {
    "pocket_option": PocketOption,
    # Add more as mapped:
    # "olymp_trade": OlympTrade,
    # "close_option": CloseOption,
}


def get_platform(name: str) -> BasePlatform:
    cls = PLATFORM_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown platform: {name}. Available: {list(PLATFORM_REGISTRY)}")
    return cls()


def run_probe(
    platform_name: str,
    rounds: int = 50,
    pair: str = "BTC/USD",
    expiry_sec: int = 60,
    amount: float = 1.0,
    direction_mode: str = "alternate",  # "alternate", "random", "call_only", "put_only"
    delay_between_s: float = 5.0,
    cdp_url: str = "http://127.0.0.1:9222",
    dry_run: bool = False,
) -> str:
    """
    Run execution probe against a platform.

    Returns path to the data CSV.
    """
    browser = Browser(cdp_url)
    platform = get_platform(platform_name)
    logger = ProbeLogger(platform_name, f"probe_{rounds}r")

    print(f"\n{'='*50}")
    print(f"BTC Binary Probe — {platform_name}")
    print(f"Rounds: {rounds} | Pair: {pair} | Expiry: {expiry_sec}s | Amount: ${amount}")
    print(f"Mode: {direction_mode} | {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
    print(f"{'='*50}\n")

    try:
        # Setup
        print("[1/4] Logging in...")
        platform.login(browser)

        print("[2/4] Setting up trading environment...")
        platform.select_pair(browser, pair)
        platform.set_expiry(browser, expiry_sec)
        platform.set_amount(browser, amount)
        time.sleep(2)

        # Main probe loop
        print(f"[3/4] Running {rounds} trade probes...\n")

        for r in range(1, rounds + 1):
            # Determine direction
            if direction_mode == "alternate":
                direction = "CALL" if r % 2 == 1 else "PUT"
            elif direction_mode == "random":
                direction = random.choice(["CALL", "PUT"])
            elif direction_mode in ("call_only", "put_only"):
                direction = direction_mode.replace("_only", "").upper()
            else:
                raise ValueError(f"Unknown direction_mode: {direction_mode}")

            record = ExecutionRecord(
                round_num=r,
                direction=direction,
                pair=pair,
                expiry_sec=expiry_sec,
            )

            print(f"Round {r}/{rounds} → {direction} | ", end="", flush=True)

            if dry_run:
                # Simulate timing
                record.click_to_ui_response_ms = random.uniform(80, 250)
                record.click_to_fill_ms = random.uniform(200, 600)
                record.ticket_display_ms = random.uniform(300, 800)
                record.network_rtt_ms = random.uniform(15, 60)
                record.result = random.choice(["WIN", "LOSS"])
                record.notes = "DRY_RUN"
                print(f"UI:{record.click_to_ui_response_ms:.0f}ms "
                      f"Fill:{record.click_to_fill_ms:.0f}ms "
                      f"→ {record.result}")
                time.sleep(0.1)
            else:
                # Real execution
                click_start = platform.place_trade(browser, direction)

                # Measure click→UI response (async, poll for confirmation)
                poll_start = time.monotonic()
                confirmation_seen = False
                ui_response_ms = None

                for _ in range(50):  # Poll for up to ~5 seconds
                    confirm = browser.page_info()
                    # TODO: check for confirmation element after mapping
                    if not confirmation_seen:
                        ui_response_ms = (time.monotonic() - click_start) * 1000
                        confirmation_seen = True
                    time.sleep(0.1)

                record.click_to_ui_response_ms = ui_response_ms

                # Wait for fill confirmation (ticket appears)
                result = platform.wait_for_result(browser, timeout_ms=expiry_sec * 1000 + 15000)
                record.result_delivery_ms = result.get("delivery_ms")
                record.result = result.get("result")
                record.notes = result.get("raw", "")

                print(f"UI:{ui_response_ms:.0f}ms " if ui_response_ms else "UI:? ",
                      f"Result:{record.result_delivery_ms:.0f}ms " if record.result_delivery_ms else "",
                      f"→ {record.result}")

            # Log
            logger.write_row(record.to_dict())

            # Delay between trades
            if r < rounds:
                time.sleep(delay_between_s)

        print(f"\n[4/4] Done! Data saved to: {logger.path}")

    except Exception as e:
        print(f"\n[ERROR] Probe failed: {e}")
        raise
    finally:
        logger.close()

    return str(logger.path)


# CLI entrypoint
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BTC Binary Options Execution Probe")
    parser.add_argument("--platform", default="pocket_option", help="Platform name")
    parser.add_argument("--rounds", type=int, default=50, help="Number of trade probes")
    parser.add_argument("--pair", default="BTC/USD")
    parser.add_argument("--expiry", type=int, default=60, help="Expiry in seconds")
    parser.add_argument("--amount", type=float, default=1.0, help="Trade amount")
    parser.add_argument("--mode", default="alternate",
                        choices=["alternate", "random", "call_only", "put_only"])
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Delay between trades (seconds)")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--dry-run", action="store_true",
                        help="Simulate without real trades")

    args = parser.parse_args()

    path = run_probe(
        platform_name=args.platform,
        rounds=args.rounds,
        pair=args.pair,
        expiry_sec=args.expiry,
        amount=args.amount,
        direction_mode=args.mode,
        delay_between_s=args.delay,
        cdp_url=args.cdp_url,
        dry_run=args.dry_run,
    )
    print(f"\nCSV: {path}")
