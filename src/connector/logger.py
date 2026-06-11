"""Comprehensive trade logger with test/live mode separation.

Two modes:
  - test  → data/test/  (demo runs, strategy backtesting, dry runs)
  - live  → data/live/  (real-money execution)

Each session gets a timestamped directory with:
  - events.jsonl   (one TradeEvent per line)
  - summary.csv     (one TradeSummary per round)
  - session.json    (session metadata)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

from src.connector.events import TradeEvent, TradeSummary


LogMode = Literal["test", "live"]

DATA_ROOT = Path(__file__).parent.parent.parent / "data"


class TradeLogger:
    """Per-session structured logger with mode separation."""

    def __init__(self, mode: LogMode = "test", label: str = ""):
        self.mode = mode
        self.label = label
        self.session_dir = self._make_session_dir()
        self._events_path = self.session_dir / "events.jsonl"
        self._summary_path = self.session_dir / "summary.csv"
        self._session_path = self.session_dir / "session.json"
        self._events_file = None
        self._summary_file = None
        self._round = 0
        self._events: list[TradeEvent] = []
        self._summaries: list[TradeSummary] = []

        self._open_files()
        self._write_session_meta()

    # ── Setup ────────────────────────────────────────────────────────────

    def _make_session_dir(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"{self.label}_{ts}" if self.label else ts
        d = DATA_ROOT / self.mode / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _open_files(self):
        self._events_file = open(self._events_path, "w", encoding="utf-8")
        self._summary_file = None  # written at end

    def _write_session_meta(self):
        meta = {
            "mode": self.mode,
            "label": self.label,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "session_dir": str(self.session_dir),
        }
        self._session_path.write_text(json.dumps(meta, indent=2))

    # ── Public API ──────────────────────────────────────────────────────

    def log(self, event: TradeEvent):
        """Record a single lifecycle event."""
        event.mode = self.mode  # tag with mode for later filtering
        self._events.append(event)
        self._events_file.write(json.dumps(event.to_dict(), default=str) + "\n")
        self._events_file.flush()

    def log_summary(self, summary: TradeSummary):
        """Record a trade round summary."""
        self._summaries.append(summary)

    def next_round(self) -> int:
        self._round += 1
        return self._round

    @property
    def round_num(self) -> int:
        return self._round

    @property
    def path(self) -> Path:
        return self.session_dir

    # ── Finalize ────────────────────────────────────────────────────────

    def close(self):
        """Write summary CSV and close files."""
        self._write_summary_csv()
        if self._events_file:
            self._events_file.close()

        # Update session meta
        meta = json.loads(self._session_path.read_text())
        meta["ended_at"] = datetime.now(timezone.utc).isoformat()
        meta["total_rounds"] = self._round
        meta["total_events"] = len(self._events)
        self._session_path.write_text(json.dumps(meta, indent=2))

    def _write_summary_csv(self):
        if not self._summaries:
            return
        with open(self._summary_path, "w", encoding="utf-8") as f:
            keys = [
                "trade_id", "round_num", "pair", "direction", "expiry_sec",
                "amount", "signal_to_browser_ms", "click_to_ui_ms",
                "click_to_confirm_ms", "total_settle_ms", "result",
                "payout", "balance_after", "event_count",
            ]
            f.write(",".join(keys) + "\n")
            for s in self._summaries:
                d = s.to_dict()
                f.write(",".join(str(d.get(k, "")) for k in keys) + "\n")


# ── Convenience ───────────────────────────────────────────────────────────

def make_event(
    logger: TradeLogger,
    kind,
    trade_id: str = "",
    **kwargs,
) -> TradeEvent:
    """Create and log an event in one call."""
    evt = TradeEvent(trade_id=trade_id, kind=kind, **kwargs)
    logger.log(evt)
    return evt
