"""
Configuration values.

- Ticker Download Config: TICKERS, DOWNLOAD_PERIOD, DOWNLOAD_INTERVAL, DATA_DIR
- SERVER_PORT
- Creates DATA_DIR to ensure it exists at import time 
"""

import os

# Ticker Data
TICKERS = ['AAPL', 'MSFT', 'IBM'] # Stock symbols
DOWNLOAD_PERIOD = "1y"    # lookback window before "now"
DOWNLOAD_INTERVAL = "1d"  # daily sampling
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Server
SERVER_PORT = int(os.environ.get("PORT", 8300))

# Ensure data directory exists at import time
os.makedirs(DATA_DIR, exist_ok=True)
