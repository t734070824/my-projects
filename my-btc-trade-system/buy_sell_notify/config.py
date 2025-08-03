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

# --- Data Fetching Settings ---
# Number of historical candles to fetch for analysis
HISTORY_LIMIT = 400
