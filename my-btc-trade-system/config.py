# 币安API配置
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_KLINES_ENDPOINT = "/fapi/v1/klines"
BINANCE_ACCOUNT_ENDPOINT = "/fapi/v2/account"
BINANCE_POSITION_ENDPOINT = "/fapi/v3/positionRisk"
BINANCE_USER_TRADES_ENDPOINT = "/fapi/v1/userTrades"

# 交易对配置 - 支持多个交易对同时获取数据
SYMBOLS = ["BTCUSDT", "ETHUSDT", "DOGEUSDT","XRPUSDT","SOLUSDT"]  # 要获取数据的交易对列表

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

# 减仓策略配置
# BTC减仓策略
BTC_REDUCE_POSITION = [
    (2, 20),   # 相对成本+3%：减少波段仓位25%
    (5, 40),   # 相对成本+6%：减少波段仓位50%
    (8, 70),  # 相对成本+10%：减少波段仓位75%
]

# ETH减仓策略
ETH_REDUCE_POSITION = [
    (3, 30),   # 相对成本+2%：减少波段仓位30%
    (6, 60),   # 相对成本+5%：减少波段仓位60%
    (10, 80),   # 相对成本+8%：减少波段仓位80%
]

# 强势上升趋势策略
# BTC强势上升加仓策略（基于7日高点回调）
BTC_STRONG_UP_ADD_POSITION = [
    (-3, 150),  # 从7日高点回调3%：加仓150U
    (-5, 300),  # 从7日高点回调5%：加仓300U
    (-8, 500),  # 从7日高点回调8%：加仓500U
]

# BTC强势上升减仓策略（阈值提高）
BTC_STRONG_UP_REDUCE_POSITION = [
    (6, 20),   # 相对成本+6%：减少波段仓位20%
    (12, 40),  # 相对成本+12%：减少波段仓位40%
    (20, 60),  # 相对成本+20%：减少波段仓位60%
]

# ETH强势上升加仓策略（基于7日高点回调）
ETH_STRONG_UP_ADD_POSITION = [
    (-4, 80),   # 从7日高点回调4%：加仓80U
    (-6, 150),  # 从7日高点回调6%：加仓150U
    (-10, 250), # 从7日高点回调10%：加仓250U
]

# ETH强势上升减仓策略（阈值提高）
ETH_STRONG_UP_REDUCE_POSITION = [
    (4, 25),   # 相对成本+4%：减少波段仓位25%
    (8, 45),   # 相对成本+8%：减少波段仓位45%
    (15, 70),  # 相对成本+15%：减少波段仓位70%
]

# 弱势下降趋势策略
# BTC弱势下降加仓策略（更加积极）
BTC_WEAK_DOWN_ADD_POSITION = [
    (-1.5, 200), # 相对成本-1.5%：加仓200U
    (-3, 400),   # 相对成本-3%：加仓400U
    (-5, 600),   # 相对成本-5%：加仓600U
]

# BTC弱势下降减仓策略（更加保守）
BTC_WEAK_DOWN_REDUCE_POSITION = [
    (5, 20),   # 相对成本+5%：减少波段仓位20%
    (10, 40),  # 相对成本+10%：减少波段仓位40%
    (18, 60),  # 相对成本+18%：减少波段仓位60%
]

# ETH弱势下降加仓策略（更加积极）
ETH_WEAK_DOWN_ADD_POSITION = [
    (-2, 100),  # 相对成本-2%：加仓100U
    (-4, 200),  # 相对成本-4%：加仓200U
    (-7, 350),  # 相对成本-7%：加仓350U
]

# ETH弱势下降减仓策略（更加保守）
ETH_WEAK_DOWN_REDUCE_POSITION = [
    (3, 25),   # 相对成本+3%：减少波段仓位25%
    (7, 50),   # 相对成本+7%：减少波段仓位50%
    (12, 75),  # 相对成本+12%：减少波段仓位75%
]

# 保证金管理分级配置
MARGIN_LEVELS = {
    'aggressive': (0, 30),      # 积极操作区：< 30%
    'normal': (30, 50),         # 正常操作区：30-50%
    'cautious': (50, 65),       # 谨慎操作区：50-65%
    'risk_control': (65, 80),   # 风险控制区：65-80%
    'emergency': (80, 100),     # 紧急区：> 80%
}

# 硬性风控红线配置
# 仓位上限
MAX_POSITION_LIMITS = {
    'BTCUSDT': 3500,    # BTC最大仓位不超过3500U
    'ETHUSDT': 2500,    # ETH最大仓位不超过2500U
}



# 操作频率限制
MAX_DAILY_OPERATIONS_PER_SIDE = 10  # 单币种单日每个方向最多操作1次

# 强制平仓条件
FORCE_CLOSE_MARGIN_RATIO = 85    # 保证金使用率达到85%
FORCE_CLOSE_SINGLE_LOSS = 15     # 单币种亏损超过总资产15%
FORCE_CLOSE_TOTAL_LOSS = 30      # 账户总亏损超过30%

# 未实现盈亏占总余额比例减仓策略（积极型）
PNL_RATIO_REDUCE_STRATEGY = [
    (12, 25),  # 未实现盈亏占总余额 >= 12%：减仓25%
    (20, 50),  # 未实现盈亏占总余额 >= 20%：减仓50%
    (30, 75),  # 未实现盈亏占总余额 >= 30%：减仓75%
]

# 钉钉机器人配置
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=f039bbc0bc60ddc6ef65edb56505af5aa16e057e1e295a6bfd8835f57858f82e"  # 钉钉机器人Webhook地址，需要配置
ENABLE_DINGTALK_NOTIFICATION = True  # 是否启用钉钉通知

# 盈亏记录配置
PNL_RECORD_INTERVAL = 60  # 记录间隔（秒），默认60秒
PNL_RECORD_MAX_HOURS = 24  # 最大记录小时数，默认24小时
PNL_RECORD_FILE = "pnl_history.json"  # 盈亏记录文件 