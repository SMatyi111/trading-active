#!/usr/bin/env python3
"""Demo strategy using the TradeEngine connector.

Shows how ANY external project can import and use the connector.
Test mode: logs go to data/test/, no real money at risk.

Usage:
    python scripts/demo_strategy.py                     # 3 rounds, test mode
    python scripts/demo_strategy.py --rounds 10         # 10 rounds
    python scripts/demo_strategy.py --mode live         # LIVE trading!
    python scripts/demo_strategy.py --strategy trend    # switch strategy
"""

import argparse
import sys
import random
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connector.engine import TradeEngine, TradeConfig


# ── Example Strategies ──────────────────────────────────────────────────────
# These are pluggable — import your own from anywhere.

def strategy_random(round_num: int) -> dict:
    """Coin flip."""
    return {"direction": random.choice(["CALL", "PUT"])}


def strategy_alternate(round_num: int) -> dict:
    """Alternate CALL/PUT."""
    return {"direction": "CALL" if round_num % 2 == 1 else "PUT"}


def strategy_martingale(last_result: str = None, stake: float = 1.0) -> dict:
    """Double after loss, reset after win."""
    if last_result == "LOSS":
        return {"direction": "CALL", "amount": stake * 2, "signal_id": "martingale"}
    return {"direction": "CALL", "amount": 1.0, "signal_id": "martingale"}


STRATEGIES = {
    "random": strategy_random,
    "alternate": strategy_alternate,
}


def main():
    parser = argparse.ArgumentParser(description="Demo strategy using TradeEngine")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--mode", default="test", choices=["test", "live"])
    parser.add_argument("--strategy", default="random", choices=list(STRATEGIES))
    parser.add_argument("--pair", default="Bitcoin OTC")
    parser.add_argument("--expiry", type=int, default=60)
    parser.add_argument("--amount", type=float, default=1.0)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")

    args = parser.parse_args()

    # ── Build config ────────────────────────────────────────────────────
    config = TradeConfig(
        mode=args.mode,
        session_label=f"demo_{args.strategy}",
        default_pair=args.pair,
        default_expiry=args.expiry,
        default_amount=args.amount,
        cdp_url=args.cdp_url,
    )

    # ── Start engine ────────────────────────────────────────────────────
    engine = TradeEngine(config)
    strategy = STRATEGIES[args.strategy]

    print(f"\n{'='*60}")
    print(f"Demo Strategy: {args.strategy} | Mode: {args.mode}")
    print(f"Pair: {args.pair} | Expiry: {args.expiry}s | Amount: ${args.amount}")
    print(f"Logs: {engine.logger.session_dir}")
    print(f"{'='*60}\n")

    engine.start()

    # ── Run trades ──────────────────────────────────────────────────────
    results = []
    last_result = None

    for r in range(1, args.rounds + 1):
        # Strategy decides what to do
        decision = strategy(r)

        print(f"[Round {r}/{args.rounds}] ", end="", flush=True)

        # Execute via connector
        summary = engine.open_position(
            pair=args.pair,
            direction=decision.get("direction", "CALL"),
            amount=decision.get("amount", args.amount),
            expiry_sec=args.expiry,
            signal_id=decision.get("signal_id", args.strategy),
        )

        results.append(summary)
        last_result = summary.result

        # Live feedback
        icon = "WIN" if summary.result == "WIN" else "LOSS"
        print(f"{summary.direction} -> {icon} "
              f"(click:{summary.click_to_ui_ms:.0f}ms) "
              f"payout:${summary.payout}")

        if r < args.rounds:
            time.sleep(args.delay)

    # ── Summary ─────────────────────────────────────────────────────────
    wins = sum(1 for s in results if s.result == "WIN")
    losses = sum(1 for s in results if s.result == "LOSS")
    total_payout = sum(s.payout or 0 for s in results)
    total_wagered = args.amount * args.rounds
    net = total_payout - total_wagered

    print(f"\n{'='*60}")
    print(f"Results: {wins}W / {losses}L | Net: ${net:+.2f}")
    print(f"Avg click-to-UI: {sum(s.click_to_ui_ms or 0 for s in results)/len(results):.0f}ms")
    print(f"Logs: {engine.logger.session_dir}")
    print(f"  events.jsonl  — every lifecycle event")
    print(f"  summary.csv   — one row per trade")
    print(f"  session.json  — session metadata")
    print(f"{'='*60}")

    engine.stop()


if __name__ == "__main__":
    main()
