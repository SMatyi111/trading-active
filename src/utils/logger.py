"""Data logging — CSV writer for probe results."""
import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import DATA_DIR


class ProbeLogger:
    """Logs execution probe data to CSV."""

    def __init__(self, platform: str, label: str = ""):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = f"{platform}_{label}_{ts}" if label else f"{platform}_{ts}"
        self.path = DATA_DIR / f"{slug}.csv"
        self.file = open(self.path, "w", newline="")
        self.writer = csv.writer(self.file)
        self.start_time = time.monotonic()
        self._headers_written = False

    def write_row(self, data: dict[str, Any]):
        if not self._headers_written:
            self.writer.writerow(data.keys())
            self._headers_written = True
        self.writer.writerow(data.values())
        self.file.flush()

    def close(self):
        self.file.close()

    def elapsed_sec(self) -> float:
        return time.monotonic() - self.start_time


class ExecutionRecord:
    """Single execution probe record."""

    def __init__(
        self,
        round_num: int,
        direction: str,  # "CALL" or "PUT"
        pair: str = "BTC/USD",
        expiry_sec: int = 60,
    ):
        self.round = round_num
        self.direction = direction
        self.pair = pair
        self.expiry = expiry_sec
        self.timestamp = datetime.now(timezone.utc).isoformat()

        # Timing (populated during probe)
        self.click_to_ui_response_ms: float | None = None
        self.click_to_fill_ms: float | None = None
        self.ticket_display_ms: float | None = None
        self.result_delivery_ms: float | None = None
        self.network_rtt_ms: float | None = None

        # Outcome
        self.result: str | None = None  # "WIN", "LOSS", "DRAW", "UNKNOWN"
        self.entry_price: str | None = None
        self.exit_price: str | None = None
        self.notes: str = ""

    def to_dict(self) -> dict:
        return {
            "round": self.round,
            "timestamp": self.timestamp,
            "pair": self.pair,
            "direction": self.direction,
            "expiry_sec": self.expiry,
            "click_to_ui_response_ms": self.click_to_ui_response_ms,
            "click_to_fill_ms": self.click_to_fill_ms,
            "ticket_display_ms": self.ticket_display_ms,
            "result_delivery_ms": self.result_delivery_ms,
            "network_rtt_ms": self.network_rtt_ms,
            "result": self.result,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "notes": self.notes,
        }
