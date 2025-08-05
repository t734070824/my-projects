# buy_sell_notify/config.py

# --- DingTalk Notifier Settings ---
# If your bot uses Keyword or IP security, just fill in the full webhook url.
# If your bot uses Signature security, fill in both the webhook base url and the secret.
DINGTALK_WEBHOOK = "https://oapi.dingtalk.com/robot/send?access_token=f039bbc0bc60ddc6ef65edb56505af5aa16e057e1e295a6bfd8835f57858f82e"
DINGTALK_SECRET = "SEC5fdbf6ca6b850638f4e6848f7949312f13d11ac44ec349e3f59e6824233a8e6b" # 加签验证密钥

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
# 增加更多主流币种以提高信号总量 (从8个增加到16个)
SYMBOLS_TO_ANALYZE = [
    # Tier 1: 超大市值 (>100B)
    'BTC/USDT', 'ETH/USDT', 'BNB/USDT',
    # Tier 2: 大市值 (10B-100B)  
    'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT',
    # Tier 3: 中市值活跃币 (1B-10B)
    'DOGE/USDT', 'SUI/USDT', 'LINK/USDT', 'NEAR/USDT', 'UNI/USDT',
    # Tier 4: 高波动小市值
    'PEPE/USDT', 'WIF/USDT', 'BONK/USDT'
]

# --- Scheduler Settings ---
# Time to run the analysis every hour. Use ":01" for the 1st minute of the hour.
RUN_AT_MINUTE = ":01"

# --- Monitoring Settings ---
# 智能监控频率：有持仓时更频繁，无持仓时降低频率节省资源
MONITOR_INTERVAL_SECONDS = 10  # 基础监控间隔10秒 (原15秒)
MONITOR_INTERVAL_NO_POSITION = 60  # 无持仓时60秒检查一次
MONITOR_INTERVAL_HIGH_PROFIT = 5   # 高盈利时5秒检查一次

# --- Data Fetching Settings ---
# Number of historical candles to fetch for analysis
HISTORY_LIMIT = 400

# --- Indicator Settings ---
# ATR (Average True Range) settings.
# You can define specific timeframes and lengths for each symbol.
# A "DEFAULT" key is required as a fallback for symbols not explicitly listed.
ATR_CONFIG = {
    "DEFAULT": {"timeframe": "4h", "length": 20},
    "BTC/USDT": {"timeframe": "1d", "length": 14},
    "ETH/USDT": {"timeframe": "4h", "length": 20},
    # You can add other symbols here, e.g.:
        "SOL/USDT": {"timeframe": "4h", "length": 20},
}

# --- Virtual Trading Settings ---
# Settings for calculating virtual trade parameters.
# A "DEFAULT" key is required as a fallback for symbols not explicitly listed.
# 基于"少而精"理念，提高风险敞口以获得更好的风险回报比
VIRTUAL_TRADE_CONFIG = {
    "DEFAULT": {
        "RISK_PER_TRADE_PERCENT": 2.5,  # 提高到2.5% (信号稀少时应该加大单笔)
        "ATR_MULTIPLIER_FOR_SL": 2.0    # 保持2倍ATR止损
    },
    
    # Tier 1: 超大市值币种 - 最高风险敞口
    "BTC/USDT": {
        "RISK_PER_TRADE_PERCENT": 5.0,  # BTC信号最稀少且质量最高，提高到5%
        "ATR_MULTIPLIER_FOR_SL": 1.8    # 稍微收紧止损
    },
    "ETH/USDT": {
        "RISK_PER_TRADE_PERCENT": 4.0,  # ETH次之，4%
        "ATR_MULTIPLIER_FOR_SL": 1.8
    },
    "BNB/USDT": {
        "RISK_PER_TRADE_PERCENT": 3.5,
        "ATR_MULTIPLIER_FOR_SL": 2.0
    },
    
    # Tier 2: 大市值币种 - 中等风险敞口
    "SOL/USDT": {
        "RISK_PER_TRADE_PERCENT": 3.0,
        "ATR_MULTIPLIER_FOR_SL": 2.0
    },
    "XRP/USDT": {
        "RISK_PER_TRADE_PERCENT": 3.0,
        "ATR_MULTIPLIER_FOR_SL": 2.2   # 稍微放宽止损
    },
    "ADA/USDT": {
        "RISK_PER_TRADE_PERCENT": 2.8,
        "ATR_MULTIPLIER_FOR_SL": 2.2
    },
    "AVAX/USDT": {
        "RISK_PER_TRADE_PERCENT": 2.8,
        "ATR_MULTIPLIER_FOR_SL": 2.0
    },
    "DOT/USDT": {
        "RISK_PER_TRADE_PERCENT": 2.5,
        "ATR_MULTIPLIER_FOR_SL": 2.2
    },
    
    # Tier 3&4: 中小市值币种 - 标准风险敞口但收紧止损
    "DOGE/USDT": {
        "RISK_PER_TRADE_PERCENT": 2.0,  # 波动大，降低风险
        "ATR_MULTIPLIER_FOR_SL": 1.8
    },
    "PEPE/USDT": {
        "RISK_PER_TRADE_PERCENT": 1.5,  # meme币风险最小
        "ATR_MULTIPLIER_FOR_SL": 1.5
    },
    "WIF/USDT": {
        "RISK_PER_TRADE_PERCENT": 1.5,
        "ATR_MULTIPLIER_FOR_SL": 1.5
    },
    "BONK/USDT": {
        "RISK_PER_TRADE_PERCENT": 1.2,
        "ATR_MULTIPLIER_FOR_SL": 1.5
    }
}


# --- Reversal (Aggressive) Strategy Settings ---
# Settings for the aggressive, counter-trend strategy.
REVERSAL_STRATEGY_CONFIG = {
    "enabled": True,  # Master switch for this strategy
    "timeframe": "1h", # Timeframe to run this strategy on
    "rsi_oversold": 28, # RSI level to trigger a long signal
    "rsi_overbought": 72, # RSI level to trigger a short signal
    "risk_per_trade_percent": 0.8, # Risk 0.8% of balance for this aggressive strategy
    "atr_multiplier_for_sl": 1.5 # Use a tighter SL (1.5 * ATR) for reversal trades
}

