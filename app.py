"""
Entry point.

- Downloads/caches data for a small ticker list.
- Registers PyLinkJS handlers that the frontend will call.
- Starts a simple web server that serves the frontend and routes JS↔Python.
"""

from backend.config import SERVER_PORT
from backend.data import download_data
from backend import handlers
from pylinkjs import PyLinkJS


def main():
    """Bootstrap the app: fetch data, register handlers, start the server."""
    print("Downloading stock data for all tickers...")
    download_data()
    print("Download complete.")

    # Register Python functions that can be invoked from the frontend via call_py(...)
    PyLinkJS.ready = handlers.ready
    PyLinkJS.get_plot_data = handlers.get_plot_data
    PyLinkJS.get_stat_value = handlers.get_stat_value

    print(f"Starting web server on port {SERVER_PORT}...")
    PyLinkJS.run_pylinkjs_app(
        default_html="frontend/stock_app.html",
        port=SERVER_PORT
    )


if __name__ == "__main__":
    main()
