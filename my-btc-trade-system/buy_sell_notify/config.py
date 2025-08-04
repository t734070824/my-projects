# buy_sell_notify/config.py

# --- DingTalk Notifier Settings ---
# If your bot uses Keyword or IP security, just fill in the full webhook url.
# If your bot uses Signature security, fill in both the webhook base url and the secret.
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=f039bbc0bc60ddc6ef65edb56505af5aa16e057e1e295a6bfd8835f57858f82e"
DINGTALK_SECRET = "" # Leave this empty if you are not using Signature security

# --- Binance API Keys ---
# IMPORTANT: Replace with your actual API Key and Secret Key
# Note: This is for the Futures account.
API_KEY = "oyV222IQtpVHqYLIWhIhgITl9R0f5c9lHK3pzrzogsJGCWBxObUSBhOKLGH1wq79"
SECRET_KEY = "Ep9pRR8nahbFsTlCJllE8SD981CWygEcFhJ38kSWzvwKIpAXhYl85m4qC3fxKHkc"

# --- Proxy Settings ---
# If you don't need a proxy, set it to None.
# Example: PROXY = None
# PROXY = 'http://127.0.0.1:10809'
PROXY = None

# --- Analysis Settings ---
# List of symbols to analyze
SYMBOLS_TO_ANALYZE = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'DOGE/USDT', 'SUI/USDT', 'ADA/USDT', 'BNB/USDT']

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
# A "DEFAULT" key is required as a fallback for symbols not explicitly listed.
VIRTUAL_TRADE_CONFIG = {
    "DEFAULT": {
        "RISK_PER_TRADE_PERCENT": 1.0,  # Default risk: 1.5% of available balance
        "ATR_MULTIPLIER_FOR_SL": 2.0    # Default SL: 2 * ATR
    },
    "BTC/USDT": {
        "RISK_PER_TRADE_PERCENT": 3.0,  # Risk for BTC: 2%
        "ATR_MULTIPLIER_FOR_SL": 2.0    # Tighter SL for BTC: 1.8 * ATR
    },
    "ETH/USDT": {
        "RISK_PER_TRADE_PERCENT": 2.0,  # Risk for ETH: 1.8%
        "ATR_MULTIPLIER_FOR_SL": 2.0    # Wider SL for ETH: 2.2 * ATR
    }
    # You can add other symbols here, e.g., "SOL/USDT": {...}
}

