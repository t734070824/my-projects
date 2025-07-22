# 币安API配置
BINANCE_API_URL = "https://fapi.binance.com/fapi/v1/klines"  # 币安合约K线数据API地址

# 交易对配置 - 支持多个交易对同时获取数据
SYMBOLS = ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]  # 要获取数据的交易对列表

# K线时间间隔配置
# 支持: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
INTERVAL = "1h"  # K线间隔，1h表示1小时

# 时区配置 (UTC偏移)
TIMEZONE = "0"  # 时区偏移，0表示UTC时间

# 代理配置
# True: 使用系统代理设置 (如v2rayN等)
# False: 禁用代理，直接连接
USE_PROXY = False 