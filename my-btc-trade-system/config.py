# 配置文件
# 币安API配置
BINANCE_API_CONFIG = {
    'base_url': 'https://data-api.binance.vision/api/v3/klines',
    'default_symbol': 'BTCUSDT',
    'default_interval': '1h',
    'default_limit': 100,
    'timeout': 30
}

# 数据获取配置
DATA_FETCH_CONFIG = {
    'retry_times': 3,
    'retry_delay': 1,  # 秒
    'cache_duration': 60,  # 缓存时间（秒）
    'enable_ssl_verify': False,  # 是否启用SSL验证
    'enable_proxy': False,  # 是否启用代理
    'proxy_settings': {
        'http': None,
        'https': None
    },
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# 风险分析配置
RISK_ANALYSIS_CONFIG = {
    'price_change_threshold': 0.05,  # 5%价格变化阈值
    'volume_spike_threshold': 2.0,   # 成交量突增阈值
    'volatility_threshold': 0.03,    # 波动率阈值
    'ma_periods': [5, 10, 20, 50],  # 移动平均线周期
    'rsi_period': 14,                # RSI周期
    'rsi_overbought': 70,           # RSI超买线
    'rsi_oversold': 30              # RSI超卖线
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'trading_system.log'
}

# 输出配置
OUTPUT_CONFIG = {
    'display_precision': 2,          # 显示精度
    'max_display_rows': 10,          # 最大显示行数
    'enable_console_output': True,   # 启用控制台输出
    'enable_file_output': True       # 启用文件输出
} 