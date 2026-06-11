#!/usr/bin/env python3
"""Run execution probe against a mapped platform.

Usage:
    python scripts/run_probe.py --platform pocket_option --rounds 10 --dry-run
    python scripts/run_probe.py --platform pocket_option --rounds 50
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.probes.execution_probe import run_probe


def main():
    parser = argparse.ArgumentParser(description="Run BTC binary options execution probe")
    parser.add_argument("--platform", default="pocket_option")
    parser.add_argument("--rounds", type=int, default=50)
    parser.add_argument("--pair", default="BTC/USD")
    parser.add_argument("--expiry", type=int, default=60)
    parser.add_argument("--amount", type=float, default=1.0)
    parser.add_argument("--mode", default="alternate",
                        choices=["alternate", "random", "call_only", "put_only"])
    parser.add_argument("--delay", type=float, default=5.0)
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--dry-run", action="store_true")

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
    print(f"Data saved to: {path}")


if __name__ == "__main__":
    main()
