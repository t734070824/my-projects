# buy_sell_notify/config.py

# --- Binance API Keys ---
# IMPORTANT: Replace with your actual API Key and Secret Key
# Note: This is for the Futures account.
API_KEY = "oyV222IQtpVHqYLIWhIhgITl9R0f5c9lHK3pzrzogsJGCWBxObUSBhOKLGH1wq79"
SECRET_KEY = "Ep9pRR8nahbFsTlCJllE8SD981CWygEcFhJ38kSWzvwKIpAXhYl85m4qC3fxKHkc"

# --- Proxy Settings ---
# If you don't need a proxy, set it to None.
# Example: PROXY = None
PROXY = 'http://127.0.0.1:10809'

# --- Analysis Settings ---
# List of symbols to analyze
SYMBOLS_TO_ANALYZE = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

# --- Scheduler Settings ---
# Time to run the analysis every hour. Use ":01" for the 1st minute of the hour.
RUN_AT_MINUTE = ":01"

# --- Monitoring Settings ---
# Interval in seconds for the independent position monitor to check for updates.
MONITOR_INTERVAL_SECONDS = 15

# --- Data Fetching Settings ---
# Number of historical candles to fetch for analysis
HISTORY_LIMIT = 400

# --- Indicator Settings ---
# ATR (Average True Range) settings.
# You can define specific timeframes and lengths for each symbol.
# A "DEFAULT" key is required as a fallback for symbols not explicitly listed.
ATR_CONFIG = {
    "DEFAULT": {"timeframe": "1d", "length": 14},
    "BTC/USDT": {"timeframe": "1d", "length": 14},
    "ETH/USDT": {"timeframe": "4h", "length": 20},
    # You can add other symbols here, e.g.:
        "SOL/USDT": {"timeframe": "4h", "length": 20},
}

# --- Virtual Trading Settings ---
# Settings for calculating virtual trade parameters.
VIRTUAL_TRADE_CONFIG = {
    "RISK_PER_TRADE_PERCENT": 2.0,  # Risk 1% of the available balance per trade
    "ATR_MULTIPLIER_FOR_SL": 2.0   # Stop loss will be set at 2 * ATR from the entry price
}

