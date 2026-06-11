"""Configuration — loaded from env or defaults."""
import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Browser
BROWSER_DEBUG_URL = os.environ.get("BU_CDP_URL", "http://127.0.0.1:9222")

# Platforms
PLATFORM_URLS = {
    "pocket_option": "https://pocketoption.com",
    "olymp_trade": "https://olymptrade.com",
    "close_option": "https://closeoption.com",
    "iq_option": "https://iqoption.com",
    "capitalcore": "https://capitalcore.com",
    "quotex": "https://quotex.io",
}

# Probe defaults
DEFAULT_ROUNDS = 50
DEFAULT_EXPIRY = 60  # seconds
DEFAULT_PAIR = "BTC/USD"

# Logging
LOG_LEVEL = os.environ.get("PROBE_LOG_LEVEL", "INFO")
