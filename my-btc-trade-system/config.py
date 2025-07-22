# 币安API配置
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_KLINES_ENDPOINT = "/fapi/v1/klines"
BINANCE_ACCOUNT_ENDPOINT = "/fapi/v2/account"
BINANCE_POSITION_ENDPOINT = "/fapi/v3/positionRisk"

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

# 趋势判断阈值配置
STRONG_UP_CHANGE = 15  # 强势上升7日涨幅阈值
STRONG_UP_CONSECUTIVE = 5  # 强势上升连续收阳天数
STRONG_DOWN_CHANGE = -12  # 弱势下降7日跌幅阈值
STRONG_DOWN_CONSECUTIVE = 4  # 弱势下降连续收阴天数
SIDEWAYS_RANGE = 8  # 横盘震荡范围
RELATIVE_BTC_STRONG = 8  # 相对BTC强势阈值
MA20_DISTANCE = 5  # 20日均线偏离阈值

# 加仓策略配置
# BTC加仓策略
BTC_ADD_POSITION_BELOW_COST = [
    (-2, 200),  # 相对成本-2%：加仓200U
    (-4, 400),  # 相对成本-4%：加仓400U
    (-6, 600),  # 相对成本-6%：加仓600U
]

BTC_ADD_POSITION_ABOVE_COST = [
    (-3, 150),  # 从5日高点回调3%：加仓150U
    (-5, 300),  # 从5日高点回调5%：加仓300U
    (-8, 500),  # 从5日高点回调8%：加仓500U
]

# 其他币种加仓策略
OTHER_ADD_POSITION_BELOW_COST = [
    (-3, 100),  # 相对成本-3%：加仓100U
    (-6, 200),  # 相对成本-6%：加仓200U
    (-9, 300),  # 相对成本-9%：加仓300U
]

OTHER_ADD_POSITION_ABOVE_COST = [
    (-4, 80),   # 从5日高点回调4%：加仓80U
    (-6, 150),  # 从5日高点回调6%：加仓150U
    (-10, 250), # 从5日高点回调10%：加仓250U
] 