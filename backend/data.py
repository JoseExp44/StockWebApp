"""
Data access layer.

- download_data: fetch and cache CSVs per ticker (auto-adjusted prices).
- load_data: load a single ticker's CSV into a DataFrame.
- filter_by_date: return a slice of rows within [start, end] inclusive.
"""

import os
import pandas as pd
import yfinance as yf
from .config import TICKERS, DATA_DIR, DOWNLOAD_PERIOD, DOWNLOAD_INTERVAL


def download_data():
    """
    Download historical data for each configured ticker and cache to CSV.

    Notes:
        - Skips tickers that return an empty DataFrame.
        - Uses yfinance auto_adjust=True for adjusted prices.
        - Keeps errors non-fatal so one bad ticker doesn't stop the rest.
    """
    for ticker in TICKERS:
        try:
            df = yf.download(
                ticker,
                period=DOWNLOAD_PERIOD,
                interval=DOWNLOAD_INTERVAL,
                auto_adjust=True,
                progress=False
            )
            if df.empty:
                print(f"Warning: no data for {ticker}, skipping.")
                continue

            # Persist for later reads to avoid repeated API calls
            df.reset_index(inplace=True)  # ensure 'Date' is a column
            csv_path = os.path.join(DATA_DIR, f"{ticker}.csv")
            df.to_csv(csv_path, index=False)
        except Exception as e:
            print(f"Error downloading {ticker}: {e}")


def load_data(ticker):
    """
    Load cached CSV for a ticker.

    Args:
        ticker: Ticker symbol (e.g., 'AAPL').

    Returns:
        DataFrame with at least a 'Date' column (datetime) if the file exists,
        or an empty DataFrame otherwise.
    """
    csv_path = os.path.join(DATA_DIR, f"{ticker}.csv")
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    df = pd.read_csv(csv_path, parse_dates=["Date"])
    return df


def filter_by_date(df, start, end):
    """
    Return rows with Date between start and end (inclusive).

    Args:
        df: DataFrame containing a 'Date' column.
        start: ISO date string 'YYYY-MM-DD'.
        end: ISO date string 'YYYY-MM-DD'.

    Returns:
        A DataFrame slice within the requested date range.
        If input is empty or lacks 'Date', returns an empty DataFrame.
    """
    if "Date" not in df or df.empty:
        return pd.DataFrame()
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    mask = (df["Date"] >= pd.to_datetime(start)) & (df["Date"] <= pd.to_datetime(end))
    return df.loc[mask]
