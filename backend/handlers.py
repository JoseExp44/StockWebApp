"""
PyLinkJS handlers: connect frontend requests to backend logic.

Flow:
  - ready: Called when the page loads. Computes defaults and calls JS initApp.
  - get_plot_data: Filters a ticker's data for the chosen range and returns X/Y series.
  - get_stat_value: Computes stats over the filtered Close prices and returns overlay lines.

Conventions:
  - Python → JS calls are made with jsc.eval_js_code("window.fnName(...)").
  - JS → Python calls use call_py('handler_name', ...).
  - Only Std Dev returns a per-stat error ('Only one price point') when n == 1.
"""

import os
import pandas as pd
import numpy as np
from .config import TICKERS, DATA_DIR
from .data import load_data, filter_by_date


def ready(jsc, origin, pathname, search, *args):
    """
    Initialize the frontend by sending available tickers and default dates.

    The default window is the latest 30 days within the union of all available
    ticker datasets (if any are present).

    JS callback:
        window.initApp(tickerList: string[], defaultStart: 'YYYY-MM-DD', defaultEnd: 'YYYY-MM-DD')
    """
    tickers = [t for t in TICKERS if os.path.exists(os.path.join(DATA_DIR, f"{t}.csv"))]

    # Build a single list of all dates across available tickers to choose defaults
    all_dates = []
    for t in tickers:
        df = load_data(t)
        if not df.empty:
            all_dates += list(df["Date"])

    default_start = default_end = None
    if all_dates:
        all_dates = pd.to_datetime(all_dates, errors='coerce').dropna()
        max_date = all_dates.max().date()
        default_end = max_date
        default_start = max(all_dates.min().date(), (default_end - pd.Timedelta(days=30)))

    # Dates to strings for the date inputs
    jsc.eval_js_code(
        f"window.initApp({tickers}, '{default_start}', '{default_end}');"
    )


def get_plot_data(jsc, ticker, start, end):
    """
    Provide X (date strings) and Y (Close prices) for the chart, or an error message.

    JS callback:
        window.plotStockData(x: string[], y: (number|null)[], errorMsg: string|null)
    """
    df = load_data(ticker)
    if df.empty:
        jsc.eval_js_code("window.plotStockData([], [], 'No data available');")
        return

    filtered = filter_by_date(df, start, end)
    if filtered.empty or "Close" not in filtered:
        jsc.eval_js_code("window.plotStockData([], [], 'No data for selected range');")
        return

    x = [pd.to_datetime(d).strftime("%m/%d/%Y") for d in filtered["Date"]]
    y = [float(c) if pd.notna(c) else None for c in filtered["Close"]]
    jsc.eval_js_code(f"window.plotStockData({x}, {y}, null);")


def get_stat_value(jsc, ticker, start, end, stat):
    """
    Compute a requested statistic and return overlay line(s) for the chart.

    Unified JS contract:
        window.drawStatLine(
            stat: 'mean'|'median'|'std',
            upper: number|null,
            lower: number|null,
            errorMsg: string|null
        )

    Behavior:
        - mean/median: return (upper=value, lower=null, error=null).
        - std:
            * if only one price point exists: (upper=null, lower=null, error='Only one price point')
            * else return (upper=mean+std, lower=mean-std, error=null)
        - If no valid numeric prices are available, return nulls (no per-stat errors for mean/median).
    """
    df = load_data(ticker)
    if df.empty:
        jsc.eval_js_code(f"window.drawStatLine('{stat}', null, null, null);")
        return

    filtered = filter_by_date(df, start, end)
    price = pd.to_numeric(filtered.get("Close", pd.Series(dtype=float)), errors="coerce") \
               .replace([np.inf, -np.inf], np.nan).dropna()

    if price.empty:
        jsc.eval_js_code(f"window.drawStatLine('{stat}', null, null, null);")
        return

    s = stat.lower()

    if s == "mean":
        val = float(price.mean())
        jsc.eval_js_code(f"window.drawStatLine('mean', {val}, null, null);")
        return

    if s == "median":
        val = float(price.median())
        jsc.eval_js_code(f"window.drawStatLine('median', {val}, null, null);")
        return

    if s == "std":
        n = len(price)
        if n == 1:
            jsc.eval_js_code("window.drawStatLine('std', null, null, 'Only one price point');")
            return
        mean = price.mean()
        std = price.std()  # sample std (ddof=1). For population, use price.std(ddof=0).
        upper = float(mean + std)
        lower = float(mean - std)
        jsc.eval_js_code(f"window.drawStatLine('std', {upper}, {lower}, null);")
        return

    # Unknown stat: silently no-op (could log if desired)
    jsc.eval_js_code(f"window.drawStatLine('{stat}', null, null, null);")
