"""
Configuration values.

These serve as a single source of truth so the rest of the codebase
doesn't hard‑code magic strings/paths. Values are intentionally small/simple.
"""

import os

# Ticker Data
TICKERS = ['AAPL', 'MSFT', 'IBM']
DOWNLOAD_PERIOD = "1y"    # lookback window before "now"
DOWNLOAD_INTERVAL = "1d"  # daily sampling
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Server
SERVER_PORT = int(os.environ.get("PORT", 8300))

# Ensure data directory exists at import time
os.makedirs(DATA_DIR, exist_ok=True)
