#!/usr/bin/env python3
"""Map a binary options platform's UI elements using browser-harness.

Usage:
    python scripts/map_platform.py --platform pocket_option
    python scripts/map_platform.py --platform pocket_option --output map.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser import Browser
from src.probes.execution_probe import get_platform


def main():
    parser = argparse.ArgumentParser(description="Map platform UI elements")
    parser.add_argument("--platform", required=True, help="Platform name (pocket_option, etc.)")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--screenshot", help="Save screenshot to this path")

    args = parser.parse_args()

    browser = Browser(args.cdp_url)
    platform = get_platform(args.platform)

    print(f"Mapping {args.platform}...")

    # Login (demo mode)
    platform.login(browser)

    # Map UI
    pmap = platform.map_ui(browser)

    # Save
    output = json.dumps(pmap.to_dict(), indent=2)
    if args.output:
        Path(args.output).write_text(output)
        print(f"Map saved to: {args.output}")
    else:
        print("\n" + output)

    if args.screenshot:
        browser.screenshot(args.screenshot)
        print(f"Screenshot saved to: {args.screenshot}")

    # Summary
    print(f"\nElements mapped: {len(pmap.extra_elements)} total")
    mapped = sum(1 for f in pmap.__dataclass_fields__
                 if f not in ("extra_elements", "platform_name", "url", "login_url", "mapped_at")
                 and getattr(pmap, f) is not None)
    print(f"Named elements identified: {mapped}")
    print(f"\nMissing key elements:")
    for name in ("buy_call_button", "buy_put_button", "expiry_60s_button",
                 "btc_pair_button", "amount_input", "balance_label"):
        if getattr(pmap, name) is None:
            print(f"  ✗ {name}")


if __name__ == "__main__":
    main()
