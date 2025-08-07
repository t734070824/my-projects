# 币安API配置
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_ACCOUNT_ENDPOINT = "/fapi/v2/account"
BINANCE_POSITION_ENDPOINT = "/fapi/v3/positionRisk"

# 代理配置
# True: 使用系统代理设置 (如v2rayN等)
# False: 禁用代理，直接连接
USE_PROXY = True

# 钉钉机器人配置
DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=9ae12d4cdaac82d49549bdb46e8f2295bf52cf04d89fcb6d5ee42568be703bca"  # 钉钉机器人Webhook地址，需要配置
ENABLE_DINGTALK_NOTIFICATION = True  # 是否启用钉钉通知

# 盈亏记录配置
PNL_RECORD_INTERVAL = 60  # 记录间隔（秒），默认60秒
PNL_RECORD_MAX_HOURS = 168  # 最大记录小时数，默认168小时 (7天)
PNL_RECORD_FILE = "pnl_history.json"  # 盈亏记录文件

# 通知配置
NOTIFICATION_INTERVAL = 1800 # 钉钉通知发送间隔（秒），默认1800秒 (30分钟)